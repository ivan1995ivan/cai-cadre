from datetime import date

from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.deletion import DeletionMarkMixin, ensure_not_marked
from apps.core.pagination import StandardPagination
from apps.org.models import Subdivision
from apps.orders.serializers import OrderListSerializer
from apps.staff import services as staff
from apps.staff.models import Employee, FamilyMember

from . import balance, printing, services
from .models import LeaveAdjustment, LeaveRequest, LeaveRight, LeaveSchedule, LeaveScheduleLine, SickLeave
from .serializers import (LeaveAdjustmentSerializer, LeaveRequestSerializer, LeaveRightSerializer, LeaveScheduleLineSerializer,
                          LeaveScheduleSerializer, SickLeaveSerializer)


def _date(value, field="date"):
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except (TypeError, ValueError):
        raise ValidationError({field: "Data se scrie AAAA-LL-ZZ."}) from None


def _employee(request, pk, module="leave"):
    employee = Employee.objects.filter(pk=pk).first() if pk else None
    if employee is None or not staff.can_see(employee, request.user, module):
        raise NotFound()
    return employee


def _visible_subdivisions(user, module="leave"):
    """None = toate; altfel id-urile subdiviziunilor utilizatorului (șeful subdiviziunii)."""
    return staff.visible_subdivision_ids(user, module)


# --- soldurile -----------------------------------------------------------------------------------------------
class BalanceListView(APIView):
    """Soldurile concediilor pe angajați (lista cu filtre): anul de muncă în curs, cuvenit, folosit, rămas."""

    perm_module = "leave"

    def get(self, request):
        p = request.query_params
        qs = Employee.objects.exclude(status__in=("dismissed", "candidate")).filter(is_archived=False)
        qs = staff.scope_employees(qs, request.user, "leave")
        if p.get("subdivision"):
            sub = Subdivision.objects.filter(pk=p["subdivision"]).first()
            ids = sub.descendant_ids() if sub else set()
            qs = qs.filter(employments__subdivision_id__in=ids).exclude(employments__status="ended").distinct()
        if p.get("q"):
            q = p["q"].strip()
            qs = qs.filter(Q(last_name__icontains=q) | Q(first_name__icontains=q) | Q(tab_number=q))
        qs = balance.prefetch(qs.order_by("last_name", "first_name", "id"))
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        calc = balance.Calculator(_date(p.get("on_date"), "on_date"))
        rows = []
        for emp in page:
            data = calc.balance(emp)
            job = calc.job_of(emp)
            cur = next((y for y in data["years"] if data["current"] and y["from"] == data["current"]["from"]), None)
            rows.append({
                "id": emp.pk, "tab_number": emp.tab_number, "full_name": emp.full_name(), "status": emp.status,
                "subdivision": calc.subdivisions[job.subdivision_id].name_ro if job else "",
                "occupation": calc.occupations[job.occupation_id].name_ro if job else "",
                "hired": data["start"], "year_from": cur["from"] if cur else None, "year_to": cur["to"] if cur else None,
                "entitled": cur["entitled"] if cur else 0, "accrued": cur["accrued"] if cur else 0,
                "used": cur["used"] if cur else 0, "remaining": data["remaining"], "available": data["available"],
            })
        return paginator.get_paginated_response(rows)


class EmployeeBalanceView(APIView):
    """Soldul unui angajat pe toți anii de muncă."""

    perm_module = ("leave", "employees")

    def get(self, request, employee):
        emp = _employee(request, employee, "employees")
        return Response(balance.balance(emp, _date(request.query_params.get("on_date"), "on_date")))


class SettingsView(APIView):
    """Setările evidenței concediilor: data pornirii și perioadele care nu dau dreptul la concediu."""

    perm_module = "leave"

    def get(self, request):
        return Response(balance.get_settings())

    def put(self, request):
        if not request.user.has_crm_perm("settings.edit"):
            raise PermissionDenied("Setările le schimbă administratorul.")
        return Response(balance.save_settings(request.data))


class SocialDatesView(APIView):
    """Datele concediilor sociale: maternitate (126 zile), paternal (14), îngrijirea copilului (până la 3 / 4 ani)."""

    def get(self, request):
        p = request.query_params
        child = None
        if p.get("child"):
            child = FamilyMember.objects.filter(pk=p["child"]).select_related("employee").first()
            if child is None or not staff.can_see(child.employee, request.user):
                raise NotFound()
        return Response(services.social_dates(p.get("kind", ""), _date(p.get("from"), "from"), child))


