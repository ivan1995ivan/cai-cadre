from datetime import date

from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.deletion import DeletionMarkMixin, ensure_not_marked
from apps.org.models import Subdivision
from apps.staff import services as staff
from apps.staff.models import Employment

from . import export, hour_types, printing, services
from .models import (CalendarDay, HourType, JobHourRate, JobSchedule, OccupationHourRate, Roster, RosterLine, ShiftType, Timesheet,
                     TimesheetLine, WorkSchedule)
from .serializers import (CalendarDaySerializer, HourTypeSerializer, JobHourRateSerializer, JobScheduleSerializer,
                          OccupationHourRateSerializer, RosterLineSerializer, RosterSerializer, ShiftTypeSerializer,
                          TimesheetLineSerializer, TimesheetSerializer, WorkScheduleSerializer)


# --- clasificatoarele: turele, graficele de lucru, calendarul --------------------------------------------------
class ShiftTypeViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = ("worktime", "dictionaries")
    serializer_class = ShiftTypeSerializer
    pagination_class = None
    queryset = ShiftType.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(is_active=True, deletion_mark=False) if self.request.query_params.get("active") else qs


class HourTypeViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    """Clasificatorul tipurilor de ore (Setări → Tipuri de ore)."""

    perm_module = ("worktime", "dictionaries")
    serializer_class = HourTypeSerializer
    pagination_class = None

    def get_queryset(self):
        qs = HourType.objects.select_related("pay_type")
        return qs.filter(is_active=True, deletion_mark=False) if self.request.query_params.get("active") else qs

    def check_delete(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "Tipul livrat cu sistemul nu se șterge; îl puteți face inactiv."})


class JobHourRateViewSet(viewsets.ModelViewSet):
    """Tarifele pe tipuri de ore ale raportului de muncă (fila „Raporturi de muncă”). Cele din ordine se schimbă doar prin ordin."""

    perm_module = ("employees", "contracts")
    serializer_class = JobHourRateSerializer
    pagination_class = None

    def get_queryset(self):
        qs = JobHourRate.objects.select_related("hour_type", "employment__employee", "order_item__order")
        p = self.request.query_params
        if p.get("employment"):
            qs = qs.filter(employment_id=p["employment"])
        elif p.get("employee"):
            qs = qs.filter(employment__employee_id=p["employee"])
        elif self.action == "list":
            return qs.none()
        return qs

    def _check(self, employment: Employment):
        if not staff.can_see(employment.employee, self.request.user):
            raise NotFound()

    def perform_create(self, serializer):
        self._check(serializer.validated_data["employment"])
        serializer.save()

    def perform_update(self, serializer):
        self._check(serializer.instance.employment)
        serializer.save()

    def perform_destroy(self, instance):
        self._check(instance.employment)
        if instance.order_item_id:
            raise ValidationError({"detail": "Tariful vine dintr-un ordin; se scoate prin anularea ordinului."})
        instance.delete()


