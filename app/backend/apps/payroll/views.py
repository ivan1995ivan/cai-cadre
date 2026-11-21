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

from . import dependencies, engine, formula, printing
from .models import (EmployeePayItem, ExemptionRequest, OccupationPayItem, PayConstant, PayItemChange, Payroll, PayrollItem,
                     PayrollLine, PayType)
from .serializers import (EmployeePayItemSerializer, ExemptionRequestSerializer, OccupationPayItemSerializer, PayConstantSerializer,
                          PayItemChangeSerializer, PayrollItemSerializer, PayrollLineSerializer, PayrollSerializer, PayTypeSerializer)


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
    perm_actions = {**SETTINGS_ACTIONS, "try_saved": "view", "try_draft": "view", "variables": "view",
                    "check_formula": "view"}
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
        users = dependencies.users_of(instance.code, PayType.objects.exclude(pk=instance.pk))
        if users:
            raise ValidationError({"detail": f"Tipul {instance.code} e folosit în baza / formula tipurilor "
                                             f"{', '.join(t.code for t in users)}; scoateți-l de acolo întâi."})

    @action(detail=False, methods=["get"])
    def variables(self, request):
        """Pentru editorul formulei: variabilele, funcțiile și constantele cu descrierea lor."""
        names = {}
        for c in PayConstant.objects.order_by("code", "-date_from"):
            names.setdefault(c.code, c.name)
        return Response({
            "variables": [{"name": k, "ro": v[0], "ru": v[1], "en": v[2]} for k, v in formula.VARIABLES.items()],
            "functions": [{"name": k, "ro": v[0], "ru": v[1], "en": v[2]} for k, v in formula.FUNCTIONS.items()],
            "constants": [{"code": k, "name": v} for k, v in names.items()],
        })

    @action(detail=False, methods=["post"], url_path="check")
    def check_formula(self, request):
        """Verificarea pe loc a formulei din editor (fără salvare): eroarea cu poziția sau ce folosește."""
        try:
            parsed = formula.check(request.data.get("expression") or "",
                                   type_codes=set(PayType.objects.values_list("code", flat=True)) | {request.data.get("code") or ""},
                                   constant_codes=set(PayConstant.objects.values_list("code", flat=True)))
        except formula.FormulaError as exc:
            return Response({"ok": False, "error": exc.message, "position": exc.position})
        return Response({"ok": True, "variables": parsed.variables, "constants": parsed.constants, "refs": parsed.refs})

    def _try(self, request, pay_type, replaces=None):
        data = request.data
        require_payroll_view(request.user)
        employee = Employee.objects.filter(pk=data.get("employee")).first()
        if employee is None or not staff.can_see(employee, request.user, "payroll"):
            raise ValidationError({"employee": "Alegeți angajatul."})
        job = None
        if data.get("employment"):
            job = employee.employments.filter(pk=data["employment"]).first()
            if job is None:
                raise ValidationError({"employment": "Raportul de muncă este al altui angajat."})
        try:
            year, month = int(data.get("year")), int(data.get("month"))
        except (TypeError, ValueError):
            raise ValidationError({"month": "Alegeți luna."}) from None
        if not 1 <= month <= 12:
            raise ValidationError({"month": "Luna este între 1 și 12."})
        row = None
        if any(data.get(k) not in (None, "") for k in ("amount", "percent", "quantity")):
            try:
                row = {k: (Decimal(str(data[k]).replace(",", ".")) if data.get(k) not in (None, "") else None)
                       for k in ("amount", "percent", "quantity")}
            except InvalidOperation:
                raise ValidationError({"amount": "Suma, procentul și cantitatea sunt numere."}) from None
        try:
            result = engine.try_type(pay_type, employee=employee, employment=job, year=year, month=month, row_values=row,
                                     replaces=replaces)
        except ValidationError as exc:
            detail = exc.detail.get("detail", exc.detail) if isinstance(exc.detail, dict) else exc.detail
            return Response({"lines": [], "errors": [str(detail[0] if isinstance(detail, list) else detail)]})
        descriptions = variable_descriptions(request)
        for ln in result["lines"]:
            for tr in ln["traces"]:
                tr["variables"] = [{"name": k, "value": v, "description": descriptions.get(k, "")} for k, v in tr["variables"].items()]
        result["errors"] = [ln["error"] for ln in result["lines"] if ln["error"]]
        return Response(result)

    @action(detail=True, methods=["post"], url_path="try")
    def try_saved(self, request, pk=None):
        """„Încearcă pe un angajat” cu tipul salvat: POST {employee, employment?, year, month, amount?, percent?, quantity?}."""
        return self._try(request, self.get_object())

    @action(detail=False, methods=["post"], url_path="try")
    def try_draft(self, request):
        """„Încearcă” cu tipul scris în editor (nesalvat): câmpurile tipului + angajatul și luna; `id` — tipul pe care îl
        înlocuiește. Formula se verifică la fel ca la salvare."""
        from .serializers import check_type

        instance = PayType.objects.filter(pk=request.data.get("id")).first() if request.data.get("id") else None
        ser = PayTypeSerializer(instance, data=request.data, partial=instance is not None)
        try:
            ser.is_valid(raise_exception=True)
            cand = check_type(instance, ser.validated_data)
        except ValidationError as exc:
            detail = exc.detail
            text = "; ".join(f"{v[0] if isinstance(v, list) else v}" for v in detail.values()) if isinstance(detail, dict) else str(detail)
            return Response({"lines": [], "errors": [text]})
        if not cand.code:
            cand.code = "NOU"
        return self._try(request, cand, replaces=instance.code if instance else None)