# --- drepturile și corectările (în fișa angajatului) --------------------------------------------------------------
class EmployeeLeaveMixin:
    perm_module = "leave"
    pagination_class = None
    model = None

    def get_queryset(self):
        qs = self.model.objects.select_related("employee")
        emp = self.request.query_params.get("employee")
        if self.action == "list":
            if not emp:
                return qs.none()
            _employee(self.request, emp)
            return qs.filter(employee_id=emp)
        return qs.filter(employee__in=staff.scope_employees(Employee.objects.all(), self.request.user, "leave"))

    def perform_create(self, serializer):
        _employee(self.request, serializer.validated_data["employee"].pk)
        extra = {"created_by": self.request.user} if hasattr(self.model, "created_by") else {}
        serializer.save(**extra)

    def perform_update(self, serializer):
        if "employee" in serializer.validated_data and serializer.validated_data["employee"] != serializer.instance.employee:
            raise ValidationError({"employee": "Înregistrarea nu se mută la alt angajat."})
        serializer.save()


class LeaveRightViewSet(EmployeeLeaveMixin, viewsets.ModelViewSet):
    model = LeaveRight
    serializer_class = LeaveRightSerializer


class LeaveAdjustmentViewSet(EmployeeLeaveMixin, viewsets.ModelViewSet):
    model = LeaveAdjustment
    serializer_class = LeaveAdjustmentSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("order_item__order")

    def perform_destroy(self, instance):
        if instance.order_item_id:
            raise ValidationError({"detail": "Corectarea făcută prin ordin se întoarce prin anularea ordinului."})
        instance.delete()