class OccupationHourRateViewSet(viewsets.ModelViewSet):
    """Tarifele-tip pe ore ale funcției: la angajare completează tabelul „Tarife pe tipuri de ore” din ordin."""

    serializer_class = OccupationHourRateSerializer
    pagination_class = None

    @property
    def perm_module(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return ("dictionaries", "payroll_settings", "orders")
        return ("dictionaries", "payroll_settings")

    def get_queryset(self):
        qs = OccupationHourRate.objects.select_related("hour_type")
        occ = self.request.query_params.get("occupation")
        if occ:
            return qs.filter(occupation_id=occ)
        return qs if self.action != "list" else qs.none()


class WorkScheduleViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = ("worktime", "dictionaries")
    serializer_class = WorkScheduleSerializer
    pagination_class = None

    def get_queryset(self):
        qs = WorkSchedule.objects.annotate(jobs_count=Count("jobs", distinct=True))
        return qs.filter(is_active=True, deletion_mark=False) if self.request.query_params.get("active") else qs


class CalendarDayViewSet(viewsets.ModelViewSet):
    perm_module = ("worktime", "dictionaries")
    serializer_class = CalendarDaySerializer
    pagination_class = None

    def get_queryset(self):
        qs = CalendarDay.objects.all()
        if self.request.query_params.get("year"):
            qs = qs.filter(date__year=self.request.query_params["year"])
        return qs


class CalendarView(APIView):
    """Calendarul de producție pe an: zilele lucrătoare, sărbătorile și norma de ore pe lună (40 / 35 / 30 h)."""

    def get(self, request):
        year = int(request.query_params.get("year") or timezone.localdate().year)
        return Response({"year": year, "months": services.month_norms(year)})


class SettingsView(APIView):
    perm_module = "worktime"

    def get(self, request):
        return Response({**services.get_settings(), hour_types.SETTINGS_KEY: hour_types.settings()})

    def put(self, request):
        if not request.user.has_crm_perm("settings.edit"):
            raise PermissionDenied("Setările le schimbă administratorul.")
        from apps.core.models import SystemSetting

        cfg = services.get_settings()
        if hour_types.SETTINGS_KEY in request.data:
            cfg[hour_types.SETTINGS_KEY] = hour_types.check_settings(request.data[hour_types.SETTINGS_KEY])
        for key in ("min_rest_hours", "max_night_shifts"):
            if key in request.data:
                try:
                    cfg[key] = max(0, int(request.data.get(key) or 0))
                except (TypeError, ValueError):
                    raise ValidationError({key: "Un număr întreg."}) from None
        SystemSetting.write(services.SETTINGS_KEY, cfg)
        return Response(cfg)


class JobScheduleViewSet(viewsets.ModelViewSet):
    """Graficul de lucru al raportului de muncă (în fișa angajatului, fila „Raporturi de muncă”)."""

    perm_module = ("worktime", "employees")
    serializer_class = JobScheduleSerializer
    pagination_class = None

    def get_queryset(self):
        qs = JobSchedule.objects.select_related("schedule", "employment__employee")
        p = self.request.query_params
        if p.get("employment"):
            qs = qs.filter(employment_id=p["employment"])
        elif p.get("employee"):
            qs = qs.filter(employment__employee_id=p["employee"])
        elif self.action == "list":
            return qs.none()
        return qs

    def _check(self, employment: Employment):
        if not staff.can_see(employment.employee, self.request.user, "worktime"):
            raise NotFound()

    def perform_create(self, serializer):
        self._check(serializer.validated_data["employment"])
        serializer.save()

    def perform_update(self, serializer):
        self._check(serializer.instance.employment)
        serializer.save()


# --- documentele lunare ----------------------------------------------------------------------------------------
class MonthDocMixin(DeletionMarkMixin):
    perm_module = "worktime"
    model = None

    def _visible(self, qs):
        ids = services.visible_ids(self.request.user)
        return qs if ids is None else qs.filter(subdivision_id__in=ids)

    def get_queryset(self):
        qs = self._visible(self.model.objects.select_related("subdivision").annotate(lines_count=Count("lines", distinct=True)))
        p = self.request.query_params
        for key in ("year", "month", "status", "subdivision"):
            if p.get(key):
                qs = qs.filter(**{key: p[key]})
        return qs

    def _check_subdivision(self, sub: Subdivision):
        ids = services.visible_ids(self.request.user)
        if ids is not None and sub.pk not in ids:
            raise PermissionDenied("Subdiviziunea nu este a dvs.")

    def perform_create(self, serializer):
        self._check_subdivision(serializer.validated_data["subdivision"])
        doc = serializer.save(created_by=self.request.user)
        self.fill_new(doc)

    def _editable(self, doc):
        ensure_not_marked(doc)
        if doc.status in ("approved", "closed"):
            raise ValidationError({"detail": "Documentul este aprobat / închis; redeschideți-l întâi."})
        if doc.status == "submitted" and not self.request.user.has_crm_perm("worktime.approve"):
            raise ValidationError({"detail": "Documentul a fost transmis; îl mai schimbă doar resursele umane."})

    def perform_update(self, serializer):
        self._editable(serializer.instance)
        serializer.save()

    def check_delete(self, instance):
        if instance.status in ("approved", "closed"):
            raise ValidationError({"detail": "Documentul aprobat / închis nu se șterge."})

    def _set_status(self, doc, status, **extra):
        doc.status = status
        for k, v in extra.items():
            setattr(doc, k, v)
        doc.save()
        return Response(self.get_serializer(doc).data)


class RosterViewSet(MonthDocMixin, viewsets.ModelViewSet):
    model = Roster
    serializer_class = RosterSerializer
    perm_actions = {"report": "view", "fill": "edit", "submit": "edit", "approve": "approve", "reopen": "approve",
                    "print": "view", "copy_previous": "edit"}

    def fill_new(self, doc):
        services.fill_roster(doc)

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        roster = self.get_object()
        return Response({**RosterSerializer(roster).data, **services.roster_report(roster)})

    @action(detail=True, methods=["post"])
    def fill(self, request, pk=None):
        roster = self.get_object()
        self._editable(roster)
        return Response({"added": services.fill_roster(roster, overwrite=bool(request.data.get("overwrite")))})

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        roster = self.get_object()
        self._editable(roster)
        return self._set_status(roster, "submitted")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._set_status(self.get_object(), "approved", approved_by=request.user, approved_at=timezone.now())

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        return self._set_status(self.get_object(), "draft", approved_by=None, approved_at=None)

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        return printing.print_roster(request, self.get_object())


class RosterLineViewSet(viewsets.ModelViewSet):
    perm_module = "worktime"
    perm_actions = {"update": "edit", "partial_update": "edit", "create": "edit", "destroy": "edit"}
    serializer_class = RosterLineSerializer
    pagination_class = None

    def get_queryset(self):
        qs = RosterLine.objects.select_related("roster", "employment__employee")
        ids = services.visible_ids(self.request.user)
        if ids is not None:
            qs = qs.filter(roster__subdivision_id__in=ids)
        if self.request.query_params.get("roster"):
            return qs.filter(roster_id=self.request.query_params["roster"])
        return qs.none() if self.action == "list" else qs

    def _editable(self, roster):
        MonthDocMixin._editable(self, roster)

    def perform_create(self, serializer):
        roster = serializer.validated_data["roster"]
        ids = services.visible_ids(self.request.user)
        if ids is not None and roster.subdivision_id not in ids:
            raise PermissionDenied("Subdiviziunea nu este a dvs.")
        self._editable(roster)
        last = roster.lines.order_by("-sort").first()
        serializer.save(sort=(last.sort + 10) if last else 10)

    def perform_update(self, serializer):
        self._editable(serializer.instance.roster)
        serializer.save()

    def perform_destroy(self, instance):
        self._editable(instance.roster)
        instance.delete()


class TimesheetViewSet(MonthDocMixin, viewsets.ModelViewSet):
    model = Timesheet
    serializer_class = TimesheetSerializer
    perm_actions = {"report": "view", "fill": "edit", "submit": "edit", "close": "approve", "reopen": "approve",
                    "print": "view", "set_cell": "edit", "set_hours": "edit", "export_xlsx": "export"}

    def fill_new(self, doc):
        services.fill_timesheet(doc)

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        ts = self.get_object()
        return Response({**TimesheetSerializer(ts).data, **services.timesheet_report(ts)})

    @action(detail=True, methods=["post"])
    def fill(self, request, pk=None):
        ts = self.get_object()
        self._editable(ts)
        return Response({"added": services.fill_timesheet(ts, keep_manual=not request.data.get("reset"))})

    @action(detail=True, methods=["post"], url_path="set-cell")
    def set_cell(self, request, pk=None):
        ts = self.get_object()
        self._editable(ts)
        line = ts.lines.filter(pk=request.data.get("line")).first()
        if line is None:
            raise ValidationError({"line": "Rândul nu există."})
        try:
            day = int(request.data.get("day"))
        except (TypeError, ValueError):
            raise ValidationError({"day": "Ziua lipsește."}) from None
        line = services.set_cell(line, day, request.data.get("code", ""), request.data.get("hours"), request.data.get("night"))
        return Response(TimesheetLineSerializer(line).data)

    @action(detail=True, methods=["post"], url_path="set-hours")
    def set_hours(self, request, pk=None):
        """Orele unui tip pe linie: POST {line, code, days: {zi: ore}} sau {line, code, month: ore}; amândouă goale — se scot."""
        ts = self.get_object()
        self._editable(ts)
        line = ts.lines.filter(pk=request.data.get("line")).first()
        if line is None:
            raise ValidationError({"line": "Rândul nu există."})
        ht = HourType.objects.filter(code=str(request.data.get("code") or "").strip().upper()).first()
        if ht is None:
            raise ValidationError({"code": "Tipul de ore nu există."})
        days = request.data.get("days")
        if days is not None and not isinstance(days, dict):
            raise ValidationError({"days": "Zilele sunt un obiect {zi: ore}."})
        if (days or request.data.get("month") not in (None, "")) and (not ht.is_active or ht.deletion_mark):
            raise ValidationError({"code": f"Tipul de ore {ht.code} nu este activ."})
        hour_types.set_hours(line, ht, days=days, month=request.data.get("month"))
        return Response(services.timesheet_report(ts, only_line=line.pk)["rows"][0])

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        ts = self.get_object()
        self._editable(ts)
        return self._set_status(ts, "submitted", submitted_at=timezone.now())

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._set_status(self.get_object(), "closed", closed_by=request.user, closed_at=timezone.now())

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        return self._set_status(self.get_object(), "draft", closed_by=None, closed_at=None)

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        return printing.print_timesheet(request, self.get_object())

    @action(detail=False, methods=["get"], url_path="export")
    def export_xlsx(self, request):
        """Exportul lunii pentru 1C Salariu: toate tabelele (sau doar subdiviziunea) din lună, închise sau nu."""
        p = request.query_params
        try:
            year, month = int(p.get("year") or 0), int(p.get("month") or 0)
        except ValueError:
            raise ValidationError({"month": "Alegeți luna."}) from None
        if not year or not month:
            raise ValidationError({"month": "Alegeți luna."})
        qs = self.get_queryset().filter(year=year, month=month)
        if p.get("closed_only"):
            qs = qs.filter(status="closed")
        return export.timesheets_xlsx(list(qs.order_by("subdivision__sort", "subdivision__name_ro")), year, month)


class TimesheetLineViewSet(viewsets.ModelViewSet):
    perm_module = "worktime"
    serializer_class = TimesheetLineSerializer
    pagination_class = None
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        qs = TimesheetLine.objects.select_related("timesheet", "employment__employee")
        ids = services.visible_ids(self.request.user)
        if ids is not None:
            qs = qs.filter(timesheet__subdivision_id__in=ids)
        if self.request.query_params.get("timesheet"):
            return qs.filter(timesheet_id=self.request.query_params["timesheet"])
        return qs.none() if self.action == "list" else qs

    def perform_update(self, serializer):
        if serializer.instance.timesheet.status == "closed":
            raise ValidationError({"detail": "Tabela este închisă."})
        serializer.save()


class EmployeeMonthView(APIView):
    """Luna unui angajat (pentru fișă / cabinet): toate raporturile lui cu zilele din tabelele secțiilor."""

    perm_module = ("worktime", "employees")

    def get(self, request, employee):
        from apps.staff.models import Employee

        emp = Employee.objects.filter(pk=employee).first()
        if emp is None or not staff.can_see(emp, request.user, "employees"):
            raise NotFound()
        today = timezone.localdate()
        year, month = int(request.query_params.get("year") or today.year), int(request.query_params.get("month") or today.month)
        lines = (TimesheetLine.objects.filter(employment__employee=emp, timesheet__year=year, timesheet__month=month)
                 .select_related("timesheet__subdivision", "employment__occupation"))
        ctx = services.Context(year, month)
        return Response({"year": year, "month": month, "days": services._days_header(ctx), "codes": services.CODE_LABELS,
                         "rows": [{"timesheet": ln.timesheet_id, "subdivision": ln.timesheet.subdivision.name_ro,
                                   "status": ln.timesheet.get_status_display(), "occupation": ln.employment.occupation.name_ro,
                                   "kind": ln.employment.get_kind_display(), "rate": float(ln.employment.rate),
                                   "days": ln.days, "totals": ln.totals} for ln in lines]})


class TimesheetImportView(APIView):
    """Importul orelor pe tipuri din Excel în tabela de pontaj: GET …/template/ — șablonul; POST (fișier) — încercarea
    (dry_run=1) sau importul. Tabela trebuie să se poată modifica (ciornă; transmisă — cu dreptul „aprobă”)."""

    perm_module = "worktime"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _timesheet(self, request, pk):
        ts = Timesheet.objects.filter(pk=pk).select_related("subdivision").first()
        ids = services.visible_ids(request.user)
        if ts is None or (ids is not None and ts.subdivision_id not in ids):
            raise NotFound()
        return ts

    def get(self, request, pk, code):
        from django.http import HttpResponse

        from apps.core import excel_import

        from .imports import hours_spec

        self._timesheet(request, pk)
        response = HttpResponse(excel_import.template(hours_spec()),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="sablon-ore-pe-tipuri.xlsx"'
        return response

    def post(self, request, pk, code):
        from apps.core import excel_import

        from .imports import hours_spec

        ts = self._timesheet(request, pk)
        if not request.user.has_crm_perm("worktime.edit"):
            raise PermissionDenied("Pontajul îl completează cine are dreptul „modifică” la timpul de muncă.")
        ensure_not_marked(ts)
        if ts.status == "closed" or (ts.status == "submitted" and not request.user.has_crm_perm("worktime.approve")):
            raise ValidationError({"detail": "Tabela nu se mai modifică (transmisă sau închisă)."})
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "Alegeți fișierul Excel (.xlsx)."})
        if upload.size > 10 * 1024 * 1024:
            raise ValidationError({"file": "Fișierul e prea mare (cel mult 10 MB)."})
        dry_run = str(request.data.get("dry_run", "1")) in ("1", "true", "True")
        return Response(excel_import.run(hours_spec(), upload.read(), dry_run=dry_run, context={"timesheet": ts}))