def require_payroll_view(user):
    from apps.users.permissions import require

    require(user, "payroll.view")


def variable_descriptions(request) -> dict:
    """Descrierea variabilelor, constantelor și tipurilor (pentru „Încearcă”), în limba utilizatorului."""
    lang = {"ru": 1, "en": 2}.get(getattr(request.user, "language", "") or request.query_params.get("lang", ""), 0)
    out = {k: v[lang] for k, v in formula.VARIABLES.items()}
    for c in PayConstant.objects.order_by("code", "-date_from"):
        out.setdefault(f"C.{c.code}", c.name)
    for t in PayType.objects.all():
        out[f"[{t.code}]"] = [t.name_ro, t.name_ru or t.name_ro, t.name_en or t.name_ro][lang]
    return out


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
        qs = super().get_queryset().select_related("pay_type", "employment__occupation", "order_item__order", "change_line__change")
        if self.request.query_params.get("current"):  # fără istoric: doar rândurile în vigoare și cele viitoare
            qs = qs.exclude(date_to__lt=timezone.localdate())
        return qs

    def perform_destroy(self, instance):
        if instance.from_document:
            raise ValidationError({"detail": "Rândul vine dintr-un document; se oprește printr-un ordin sau prin „Modificarea "
                                             "acumulărilor planificate”, iar anularea documentului îl scoate."})
        instance.delete()


class ExemptionRequestViewSet(EmployeeScopedMixin, viewsets.ModelViewSet):
    model = ExemptionRequest
    serializer_class = ExemptionRequestSerializer

    def get_queryset(self):
        return super().get_queryset().prefetch_related("dependents__family_member")

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        """Tiparul cererii (anexa 6 la Regulamentul aprobat prin HG 697/2014)."""
        from .payment_printing import print_exemption_request

        return print_exemption_request(request, self.get_object())


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