# --- graficul anual -------------------------------------------------------------------------------------------
class LeaveScheduleViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "leave"
    serializer_class = LeaveScheduleSerializer
    perm_actions = {"report": "view", "fill": "edit", "submit": "edit", "approve": "approve", "reopen": "approve",
                    "print": "view", "make_orders": "edit"}

    def get_queryset(self):
        qs = LeaveSchedule.objects.select_related("subdivision").annotate(
            lines_count=Count("lines", distinct=True),
            planned_count=Count("lines", filter=Q(lines__date_from__isnull=False), distinct=True))
        ids = _visible_subdivisions(self.request.user)
        if ids is not None:
            qs = qs.filter(subdivision_id__in=ids)
        p = self.request.query_params
        if p.get("year"):
            qs = qs.filter(year=p["year"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("subdivision"):
            qs = qs.filter(subdivision_id=p["subdivision"])
        return qs

    def _check_subdivision(self, sub):
        ids = _visible_subdivisions(self.request.user)
        if ids is not None and sub.pk not in ids:
            raise PermissionDenied("Subdiviziunea nu este a dvs.")

    def perform_create(self, serializer):
        self._check_subdivision(serializer.validated_data["subdivision"])
        sch = serializer.save(created_by=self.request.user)
        services.fill_schedule(sch)

    def perform_update(self, serializer):
        _editable(serializer.instance, self.request.user)
        serializer.save()

    def check_delete(self, instance):
        if instance.status == "approved":
            raise ValidationError({"detail": "Graficul aprobat nu se șterge."})

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        sch = self.get_object()
        return Response({**LeaveScheduleSerializer(sch).data, **services.schedule_report(sch)})

    @action(detail=True, methods=["post"])
    def fill(self, request, pk=None):
        sch = self.get_object()
        _editable(sch, request.user)
        return Response({"added": services.fill_schedule(sch)})

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        sch = self.get_object()
        _editable(sch, request.user)
        sch.status = "submitted"
        sch.save(update_fields=["status"])
        return Response(LeaveScheduleSerializer(sch).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Aprobarea fără ordin (de ex. graficul aprobat pe hârtie): se scrie prin ce act."""
        sch = self.get_object()
        sch.status, sch.approved_at = "approved", timezone.now()
        sch.approved_by = str(request.data.get("approved_by") or sch.approved_by or "")[:200]
        sch.save(update_fields=["status", "approved_at", "approved_by"])
        return Response(LeaveScheduleSerializer(sch).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        sch = self.get_object()
        sch.status, sch.approved_at = "draft", None
        sch.save(update_fields=["status", "approved_at"])
        return Response(LeaveScheduleSerializer(sch).data)

    @action(detail=True, methods=["post"], url_path="make-orders")
    def make_orders(self, request, pk=None):
        if not request.user.has_crm_perm("orders.create"):
            raise PermissionDenied("Nu aveți drept să faceți ordine.")
        sch = self.get_object()
        try:
            month = int(request.data.get("month"))
        except (TypeError, ValueError):
            raise ValidationError({"month": "Alegeți luna."}) from None
        order = services.make_schedule_orders(sch, month, request.user)
        return Response(OrderListSerializer(order).data, status=201)

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        return printing.print_schedule(request, self.get_object())


def _editable(schedule, user):
    """Șeful subdiviziunii schimbă graficul cât e ciornă; resursele umane (drept de aprobare) — până la aprobare."""
    ensure_not_marked(schedule)
    if schedule.status == "approved":
        raise ValidationError({"detail": "Graficul este aprobat. Schimbările se fac prin ordinul de amânare."})
    if schedule.status == "submitted" and not user.has_crm_perm("leave.approve"):
        raise ValidationError({"detail": "Graficul a fost transmis la resurse umane."})
    if _visible_subdivisions(user) is not None and schedule.status != "draft":
        raise ValidationError({"detail": "Graficul a fost transmis la resurse umane."})


class LeaveScheduleLineViewSet(viewsets.ModelViewSet):
    perm_module = "leave"
    perm_actions = {"update": "edit", "partial_update": "edit", "create": "edit", "destroy": "edit"}
    serializer_class = LeaveScheduleLineSerializer
    pagination_class = None

    def get_queryset(self):
        qs = LeaveScheduleLine.objects.select_related("schedule", "employee")
        ids = _visible_subdivisions(self.request.user)
        if ids is not None:
            qs = qs.filter(schedule__subdivision_id__in=ids)
        if self.request.query_params.get("schedule"):
            qs = qs.filter(schedule_id=self.request.query_params["schedule"])
        elif self.action == "list":
            return qs.none()
        return qs

    def perform_create(self, serializer):
        sch = serializer.validated_data["schedule"]
        if _visible_subdivisions(self.request.user) is not None and sch.subdivision_id not in _visible_subdivisions(self.request.user):
            raise PermissionDenied("Subdiviziunea nu este a dvs.")
        _editable(sch, self.request.user)
        if sch.lines.filter(employee=serializer.validated_data["employee"]).exists() and not self.request.data.get("second_part"):
            raise ValidationError({"employee": "Angajatul este deja în grafic (pentru a doua parte a concediului bifați „partea a doua”)."})
        last = sch.lines.order_by("-sort").first()
        serializer.save(sort=(last.sort + 10) if last else 10)

    def perform_update(self, serializer):
        _editable(serializer.instance.schedule, self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _editable(instance.schedule, self.request.user)
        instance.delete()


# --- cererile ---------------------------------------------------------------------------------------------------
class LeaveRequestViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "leave"
    serializer_class = LeaveRequestSerializer
    perm_actions = {"approve": "approve", "reject": "approve", "withdraw": "edit", "make_orders": "edit"}

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related("employee", "decided_by", "order_item__order").prefetch_related(
            "employee__employments__subdivision")
        qs = qs.filter(employee__in=staff.scope_employees(Employee.objects.all(), self.request.user, "leave"))
        p = self.request.query_params
        if p.get("employee"):
            qs = qs.filter(employee_id=p["employee"])
        if p.get("status"):
            qs = qs.filter(status__in=p["status"].split(","))
        if p.get("kind"):
            qs = qs.filter(kind=p["kind"])
        if p.get("subdivision"):
            sub = Subdivision.objects.filter(pk=p["subdivision"]).first()
            qs = qs.filter(employee__employments__subdivision_id__in=sub.descendant_ids() if sub else set()).distinct()
        if p.get("year"):
            qs = qs.filter(date_from__year=p["year"])
        return qs

    def perform_create(self, serializer):
        emp = _employee(self.request, serializer.validated_data["employee"].pk)
        data = serializer.validated_data
        clash = services.overlapping(emp, data["date_from"], data["date_to"]).first()
        if clash is not None:
            raise ValidationError({"date_from": f"Perioada se suprapune cu {clash.get_kind_display().lower()} "
                                                f"{clash.date_from:%d.%m.%Y}–{clash.date_to:%d.%m.%Y}."})
        services.fire("created", serializer.save(created_by=self.request.user))

    def perform_update(self, serializer):
        if serializer.instance.status not in ("new", "rejected"):
            raise ValidationError({"detail": "Cererea aprobată nu se mai modifică."})
        serializer.save(status="new")

    def check_delete(self, instance):
        if instance.status not in ("new", "rejected", "withdrawn"):
            raise ValidationError({"detail": "Se șterge doar cererea neaprobată."})

    def _decide(self, request, status):
        req = self.get_object()
        if req.status not in ("new", "approved", "rejected"):
            raise ValidationError({"detail": "Pentru cerere s-a emis deja ordinul."})
        req.status, req.decided_by, req.decided_at = status, request.user, timezone.now()
        req.decision_note = str(request.data.get("note") or "")[:300]
        req.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])
        services.fire("decided", req)
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._decide(request, "approved")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._decide(request, "rejected")

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        req = self.get_object()
        if req.status == "ordered" and req.order_item_id:
            raise ValidationError({"detail": "Ordinul este deja făcut; se anulează ordinul."})
        req.status = "withdrawn"
        req.save(update_fields=["status"])
        return Response(self.get_serializer(req).data)

    @action(detail=False, methods=["post"], url_path="make-orders")
    def make_orders(self, request):
        if not request.user.has_crm_perm("orders.create"):
            raise PermissionDenied("Nu aveți drept să faceți ordine.")
        ids = request.data.get("ids") or []
        reqs = list(self.get_queryset().filter(pk__in=ids))
        if not reqs:
            raise ValidationError({"detail": "Alegeți cererile aprobate."})
        orders = services.make_request_orders(reqs, request.user)
        return Response(OrderListSerializer(orders, many=True).data, status=201)


# --- foile de boală ---------------------------------------------------------------------------------------------
class SickLeaveViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "sick_leave"
    serializer_class = SickLeaveSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        qs = SickLeave.objects.select_related("employee", "continuation_of").prefetch_related(
            "employee__employments__subdivision",
            Prefetch("continuations", queryset=SickLeave.objects.filter(deletion_mark=False), to_attr="live_continuations"))
        qs = qs.filter(employee__in=staff.scope_employees(Employee.objects.all(), self.request.user, "sick_leave"))
        p = self.request.query_params
        if p.get("employee"):
            qs = qs.filter(employee_id=p["employee"])
        if p.get("kind"):
            qs = qs.filter(kind=p["kind"])
        if p.get("date_from"):
            qs = qs.filter(date_to__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(date_from__lte=p["date_to"])
        if p.get("open"):  # deschis: fără data prezentării la lucru și fără certificat care îl continuă
            continued = SickLeave.objects.filter(continuation_of=OuterRef("pk"), deletion_mark=False)
            qs = qs.filter(return_date__isnull=True).exclude(Exists(continued))
        if p.get("q"):
            q = p["q"].strip()
            qs = qs.filter(Q(number__icontains=q) | Q(employee__last_name__icontains=q) | Q(employee__tab_number=q))
        if p.get("subdivision"):
            sub = Subdivision.objects.filter(pk=p["subdivision"]).first()
            qs = qs.filter(employee__employments__subdivision_id__in=sub.descendant_ids() if sub else set()).distinct()
        return qs

    def _save(self, serializer, **extra):
        sick = serializer.instance or SickLeave()
        for key, value in {**serializer.validated_data, **extra}.items():
            setattr(sick, key, value)
        if not staff.can_see(sick.employee, self.request.user, "sick_leave"):
            raise NotFound()
        self.warnings = services.save_sick_leave(sick)
        serializer.instance = sick

    def perform_create(self, serializer):
        self._save(serializer, created_by=self.request.user)

    def perform_update(self, serializer):
        self._save(serializer)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data["warnings"] = getattr(self, "warnings", [])
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data["warnings"] = getattr(self, "warnings", [])
        return response
