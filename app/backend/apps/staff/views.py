from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import Prefetch, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.deletion import DeletionMarkMixin
from apps.org.models import DictItem

from . import printing, services
from .models import (AccessLog, Education, Employee, EmployeeDocument, Employment, FamilyMember, FunctionCombination,
                     MilitaryRecord, PriorExperience)
from .serializers import (AccessLogSerializer, ContractRowSerializer, EducationSerializer, EmployeeDocumentSerializer, EmployeeListSerializer,
                          EmployeeSerializer, EmploymentSerializer, FamilyMemberSerializer, FunctionCombinationSerializer,
                          MilitaryRecordSerializer, PriorExperienceSerializer)


def _date(value, field="date"):
    try:
        return date.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        raise ValidationError({field: "Data se scrie AAAA-LL-ZZ."}) from None


def log_access(employee, user, action="view", detail=""):
    AccessLog.objects.create(employee=employee, user=user, action=action, detail=detail[:120])


class EmployeeViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "employees"
    perm_actions = {"seniority": "view", "summary": "view", "access_log": "view", "archive": "edit", "print": "view", "next_number": "create",
                    "export_list": "export", "print_list": "view"}
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        return EmployeeListSerializer if self.action in ("list", "export_list", "print_list") else EmployeeSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "with_seniority": self.action == "retrieve"}

    def get_queryset(self):
        p = self.request.query_params
        qs = Employee.objects.prefetch_related(
            Prefetch("employments", queryset=Employment.objects.select_related("subdivision", "occupation")))
        qs = services.scope_employees(qs, self.request.user)
        if p.get("q"):
            q = p["q"].strip()
            cond = Q(last_name__icontains=q) | Q(first_name__icontains=q) | Q(tab_number=q) | Q(patronymic__icontains=q)
            if q.isdigit() and len(q) == 13:
                cond |= Q(idnp=q)
            parts = q.split()
            if len(parts) >= 2:
                cond |= Q(last_name__icontains=parts[0], first_name__icontains=parts[1])
            qs = qs.filter(cond)
        if p.get("ids"):  # denumirile angajaților deja aleși într-un câmp (fără deschiderea dosarului, deci fără jurnal)
            qs = qs.filter(pk__in=[int(x) for x in p["ids"].split(",") if x.strip().isdigit()][:100])
        # filtrul de stare e doar pentru liste: dosarul unui angajat eliberat sau arhivat se deschide oricând
        status = p.get("status", "current") if self.action in ("list", "print_list", "export_list") else "all"
        if status == "current":
            qs = qs.filter(status__in=("active", "suspended"), is_archived=False)
        elif status in ("active", "suspended", "dismissed", "candidate"):
            qs = qs.filter(status=status)
        elif status == "archived":
            qs = qs.filter(is_archived=True)
        active_jobs = Q(employments__status__in=("active", "suspended"))
        if p.get("subdivision"):
            from apps.org.models import Subdivision

            sub = Subdivision.objects.filter(pk=p["subdivision"]).first()
            ids = sub.descendant_ids() if sub and p.get("with_children", "1") == "1" else {p["subdivision"]}
            qs = qs.filter(active_jobs, employments__subdivision_id__in=ids)
        if p.get("occupation"):
            qs = qs.filter(active_jobs, employments__occupation_id=p["occupation"])
        if p.get("category") == "none":
            qs = qs.filter(active_jobs, employments__occupation__category__isnull=True)
        elif str(p.get("category") or "").isdigit():
            qs = qs.filter(active_jobs, employments__occupation__category_id=p["category"])
        if p.get("kind"):
            qs = qs.filter(active_jobs, employments__kind=p["kind"])
        if p.get("sex") in ("M", "F"):
            qs = qs.filter(sex=p["sex"])
        return qs.distinct().order_by("last_name", "first_name", "patronymic", "id")

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        log_access(obj, request.user, "view")
        return Response(self.get_serializer(obj).data)

    def perform_create(self, serializer):
        tab = serializer.validated_data.get("tab_number") or services.next_tab_number()
        serializer.save(tab_number=tab)

    def check_delete(self, instance):
        if instance.employments.exists():
            raise ValidationError({"detail": "Angajatul are raporturi de muncă: dosarul nu se șterge, se arhivează."})

    @action(detail=False, methods=["get"], url_path="next-number")
    def next_number(self, request):
        return Response({"tab_number": services.next_tab_number()})

    @action(detail=True, methods=["get"])
    def seniority(self, request, pk=None):
        s = services.seniority(self.get_object(), _date(request.query_params.get("date")))
        lang = request.user.language or "ro"
        return Response({k: ({**v, "text": services.seniority_text(v, lang)} if isinstance(v, dict) else v) for k, v in s.items()})

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        """Fișa scurtă pentru lista angajaților (la trecerea mouse-ului): fotografia, vârsta, vechimea, raporturile de muncă,
        absența de azi, concediul disponibil, mărimile. Nu se scrie în jurnalul accesului (nu e deschiderea
        dosarului); câmpurile sensibile se ascund după aceleași reguli ca în dosar."""
        from .serializers import hidden_for

        e = self.get_object()
        today = date.today()
        lang = request.user.language or "ro"
        age = None
        if e.birth_date:
            age = today.year - e.birth_date.year - ((today.month, today.day) < (e.birth_date.month, e.birth_date.day))
        jobs = [{"kind": j.get_kind_display(), "occupation": j.occupation.local_name(lang) if j.occupation_id else "",
                 "subdivision": j.subdivision.local_name(lang) if j.subdivision_id else "", "rate": float(j.rate),
                 "date_from": j.date_from, "date_to": j.date_to, "status": j.get_status_display()}
                for j in e.employments.select_related("occupation", "subdivision").exclude(status="ended").order_by("date_from")]
        sen = services.seniority(e)
        seniority = {k: services.seniority_text(v, lang) for k, v in sen.items() if k != "on_date"}
        out = {"id": e.pk, "full_name": e.full_name(), "tab_number": e.tab_number, "photo": e.photo.url if e.photo else None,
               "sex": e.sex, "birth_date": e.birth_date, "age": age, "status": e.get_status_display(), "phone": e.phone,
               "email": e.email, "jobs": jobs, "seniority": seniority,
               "clothing_size": e.clothing_size, "shoe_size": e.shoe_size, "height": e.height, "absence": None, "leave": None}
        if request.user.has_crm_perm("leave.view"):
            from apps.leave import balance
            from apps.leave.models import Absence

            a = Absence.objects.filter(employee=e, date_from__lte=today, date_to__gte=today).first()
            if a:
                out["absence"] = {"kind": a.get_kind_display(), "date_from": a.date_from, "date_to": a.date_to}
            try:
                bal = balance.balance(e, today)
                out["leave"] = {"available": bal.get("available"), "remaining": bal.get("remaining")}
            except Exception:  # fără raport de muncă de bază: fără sold
                out["leave"] = None
        for field in hidden_for(request) & set(out):
            out[field] = None
        return Response(out)

    @action(detail=True, methods=["get"], url_path="access-log")
    def access_log(self, request, pk=None):
        if not request.user.has_crm_perm("audit.view") and not request.user.has_crm_perm("employees.sensitive"):
            raise PermissionDenied("Jurnalul accesului îl văd cei cu drept de audit.")
        return Response(AccessLogSerializer(self.get_object().access_log.select_related("user")[:200], many=True).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        emp = self.get_object()
        archived = bool(request.data.get("archived", True))
        if archived and emp.employments.exclude(status="ended").exists():
            raise ValidationError({"detail": "Se arhivează doar dosarul angajatului eliberat."})
        emp.is_archived = archived
        emp.save(update_fields=["is_archived"])
        return Response(EmployeeSerializer(emp, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        emp = self.get_object()
        doc = request.query_params.get("doc", "employee_card")
        if doc not in printing.EMPLOYEE_DOCS:
            raise ValidationError({"doc": "Formular necunoscut."})
        if doc == "certificate_salary" and not request.user.has_crm_perm("payroll.view"):
            raise PermissionDenied("Adeverința privind salariul o tipărește cine are dreptul de a vedea salarizarea.")
        log_access(emp, request.user, "print", doc)
        return printing.print_employee(request, emp, doc)

    @action(detail=False, methods=["get"], url_path="print-list")
    def print_list(self, request):
        return printing.print_list(request, self.get_queryset())


class EmployeeChildViewSet(viewsets.ModelViewSet):
    """Filele dosarului (acte, familie, studii...): se văd și se schimbă doar pentru angajații vizibili."""

    perm_module = "employees"
    pagination_class = None
    model = None
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    sensitive = False  # filele cu date sensibile cer și dreptul employees.sensitive

    def get_queryset(self):
        qs = self.model.objects.select_related("employee")
        emp = self.request.query_params.get("employee")
        if self.action == "list":
            if not emp:
                return qs.none()
            qs = qs.filter(employee_id=emp)
        visible = services.scope_employees(Employee.objects.all(), self.request.user)
        return qs.filter(employee__in=visible)

    def check_permissions(self, request):
        super().check_permissions(request)
        if self.sensitive and not request.user.has_crm_perm("employees.sensitive"):
            raise PermissionDenied("Această filă conține date sensibile.")

    def _check_employee(self, employee):
        if not services.can_see(employee, self.request.user):
            raise NotFound()

    def perform_create(self, serializer):
        self._check_employee(serializer.validated_data["employee"])
        serializer.save()

    def perform_update(self, serializer):
        if "employee" in serializer.validated_data and serializer.validated_data["employee"] != serializer.instance.employee:
            raise ValidationError({"employee": "Înregistrarea nu se mută la alt angajat."})
        serializer.save()


class DocumentViewSet(EmployeeChildViewSet):
    model = EmployeeDocument
    serializer_class = EmployeeDocumentSerializer
    sensitive = True

    def get_queryset(self):
        return super().get_queryset().select_related("doc_type")


class FamilyViewSet(EmployeeChildViewSet):
    model = FamilyMember
    serializer_class = FamilyMemberSerializer

    def check_permissions(self, request):
        super().check_permissions(request)
        if "family" in request.user.hidden_fields():
            raise PermissionDenied("Datele despre familie sunt ascunse pentru rolul dvs.")


class EducationViewSet(EmployeeChildViewSet):
    model = Education
    serializer_class = EducationSerializer


class ExperienceViewSet(EmployeeChildViewSet):
    model = PriorExperience
    serializer_class = PriorExperienceSerializer


class MilitaryViewSet(EmployeeChildViewSet):
    """Fișa de evidență militară — doar cu modulul opțional „Evidența militară” pornit (Constante → Module)."""

    perm_module = ("employees", "military")
    model = MilitaryRecord
    serializer_class = MilitaryRecordSerializer

    def initial(self, request, *args, **kwargs):
        from apps.core.models import Company

        super().initial(request, *args, **kwargs)  # întâi autentificarea și drepturile
        if not Company.get().military_enabled:
            raise NotFound("Modulul „Evidența militară” este oprit.")

    def perform_create(self, serializer):
        self._check_employee(serializer.validated_data["employee"])
        if MilitaryRecord.objects.filter(employee=serializer.validated_data["employee"]).exists():
            raise ValidationError({"detail": "Angajatul are deja fișa de evidență militară."})
        serializer.save()


class EmploymentViewSet(EmployeeChildViewSet):
    """Raporturile de muncă. Angajarea, modificarea, suspendarea și încetarea trec prin services (cu istoric);
    din Etapa 3 le fac ordinele — aici rămân pentru datele inițiale și corecții."""

    perm_module = ("employees", "contracts")
    perm_actions = {"change": "edit", "suspend": "edit", "resume": "edit", "terminate": "edit"}
    model = Employment
    serializer_class = EmploymentSerializer

    def get_queryset(self):
        p = self.request.query_params
        if self.action == "list" and p.get("all") == "1":
            # registrul contractelor: toate raporturile angajaților vizibili, cu filtre
            visible = services.scope_employees(Employee.objects.all(), self.request.user)
            qs = Employment.objects.filter(employee__in=visible).select_related("employee", "subdivision", "occupation",
                                                                                "termination_reason")
            if p.get("status") in ("active", "suspended", "ended"):
                qs = qs.filter(status=p["status"])
            elif p.get("status") != "all":
                qs = qs.exclude(status="ended")
            if p.get("kind"):
                qs = qs.filter(kind=p["kind"])
            if p.get("subdivision"):
                qs = qs.filter(subdivision_id=p["subdivision"])
            if p.get("q"):
                qs = qs.filter(Q(employee__last_name__icontains=p["q"]) | Q(employee__first_name__icontains=p["q"])
                               | Q(contract_number__icontains=p["q"]) | Q(employee__tab_number=p["q"]))
            days = p.get("expiring")
            if days and days.isdigit():
                limit = date.today() + timedelta(days=int(days))
                qs = qs.exclude(status="ended").filter(Q(date_to__lte=limit) | Q(probation_until__gte=date.today(),
                                                                                  probation_until__lte=limit))
            return qs.order_by("employee__last_name", "employee__first_name", "date_from")
        return super().get_queryset().select_related("subdivision", "occupation", "termination_reason").prefetch_related(
            "history__subdivision", "history__occupation")

    def get_serializer(self, *args, **kwargs):
        if self.action == "list" and self.request.query_params.get("all") == "1":
            kwargs["context"] = self.get_serializer_context()
            return ContractRowSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        data = dict(serializer.validated_data)
        employee = data.pop("employee")
        self._check_employee(employee)
        order = data.pop("hire_order", "")
        serializer.instance = services.hire(employee, user=self.request.user, order=order, **data)

    def perform_update(self, serializer):
        # valorile cu istoric (funcție, secție, normă, salariu) se schimbă prin „Modificare”, nu prin editare simplă
        tracked = {"subdivision", "occupation", "rate", "base_salary", "allowance_pct", "pay_mode", "hourly_rate", "employee", "kind",
                   "date_from"}
        changed = {k for k, v in serializer.validated_data.items() if k in tracked and getattr(serializer.instance, k) != v}
        if changed and not self.request.data.get("correction"):
            raise ValidationError({"detail": "Funcția, subdiviziunea, norma și salariul se schimbă prin „Modificare” "
                                             "(rămân în istoric). Pentru o greșeală de introducere bifați „Corectare”."})
        emp = serializer.save()
        if changed:  # corectare: prima înregistrare din istoric primește valorile corecte
            first = emp.history.order_by("date", "id").first()
            if first:
                for f in services.SNAPSHOT_FIELDS:
                    setattr(first, f, getattr(emp, f))
                first.date = emp.date_from
                first.save()

    def perform_destroy(self, instance):
        if instance.history.exclude(event__in=("hire", "import")).exists():
            raise ValidationError({"detail": "Raportul are modificări în istoric și nu se șterge."})
        employee = instance.employee
        instance.delete()
        services.refresh_status(employee)

    def _emp(self):
        return self.get_object()

    @action(detail=True, methods=["post"])
    def change(self, request, pk=None):
        emp = self._emp()
        fields = {}
        from apps.org.models import Occupation, Subdivision

        for name, model in (("subdivision", Subdivision), ("occupation", Occupation)):
            if request.data.get(name):
                obj = model.objects.filter(pk=request.data[name]).first()
                if obj is None:
                    raise ValidationError({name: "Nu există."})
                if obj.pk != getattr(emp, f"{name}_id"):
                    fields[name] = obj
        mode = request.data.get("pay_mode")
        if mode and mode != emp.pay_mode:
            fields["pay_mode"] = mode
        for f in ("rate", "base_salary", "allowance_pct", "hourly_rate"):
            if request.data.get(f) not in (None, ""):
                try:
                    value = Decimal(str(request.data[f]).replace(",", "."))
                except InvalidOperation:
                    raise ValidationError({f: "Nu este un număr."}) from None
                if value != getattr(emp, f):
                    fields[f] = value
        if not fields:
            raise ValidationError({"detail": "Nu s-a schimbat nimic."})
        day = _date(request.data.get("date")) or date.today()
        services.change(emp, day, user=request.user, order=request.data.get("order", ""),
                        note=request.data.get("note", ""), **fields)
        return Response(self.get_serializer(Employment.objects.get(pk=emp.pk)).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        emp = services.suspend(self._emp(), _date(request.data.get("date")) or date.today(), request.data.get("reason", ""),
                               user=request.user, order=request.data.get("order", ""))
        return Response(self.get_serializer(emp).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        emp = services.resume(self._emp(), _date(request.data.get("date")) or date.today(), user=request.user,
                              order=request.data.get("order", ""))
        return Response(self.get_serializer(emp).data)

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        reason = DictItem.objects.filter(kind="termination", pk=request.data.get("reason")).first()
        day = _date(request.data.get("date"), "end_date")
        if day is None:
            raise ValidationError({"end_date": "Data încetării este obligatorie."})
        emp = services.terminate(self._emp(), day, reason, user=request.user, order=request.data.get("order", ""),
                                 note=request.data.get("note", ""))
        return Response(self.get_serializer(emp).data)


class FunctionCombinationViewSet(viewsets.ModelViewSet):
    """Cumularea funcțiilor / suplinirea / interimatul pe raportul de muncă (fila „Raporturi de muncă”); de regulă vin din
    ordine, aici — datele inițiale și corecțiile. Cele din ordine se schimbă doar prin ordin."""

    perm_module = ("employees", "contracts")
    serializer_class = FunctionCombinationSerializer
    pagination_class = None

    def get_queryset(self):
        qs = FunctionCombination.objects.select_related("employment__employee", "occupation", "subdivision", "hour_type",
                                                        "order_item__order")
        p = self.request.query_params
        if p.get("employment"):
            qs = qs.filter(employment_id=p["employment"])
        elif p.get("employee"):
            qs = qs.filter(employment__employee_id=p["employee"])
        elif self.action == "list":
            return qs.none()
        visible = services.scope_employees(Employee.objects.all(), self.request.user)
        return qs.filter(employment__employee__in=visible)

    def perform_create(self, serializer):
        if not services.can_see(serializer.validated_data["employment"].employee, self.request.user):
            raise NotFound()
        serializer.save()

    def perform_update(self, serializer):
        if "employment" in serializer.validated_data and serializer.validated_data["employment"] != serializer.instance.employment:
            raise ValidationError({"employment": "Înregistrarea nu se mută la alt raport."})
        serializer.save()

    def perform_destroy(self, instance):
        if instance.order_item_id:
            raise ValidationError({"detail": "Cumularea vine dintr-un ordin; se scoate prin anularea ordinului."})
        instance.delete()
