from decimal import Decimal, InvalidOperation

from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.core.deletion import DeletionMarkMixin, ensure_not_marked
from apps.core.models import NumberSeries
from apps.staff import services as staff
from apps.staff.models import Employee

from . import engine, printing
from .models import EmployeePayItem, ExemptionRequest, PayConstant, Payroll, PayrollItem, PayrollLine, PayType
from .serializers import (EmployeePayItemSerializer, ExemptionRequestSerializer, PayConstantSerializer, PayrollItemSerializer,
                          PayrollLineSerializer, PayrollSerializer, PayTypeSerializer)


# --- setările salariului ----------------------------------------------------------------------------------------
SETTINGS_ACTIONS = {"create": "edit", "update": "edit", "partial_update": "edit", "destroy": "edit"}


class PayConstantViewSet(viewsets.ModelViewSet):
    perm_module = "payroll_settings"
    perm_actions = SETTINGS_ACTIONS
    serializer_class = PayConstantSerializer
    pagination_class = None
    queryset = PayConstant.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("code"):
            qs = qs.filter(code=self.request.query_params["code"])
        return qs


class PayTypeViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = ("payroll_settings", "payroll")
    perm_actions = SETTINGS_ACTIONS
    serializer_class = PayTypeSerializer
    pagination_class = None
    queryset = PayType.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("active"):
            qs = qs.filter(is_active=True)
        if p.get("category"):
            qs = qs.filter(category=p["category"])
        if p.get("personal"):  # tipurile care se pun pe angajat (nu cele automate)
            qs = qs.exclude(formula="auto")
        return qs

    def check_delete(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "Tipul livrat cu sistemul nu se șterge; îl puteți face inactiv."})


# --- pe angajat: sporuri / rețineri personale, cererea de scutire --------------------------------------------------
class EmployeeScopedMixin:
    perm_module = "payroll"
    pagination_class = None
    model = None

    def get_queryset(self):
        qs = self.model.objects.select_related("employee")
        emp = self.request.query_params.get("employee")
        if self.action == "list":
            if not emp:
                return qs.none()
            employee = Employee.objects.filter(pk=emp).first()
            if employee is None or not staff.can_see(employee, self.request.user, "payroll"):
                raise NotFound()
            return qs.filter(employee_id=emp)
        return qs.filter(employee__in=staff.scope_employees(Employee.objects.all(), self.request.user, "payroll"))

    def perform_create(self, serializer):
        if not staff.can_see(serializer.validated_data["employee"], self.request.user, "payroll"):
            raise NotFound()
        serializer.save()


class EmployeePayItemViewSet(EmployeeScopedMixin, viewsets.ModelViewSet):
    model = EmployeePayItem
    serializer_class = EmployeePayItemSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("pay_type", "employment__occupation")


class ExemptionRequestViewSet(EmployeeScopedMixin, viewsets.ModelViewSet):
    model = ExemptionRequest
    serializer_class = ExemptionRequestSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list" and self.request.query_params.get("year"):
            qs = qs.filter(year=self.request.query_params["year"])
        return qs