# --- acumulările-tip ale funcției ------------------------------------------------------------------------------------
class OccupationPayItemViewSet(viewsets.ModelViewSet):
    """Acumulările-tip ale funcției (clasificatorul funcțiilor): la angajare completează tabelul din ordin. Le citește și cine
    face ordine; le schimbă cine schimbă clasificatoarele sau setările salariului."""

    serializer_class = OccupationPayItemSerializer
    pagination_class = None

    @property
    def perm_module(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return ("dictionaries", "payroll_settings", "orders")
        return ("dictionaries", "payroll_settings")

    def get_queryset(self):
        qs = OccupationPayItem.objects.select_related("pay_type")
        occ = self.request.query_params.get("occupation")
        if occ:
            return qs.filter(occupation_id=occ)
        return qs if self.action != "list" else qs.none()


# --- documentul „Modificarea acumulărilor planificate” -----------------------------------------------------------------
class PayItemChangeViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "payroll"
    serializer_class = PayItemChangeSerializer
    perm_actions = {"approve": "approve", "unapprove": "approve", "print": "view"}

    def get_queryset(self):
        qs = PayItemChange.objects.prefetch_related("lines__employee", "lines__pay_type", "lines__employment__occupation")
        if staff.visible_subdivision_ids(self.request.user, "payroll") is not None:  # doar documentele angajaților văzuți
            visible = staff.scope_employees(Employee.objects.all(), self.request.user, "payroll")
            qs = qs.exclude(lines__employee__in=Employee.objects.exclude(pk__in=visible))
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("year"):
            qs = qs.filter(date__year=p["year"])
        if p.get("employee"):
            qs = qs.filter(lines__employee_id=p["employee"])
        return qs.distinct()

    def _check_lines(self, serializer):
        for ln in serializer.validated_data.get("lines") or []:
            if not staff.can_see(ln["employee"], self.request.user, "payroll"):
                raise PermissionDenied("Angajatul nu este în subdiviziunile dvs.")

    def perform_create(self, serializer):
        self._check_lines(serializer)
        serializer.save(created_by=self.request.user, number=NumberSeries.next_number("pay_item_change"))

    def _editable(self, doc):
        ensure_not_marked(doc)
        if doc.status != "draft":
            raise ValidationError({"detail": "Documentul este aprobat; anulați întâi aprobarea (drept de aprobare)."})

    def perform_update(self, serializer):
        self._editable(serializer.instance)
        self._check_lines(serializer)
        serializer.save()

    def check_delete(self, instance):
        self._editable(instance)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Aprobarea: fiecare rând intră în fila „Salariu” (adaugă / modifică / oprește); o eroare oprește tot."""
        from django.db import transaction

        from . import planned

        with transaction.atomic():
            doc = PayItemChange.objects.select_for_update().get(pk=self.get_object().pk)
            self._editable(doc)
            lines = list(doc.lines.select_related("employee", "employment", "pay_type", "target").order_by("sort", "id"))
            if not lines:
                raise ValidationError({"detail": "Documentul nu are rânduri."})
            for n, ln in enumerate(lines, start=1):
                res = planned.apply({"pay_type": ln.pay_type, "action": ln.action, "amount": ln.amount, "percent": ln.percent,
                                     "quantity": ln.quantity, "date_from": ln.date_from, "date_to": ln.date_to,
                                     "document": ln.document, "target": ln.target_id},
                                    employee=ln.employee, employment=ln.employment, default_from=doc.date,
                                    reference=f"Modificarea acumulărilor {doc.reference()}",
                                    who=f"Rândul {n} ({ln.employee.full_name()})", source={"change_line": ln})
                ln.result = {"items": [res]}
                ln.save(update_fields=["result"])
            doc.status, doc.approved_by, doc.approved_at = "approved", request.user, timezone.now()
            doc.save(update_fields=["status", "approved_by", "approved_at"])
        return Response(PayItemChangeSerializer(doc).data)

    @action(detail=True, methods=["post"])
    def unapprove(self, request, pk=None):
        """Anularea aprobării: rândurile din fila „Salariu” revin exact la starea dinainte (în ordine inversă)."""
        from django.db import transaction

        from . import planned

        with transaction.atomic():
            doc = PayItemChange.objects.select_for_update().get(pk=self.get_object().pk)
            if doc.status != "approved":
                raise ValidationError({"detail": "Documentul nu este aprobat."})
            for ln in doc.lines.select_related("employee").order_by("-sort", "-id"):
                planned.undo((ln.result or {}).get("items"), f"Rândul {ln.sort // 10} ({ln.employee.full_name()})")
                ln.result = {}
                ln.save(update_fields=["result"])
            doc.status, doc.approved_by, doc.approved_at = "draft", None, None
            doc.save(update_fields=["status", "approved_by", "approved_at"])
        return Response(PayItemChangeSerializer(doc).data)

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        from .change_printing import print_change

        return print_change(request, self.get_object())
