from datetime import date

from django.db.models import Prefetch, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.deletion import DeletionMarkMixin
from apps.leave.models import WITHOUT_HOLIDAYS, Absence
from apps.org import calendar
from apps.org.models import OrderType
from apps.staff import services as staff_services
from apps.staff.models import Employee

from . import printing, services
from .models import Incentive, Order, OrderItem, Sanction
from .serializers import (AbsenceSerializer, IncentiveSerializer, OrderItemSerializer, OrderListSerializer, OrderSerializer,
                          SanctionSerializer)


def _date(value, field="date"):
    try:
        return date.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        raise ValidationError({field: "Data se scrie AAAA-LL-ZZ."}) from None


class OrderViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "orders"
    perm_actions = {"related": "view", "sign": "approve", "print": "view", "acknowledge": "edit", "refresh_texts": "edit",
                    "cancel_by_order": "create", "register": "view", "print_register": "view", "add_subdivision": "edit"}

    def get_serializer_class(self):
        return OrderListSerializer if self.action == "list" else OrderSerializer

    @action(detail=True, methods=["get"])
    def related(self, request, pk=None):
        """Documentele legate de ordin: ce a rezultat din punctele lui la semnare (absențele, acumulările planificate, tarifele
        pe tipuri de ore, cumulările, formarea, sancțiunile și stimulările, corectările soldului concediilor) și de unde
        a pornit (cererea de concediu, ordinul anulat de acesta / care îl anulează)."""
        from .related import related

        return Response(related(self.get_object(), request.user))

    def get_queryset(self):
        p = self.request.query_params
        qs = Order.objects.select_related("order_type", "cancelled_by").prefetch_related("legal_bases", 
            Prefetch("items", queryset=OrderItem.objects.select_related("employee", "employment__occupation",
                                                                         "employment__subdivision")))
        qs = services.visible_orders(qs, self.request.user)
        if p.get("register"):
            qs = qs.filter(register=p["register"])
        if p.get("year"):
            qs = qs.filter(year=p["year"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("type"):
            qs = qs.filter(order_type__code=p["type"])
        if p.get("group"):
            qs = qs.filter(order_type__group=p["group"])
        if p.get("employee"):
            qs = qs.filter(items__employee_id=p["employee"])
        if p.get("q"):
            q = p["q"].strip()
            qs = qs.filter(Q(number__iexact=q) | Q(title__icontains=q) | Q(items__employee__last_name__icontains=q)
                           | Q(items__employee__tab_number=q))
        if p.get("date_from"):
            qs = qs.filter(date__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(date__lte=p["date_to"])
        return qs.distinct()

    def create(self, request, *args, **kwargs):
        ot = OrderType.objects.filter(pk=request.data.get("order_type"), is_active=True).first()
        if ot is None:
            raise ValidationError({"order_type": "Alegeți tipul ordinului."})
        order = services.new_order(ot, user=request.user, date=_date(request.data.get("date")))
        for i, emp_id in enumerate(request.data.get("employees") or []):
            emp = staff_services.scope_employees(Employee.objects.all(), request.user).filter(pk=emp_id).first()
            if emp:
                item = OrderItem.objects.create(order=order, employee=emp, sort=(i + 1) * 10)
                services.refresh_text(item)
                item.save(update_fields=["text"])
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data, status=201)

    def perform_update(self, serializer):
        services.check_editable(serializer.instance)
        order = serializer.save()
        if "date" in serializer.validated_data:
            order.year = order.date.year
            order.save(update_fields=["year"])

    def check_delete(self, instance):
        services.check_editable(instance)

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        order = services.sign(self.get_object(), request.user)
        return Response(OrderSerializer(Order.objects.get(pk=order.pk), context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"], url_path="add-subdivision")
    def add_subdivision(self, request, pk=None):
        """Ordinul colectiv (de ex. staționarea unui atelier): adaugă câte un punct pentru fiecare angajat cu raport de muncă
        activ la data ordinului în subdiviziune (cu sub-subdiviziunile), fără prestările de servicii și fără cei deja în ordin;
        punctele noi primesc parametrii primului punct (perioada, cauza, procentul…), cu raportul de muncă al fiecăruia."""
        from apps.org.models import Subdivision
        from apps.staff.models import Employment

        order = self.get_object()
        services.check_editable(order)
        if not order.order_type.collective:
            raise ValidationError({"detail": "Acest tip de ordin este pentru un singur angajat."})
        sub = Subdivision.objects.filter(pk=request.data.get("subdivision")).first()
        if sub is None:
            raise ValidationError({"subdivision": "Alegeți subdiviziunea."})
        day = order.date
        jobs = (Employment.objects.filter(subdivision_id__in=sub.descendant_ids(), date_from__lte=day)
                .filter(Q(end_date__isnull=True) | Q(end_date__gte=day)).exclude(kind="contractor")
                .select_related("employee").order_by("employee__last_name", "employee__first_name", "id"))
        first = order.items.order_by("sort", "id").first()
        params = {k: v for k, v in ((first.params or {}) if first else {}).items() if k not in ("employment", "child")}
        present = set(order.items.values_list("employee_id", flat=True))
        last = order.items.order_by("-sort").first()
        sort = last.sort if last else 0
        added = 0
        for job in jobs:
            if job.employee_id in present or not staff_services.can_see(job.employee, request.user):
                continue
            present.add(job.employee_id)
            sort += 10
            item = OrderItem.objects.create(order=order, employee=job.employee, employment=job,
                                            params={**params, "employment": job.pk}, sort=sort)
            services.refresh_text(item)
            item.save(update_fields=["text"])
            added += 1
        data = OrderSerializer(Order.objects.get(pk=order.pk), context=self.get_serializer_context()).data
        return Response({**data, "added": added})

    @action(detail=True, methods=["post"], url_path="refresh-texts")
    def refresh_texts(self, request, pk=None):
        order = self.get_object()
        services.check_editable(order)
        for item in order.items.all():
            services.refresh_text(item, force=bool(request.data.get("force")))
            if request.data.get("force"):
                item.text_edited = False
            item.save(update_fields=["text", "text_edited"])
        return Response(OrderSerializer(Order.objects.get(pk=order.pk), context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """„Am luat cunoștință”: data pe punctele alese (sau pe toate)."""
        order = self.get_object()
        if order.status != "signed":
            raise ValidationError({"detail": "Se aduce la cunoștință doar ordinul semnat."})
        day = _date(request.data.get("date")) or date.today()
        items = order.items.all()
        if request.data.get("items"):
            items = items.filter(pk__in=request.data["items"])
        items.update(acknowledged_on=day)
        return Response(OrderSerializer(Order.objects.get(pk=order.pk), context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"], url_path="cancel-by-order")
    def cancel_by_order(self, request, pk=None):
        """Ciorna ordinului de anulare pentru ordinul semnat (se semnează apoi ca orice ordin)."""
        target = self.get_object()
        if target.status != "signed":
            raise ValidationError({"detail": "Se anulează doar ordinul semnat."})
        ot = OrderType.objects.filter(code="cancel_order").first()
        if ot is None:
            raise ValidationError({"detail": "Tipul „Anularea unui ordin” lipsește din clasificator."})
        order = services.new_order(ot, user=request.user)
        order.title = f"Cu privire la anularea ordinului nr. {target.reference()}"
        order.register = target.register  # anularea se înregistrează în același registru
        order.save(update_fields=["title", "register"])
        item = OrderItem.objects.create(order=order, params={"order": target.pk, "cancelled_label": target.reference()}, sort=10)
        services.refresh_text(item)
        item.save(update_fields=["text"])
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data, status=201)

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        return printing.print_order(request, self.get_object(), request.query_params.get("item"))

    @action(detail=False, methods=["get"])
    def register(self, request):
        reg = request.query_params.get("register", "order_personnel")
        year = int(request.query_params.get("year") or date.today().year)
        data = services.register_report(reg, year)
        return Response({"register": reg, "year": year, "gaps": data["gaps"],
                         "orders": OrderListSerializer(data["orders"], many=True, context=self.get_serializer_context()).data})

    @action(detail=False, methods=["get"], url_path="print-register")
    def print_register(self, request):
        reg = request.query_params.get("register", "order_personnel")
        year = int(request.query_params.get("year") or date.today().year)
        return printing.print_register(request, services.register_report(reg, year))


class OrderItemViewSet(viewsets.ModelViewSet):
    perm_module = "orders"
    perm_actions = {"copy_params": "edit"}
    serializer_class = OrderItemSerializer
    pagination_class = None

    def get_queryset(self):
        qs = OrderItem.objects.select_related("order", "order__order_type", "employee")
        p = self.request.query_params
        if p.get("order"):
            qs = qs.filter(order_id=p["order"])
        elif p.get("employee"):
            qs = qs.filter(employee_id=p["employee"], order__status__in=("signed", "cancelled"))
        elif self.action == "list":
            return qs.none()
        visible = services.visible_orders(Order.objects.all(), self.request.user)
        return qs.filter(order__in=visible) if visible is not None else qs

    def _check(self, order, employee):
        services.check_editable(order)
        if employee is not None and not staff_services.can_see(employee, self.request.user):
            raise PermissionDenied("Angajatul nu este în subdiviziunile dvs.")

    def perform_create(self, serializer):
        order = serializer.validated_data["order"]
        self._check(order, serializer.validated_data.get("employee"))
        if not order.order_type.collective and order.items.exists():
            raise ValidationError({"detail": "Acest tip de ordin este pentru un singur angajat."})
        if serializer.validated_data.get("employee") and order.items.filter(employee=serializer.validated_data["employee"]).exists() \
                and order.order_type.effect in ("hire", "terminate", "suspend", "resume", "change", "salary"):
            raise ValidationError({"employee": "Angajatul este deja în ordin."})
        last = order.items.order_by("-sort").first()
        item = serializer.save(sort=(last.sort + 10) if last else 10)
        if not item.text_edited:
            services.refresh_text(item)
            item.save(update_fields=["text"])

    def perform_update(self, serializer):
        self._check(serializer.instance.order, serializer.validated_data.get("employee", serializer.instance.employee))
        if "text" in serializer.validated_data and serializer.validated_data["text"] != serializer.instance.text:
            serializer.validated_data["text_edited"] = True
        item = serializer.save()
        if not item.text_edited:
            services.refresh_text(item)
            item.save(update_fields=["text"])

    def perform_destroy(self, instance):
        services.check_editable(instance.order)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="copy-params")
    def copy_params(self, request, pk=None):
        """Parametrii acestui punct (perioada, cauza, procentul…) la toate celelalte puncte ale ordinului; raportul de muncă al
        fiecăruia rămâne al lui."""
        item = self.get_object()
        self._check(item.order, None)
        params = {k: v for k, v in (item.params or {}).items() if k not in ("employment", "child")}
        changed = 0
        for other in item.order.items.exclude(pk=item.pk):
            own = {k: v for k, v in (other.params or {}).items() if k == "employment"}
            other.params = {**params, **own}
            services.refresh_text(other)
            other.save(update_fields=["params", "text"])
            changed += 1
        return Response({"changed": changed})


class EmployeeRecordsMixin:
    """Absențele, sancțiunile, stimulările angajatului (doar citire: le fac ordinele)."""

    perm_module = "employees"
    pagination_class = None
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        emp = self.request.query_params.get("employee")
        if not emp:
            return self.model.objects.none()
        employee = Employee.objects.filter(pk=emp).first()
        if employee is None or not staff_services.can_see(employee, self.request.user):
            raise NotFound()
        return self.model.objects.filter(employee=employee).select_related("order_item__order")


class AbsenceViewSet(EmployeeRecordsMixin, viewsets.ModelViewSet):
    model = Absence
    serializer_class = AbsenceSerializer


class SanctionViewSet(EmployeeRecordsMixin, viewsets.ModelViewSet):
    model = Sanction
    serializer_class = SanctionSerializer


class IncentiveViewSet(EmployeeRecordsMixin, viewsets.ModelViewSet):
    model = Incentive
    serializer_class = IncentiveSerializer


class LeaveDaysView(APIView):
    """Calculul perioadei de concediu: din „from” + „to” → zile; din „from” + „days” → ultima zi (fără sărbători)."""

    def get(self, request):
        start = _date(request.query_params.get("from"), "from")
        if start is None:
            raise ValidationError({"from": "Data de început este obligatorie."})
        kind = request.query_params.get("kind", "annual")
        skip = kind in WITHOUT_HOLIDAYS
        end = _date(request.query_params.get("to"), "to")
        if end is None:
            days = int(request.query_params.get("days") or 0)
            if days <= 0:
                raise ValidationError({"days": "Dați data de sfârșit sau numărul de zile."})
            from datetime import timedelta

            end = calendar.leave_end(start, days) if skip else start + timedelta(days=days - 1)
        days = calendar.leave_days(start, end) if skip else (end - start).days + 1
        holidays = sorted(calendar.holidays_between(start, end)) if skip else []
        return Response({"from": start, "to": end, "days": days, "holidays": holidays})