# --- calculul lunar --------------------------------------------------------------------------------------------------
class PayrollViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "payroll"
    serializer_class = PayrollSerializer
    perm_actions = {"calculate": "edit", "check": "edit", "approve": "approve", "reopen": "approve", "report": "view",
                    "print": "view"}

    def get_queryset(self):
        qs = Payroll.objects.select_related("subdivision").annotate(lines_count=Count("lines", distinct=True))
        ids = staff.visible_subdivision_ids(self.request.user, "payroll")
        if ids is not None:
            qs = qs.filter(subdivision_id__in=ids)
        p = self.request.query_params
        for key in ("year", "month", "status", "subdivision"):
            if p.get(key):
                qs = qs.filter(**{key: p[key]})
        return qs

    def perform_create(self, serializer):
        sub = serializer.validated_data.get("subdivision")
        ids = staff.visible_subdivision_ids(self.request.user, "payroll")
        if ids is not None and (sub is None or sub.pk not in ids):
            raise PermissionDenied("Calculul se face doar pe subdiviziunile dvs.")
        doc = serializer.save(created_by=self.request.user, number=NumberSeries.next_number("payroll"))
        engine.calculate(doc)

    def _editable(self, doc):
        ensure_not_marked(doc)
        if doc.status == "approved":
            raise ValidationError({"detail": "Calculul este aprobat; redeschideți-l întâi (drept de aprobare)."})

    def perform_update(self, serializer):
        self._editable(serializer.instance)
        serializer.save()

    def check_delete(self, instance):
        self._editable(instance)

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        doc = self.get_object()
        lines = doc.lines.select_related("employee", "employment").prefetch_related("items__pay_type").order_by("sort", "id")
        payments = doc.payments.filter(deletion_mark=False).order_by("date", "id")
        return Response({**PayrollSerializer(doc).data, "lines": PayrollLineSerializer(lines, many=True).data,
                         "types": PayTypeSerializer(PayType.objects.filter(is_active=True), many=True).data,
                         "payments": [{"id": x.id, "number": x.number, "date": x.date, "status": x.status,
                                       "status_label": x.get_status_display()} for x in payments]})

    @action(detail=True, methods=["post"])
    def calculate(self, request, pk=None):
        doc = self.get_object()
        self._editable(doc)
        return Response(engine.calculate(doc))

    @action(detail=True, methods=["post"])
    def check(self, request, pk=None):
        doc = self.get_object()
        self._editable(doc)
        doc.status = "checked"
        doc.save(update_fields=["status"])
        return Response(PayrollSerializer(doc).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        doc = self.get_object()
        if not doc.lines.exists():
            raise ValidationError({"detail": "Calculul nu are rânduri."})
        doc.status, doc.approved_by, doc.approved_at = "approved", request.user, timezone.now()
        doc.save(update_fields=["status", "approved_by", "approved_at"])
        return Response(PayrollSerializer(doc).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        doc = self.get_object()
        done = list(doc.payments.filter(status__in=("approved", "paid"), deletion_mark=False).values_list("number", flat=True))
        if done:
            raise ValidationError({"detail": "În baza calculului sunt îndreptări spre plată aprobate (nr. " + ", ".join(done)
                                             + "); redeschideți-le întâi."})
        doc.status, doc.approved_by, doc.approved_at = "draft", None, None
        doc.save(update_fields=["status", "approved_by", "approved_at"])
        return Response(PayrollSerializer(doc).data)

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        return printing.print_sheet(request, self.get_object())


class PayrollItemViewSet(viewsets.ModelViewSet):
    """Rândurile scrise de mână în calcul: corectarea unei sume calculate (salariul, un spor, CAS — rândul de mână îl
    înlocuiește pe cel calculat) sau un rând nou (premiu unic, reținere). După salvare se refac rândurile angajatului și
    bazele lui. Un rând de mână de același tip pe același raport se înlocuiește, nu se dublează."""

    perm_module = "payroll"
    serializer_class = PayrollItemSerializer
    pagination_class = None
    perm_actions = {"create": "edit", "update": "edit", "partial_update": "edit", "destroy": "edit"}

    def get_queryset(self):
        qs = PayrollItem.objects.select_related("pay_type", "line__payroll")
        if self.request.query_params.get("line"):
            return qs.filter(line_id=self.request.query_params["line"])
        return qs.none() if self.action == "list" else qs

    @staticmethod
    def _check(line: PayrollLine):
        if line.payroll.status == "approved":
            raise ValidationError({"detail": "Calculul este aprobat; redeschideți-l întâi."})

    def _amount(self, serializer):
        try:
            return Decimal(str(serializer.validated_data.get("amount", getattr(serializer.instance, "amount", 0))))
        except InvalidOperation:
            raise ValidationError({"amount": "Nu este un număr."}) from None

    def perform_create(self, serializer):
        line = serializer.validated_data["line"]
        self._check(line)
        if serializer.validated_data["pay_type"].auto in engine.AT_PAYMENT:
            raise ValidationError({"pay_type": "Impozitul pe venit, CNAM și avansul se rețin la plată — se corectează în "
                                               "îndreptarea spre plată, nu în calcul."})
        amount = self._amount(serializer)
        t = serializer.validated_data["pay_type"]
        same = line.items.filter(manual=True, pay_type=t).order_by("id")
        if same.exists():  # aceeași corectare a doua oară: se schimbă suma, nu se adaugă încă un rând
            item = same.first()
            same.exclude(pk=item.pk).delete()
            item.amount, item.note = amount, serializer.validated_data.get("note", item.note)
            item.save(update_fields=["amount", "note"])
            serializer.instance = item
        else:
            serializer.save(manual=True, amount=amount)
        engine.calculate(line.payroll, employee_id=line.employee_id)

    def perform_update(self, serializer):
        line = serializer.instance.line
        if not serializer.instance.manual:
            raise ValidationError({"detail": "Rândul calculat se corectează adăugând un rând de mână de același tip."})
        self._check(line)
        serializer.save(manual=True, amount=self._amount(serializer))
        engine.calculate(line.payroll, employee_id=line.employee_id)

    def perform_destroy(self, instance):
        if not instance.manual:
            raise ValidationError({"detail": "Rândul calculat automat nu se șterge."})
        line = instance.line
        self._check(line)
        instance.delete()
        engine.calculate(line.payroll, employee_id=line.employee_id)
