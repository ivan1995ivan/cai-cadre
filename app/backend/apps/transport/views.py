"""API-ul transportului: vehiculele, tarifele pe km, țările cu normele diurnei, cursele (ciornă → aprobat → în calculul
salariului lunii întoarcerii), importul curselor din Excel și tiparul foii de parcurs."""
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.deletion import DeletionMarkMixin, ensure_not_marked
from apps.core.models import NumberSeries
from apps.staff import services as staff
from apps.staff.models import Employee, Employment

from . import services
from .models import Country, KmRate, PerDiemNorm, Trip, Vehicle
from .serializers import (CountrySerializer, KmRateSerializer, PerDiemNormSerializer, TripSerializer, VehicleSerializer)

# clasificatoarele transportului le modifică cine are „modifică” la transport
CATALOG_ACTIONS = {"create": "edit", "update": "edit", "partial_update": "edit", "destroy": "edit", "unmark": "edit"}


class VehicleViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "transport"
    perm_actions = CATALOG_ACTIONS
    serializer_class = VehicleSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Vehicle.objects.select_related("subdivision")
        p = self.request.query_params
        if p.get("active") in ("1", "true"):
            qs = qs.filter(is_active=True, deletion_mark=False)
        if p.get("trailer") in ("0", "1"):
            qs = qs.filter(kind="trailer") if p["trailer"] == "1" else qs.exclude(kind="trailer")
        return qs

    def check_delete(self, instance):
        if instance.trips.exists() or instance.trailer_trips.exists():
            raise ValidationError({"detail": "Vehiculul are curse; marcați-l inactiv în loc să-l ștergeți."})


class KmRateViewSet(viewsets.ModelViewSet):
    perm_module = "transport"
    perm_actions = CATALOG_ACTIONS
    serializer_class = KmRateSerializer
    pagination_class = None
    queryset = KmRate.objects.all()


class CountryViewSet(viewsets.ModelViewSet):
    perm_module = "transport"
    perm_actions = CATALOG_ACTIONS
    serializer_class = CountrySerializer
    pagination_class = None

    def get_queryset(self):
        qs = Country.objects.prefetch_related("norms")
        if self.request.query_params.get("active") in ("1", "true"):
            qs = qs.filter(is_active=True)
        return qs

    def perform_destroy(self, instance):
        from .models import TripLeg

        if TripLeg.objects.filter(country=instance).exists():
            raise ValidationError({"detail": "Țara apare în curse; faceți-o inactivă."})
        instance.delete()


class PerDiemNormViewSet(viewsets.ModelViewSet):
    perm_module = "transport"
    perm_actions = CATALOG_ACTIONS
    serializer_class = PerDiemNormSerializer
    pagination_class = None

    def get_queryset(self):
        qs = PerDiemNorm.objects.select_related("country")
        country = self.request.query_params.get("country")
        if country:
            return qs.filter(country_id=country)
        return qs


class TripViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "transport"
    serializer_class = TripSerializer
    perm_actions = {"approve": "approve", "unapprove": "approve", "print": "view", "drivers": "view", "tacho": "view",
                    "tacho_legs": "view", "gps": "view"}

    def get_queryset(self):
        qs = Trip.objects.select_related("driver__employee", "driver__occupation", "co_driver__employee", "co_driver__occupation",
                                         "vehicle", "trailer").prefetch_related("legs__country", "diems__country",
                                                                               "diems__employment__employee")
        if staff.visible_subdivision_ids(self.request.user, "transport") is not None:  # doar cursele șoferilor văzuți
            visible = staff.scope_employees(Employee.objects.all(), self.request.user, "transport")
            qs = qs.filter(driver__employee__in=visible)
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("year"):
            qs = qs.filter(arrival__year=p["year"])
        if p.get("month"):
            qs = qs.filter(arrival__month=p["month"])
        if p.get("vehicle"):
            qs = qs.filter(Q(vehicle_id=p["vehicle"]) | Q(trailer_id=p["vehicle"]))
        if p.get("employee"):
            qs = qs.filter(Q(driver__employee_id=p["employee"]) | Q(co_driver__employee_id=p["employee"]))
        return qs

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "detail": self.action != "list"}

    def _check_people(self, serializer):
        for name in ("driver", "co_driver"):
            job = serializer.validated_data.get(name)
            if job is not None and not staff.can_see(job.employee, self.request.user, "transport"):
                raise PermissionDenied("Șoferul nu este în subdiviziunile dvs.")

    def perform_create(self, serializer):
        self._check_people(serializer)
        serializer.save(created_by=self.request.user, number=NumberSeries.next_number("trip"))

    def _editable(self, doc):
        ensure_not_marked(doc)
        if doc.status != "draft":
            raise ValidationError({"detail": "Cursa este aprobată; anulați întâi aprobarea (drept de aprobare)."})

    def perform_update(self, serializer):
        self._editable(serializer.instance)
        self._check_people(serializer)
        serializer.save()

    def check_delete(self, instance):
        self._editable(instance)

    def _fresh(self, pk):
        return self.get_serializer(Trip.objects.get(pk=pk)).data

    @staticmethod
    def _payroll_closed(doc):
        """Luna întoarcerii are calculul salariului aprobat pentru acești șoferi: cursa nu se aprobă / nu se anulează."""
        from apps.payroll.models import Payroll

        day = services.local_day(doc.arrival)
        jobs = [j for j in (doc.driver_id, doc.co_driver_id) if j]
        closed = Payroll.objects.filter(year=day.year, month=day.month, status="approved", deletion_mark=False,
                                        lines__employment_id__in=jobs).distinct()
        if closed.exists():
            refs = ", ".join(f"nr. {p.number}" for p in closed[:3])
            raise ValidationError({"detail": f"Calculul salariului pe {day:%m.%Y} ({refs}) e aprobat pentru acești șoferi; "
                                             f"redeschideți-l întâi, apoi recalculați-l după cursă."})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Aprobarea: cursa se socotește din nou cu verificarea completă (orice problemă oprește); tariful pe km, cursurile
        valutare și diurna se fixează; cursa intră în calculul salariului lunii întoarcerii."""
        with transaction.atomic():
            doc = Trip.objects.select_for_update().get(pk=self.get_object().pk)
            self._editable(doc)
            services.compute(doc, strict=True)
            self._payroll_closed(doc)
            doc.status, doc.approved_by, doc.approved_at = "approved", request.user, timezone.now()
            doc.save(update_fields=["status", "approved_by", "approved_at"])
        return Response(self._fresh(doc.pk))

    @action(detail=True, methods=["post"])
    def unapprove(self, request, pk=None):
        with transaction.atomic():
            doc = Trip.objects.select_for_update().get(pk=self.get_object().pk)
            if doc.status != "approved":
                raise ValidationError({"detail": "Cursa nu este aprobată."})
            self._payroll_closed(doc)
            doc.status, doc.approved_by, doc.approved_at = "draft", None, None
            doc.save(update_fields=["status", "approved_by", "approved_at"])
        return Response(self._fresh(doc.pk))

    @action(detail=False, methods=["get"])
    def drivers(self, request):
        """Raporturile de muncă care pot fi șoferi la data dată (active, fără prestări servicii), văzute de utilizator."""
        from .serializers import JobChoiceSerializer

        day = request.query_params.get("date") or timezone.localdate().isoformat()
        visible = staff.scope_employees(Employee.objects.all(), request.user, "transport")
        qs = (Employment.objects.filter(employee__in=visible, date_from__lte=day).filter(Q(end_date__isnull=True) | Q(end_date__gte=day))
              .exclude(kind="contractor").select_related("employee", "occupation")
              .order_by("employee__last_name", "employee__first_name", "id"))
        return Response(JobChoiceSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def tacho(self, request, pk=None):
        """Tahograful în timpul cursei: timpii fiecărui șofer, acoperirea cu descărcări, constatările."""
        from . import tacho

        return Response(tacho.trip_info(self.get_object()))

    @action(detail=True, methods=["get"])
    def gps(self, request, pk=None):
        """GPS-ul vehiculului pe zilele cursei: km, timpii, combustibilul, kilometrajul, țările; diferența față de foaie."""
        from . import gps

        return Response(gps.trip_info(self.get_object()))

    @action(detail=True, methods=["get"], url_path="tacho-legs")
    def tacho_legs(self, request, pk=None):
        """Țările cursei din trecerile frontierei de pe cardul șoferului — propunerea (se pune în formular, nu se salvează)."""
        from . import tacho

        return Response({"legs": tacho.legs_from_borders(self.get_object())})

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        from .printing import print_trip

        return print_trip(request, self.get_object())


class TripImportView(APIView):
    """Importul curselor dintr-un fișier Excel (un rând pe segment de țară; rândurile cu același „Nr. cursei” din fișier fac o
    cursă): GET …/template/ — șablonul; POST (fișierul) — verificarea (`dry_run=1`) sau importul (cursele noi, ciornă)."""

    perm_module = "transport"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        from apps.core import excel_import

        from .imports import trips_spec

        response = HttpResponse(excel_import.template(trips_spec()),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="sablon-curse.xlsx"'
        return response

    def post(self, request):
        from apps.core import excel_import

        from .imports import finish, trips_spec

        if not request.user.has_crm_perm("transport.create"):
            raise PermissionDenied("Cursele le importă cine are dreptul „creează” la transport.")
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "Alegeți fișierul Excel (.xlsx)."})
        if upload.size > 10 * 1024 * 1024:
            raise ValidationError({"file": "Fișierul e prea mare (cel mult 10 MB)."})
        dry_run = str(request.data.get("dry_run", "1")) in ("1", "true", "True")
        context = {"user": request.user, "trips": {}}
        result = excel_import.run(trips_spec(), upload.read(), dry_run=dry_run, context=context)
        if not dry_run:
            finish(context)
        return Response(result)


# --- tahograful ------------------------------------------------------------------------------------------------------------
def _month_bounds(text):
    from datetime import date

    try:
        y, m = (int(x) for x in str(text).split("-")[:2])
        first = date(y, m, 1)
    except (TypeError, ValueError):
        raise ValidationError({"month": "Luna se scrie AAAA-LL."}) from None
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    from datetime import timedelta

    return first, nxt - timedelta(days=1)


def _visible_employee(request, pk):
    emp = Employee.objects.filter(pk=pk).first()
    if emp is None or not staff.can_see(emp, request.user, "transport"):
        raise ValidationError({"employee": "Angajatul nu există sau nu este în subdiviziunile dvs."})
    return emp


class TachoFileViewSet(viewsets.ReadOnlyModelViewSet):
    """Descărcările cardului de conducător: lista, încărcarea (mai multe fișiere deodată), legarea de angajat, fișierul original
    (pentru control), ștergerea (zilele angajatului se refac din celelalte)."""

    perm_module = "transport"
    perm_actions = {"upload": "create", "assign": "edit", "original": "view", "remove": "delete", "drivers": "view"}
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        from .serializers import TachoFileSerializer

        return TachoFileSerializer

    def get_queryset(self):
        from .models import TachoFile

        qs = TachoFile.objects.select_related("employee")
        if staff.visible_subdivision_ids(self.request.user, "transport") is not None:
            visible = staff.scope_employees(Employee.objects.all(), self.request.user, "transport")
            qs = qs.filter(employee__in=visible)
        p = self.request.query_params
        if p.get("employee"):
            qs = qs.filter(employee_id=p["employee"])
        if p.get("unmatched") in ("1", "true"):
            qs = qs.filter(employee__isnull=True)
        return qs

    @action(detail=False, methods=["post"])
    def upload(self, request):
        from . import tacho

        files = request.FILES.getlist("files") or request.FILES.getlist("file")
        if not files:
            raise ValidationError({"files": "Alegeți fișierele descărcate de pe card (.ddd)."})
        if len(files) > 100:
            raise ValidationError({"files": "Cel mult 100 de fișiere deodată."})
        results = []
        for up in files:
            r = tacho.upload(up.name, up.read(), request.user)
            emp = r.get("employee")
            if emp and not staff.can_see(Employee.objects.get(pk=emp), request.user, "transport"):
                r["employee_name"] = ""
            results.append(r)
        return Response({"results": results})

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        from . import tacho

        f = self.get_object()
        emp = _visible_employee(request, request.data.get("employee")) if request.data.get("employee") else None
        tacho.assign(f, emp)
        return Response(self.get_serializer(f).data)

    @action(detail=True, methods=["get"])
    def original(self, request, pk=None):
        from django.http import FileResponse

        f = self.get_object()
        name = f"C_{f.card_number}_{(f.downloaded_at or f.uploaded_at):%Y%m%d%H%M}.ddd"
        return FileResponse(f.file.open("rb"), as_attachment=True, filename=name, content_type="application/octet-stream")

    @action(detail=True, methods=["post"])
    def remove(self, request, pk=None):
        from . import tacho

        tacho.delete_file(self.get_object())
        return Response(status=204)

    @action(detail=False, methods=["get"])
    def drivers(self, request):
        """Angajații cu zile de pe card, văzuți de utilizator."""
        visible = staff.scope_employees(Employee.objects.all(), request.user, "transport")
        qs = visible.filter(tacho_days__isnull=False).distinct().order_by("last_name", "first_name")
        return Response([{"id": e.pk, "label": f"{e.full_name()} ({e.tab_number})"} for e in qs])


class TachoDaysView(APIView):
    """GET ?employee=&month=AAAA-LL — zilele lunii cu activitățile, km, țările, vehiculele și constatările (ora Moldovei)."""

    perm_module = "transport"

    def get(self, request):
        from . import tacho

        emp = _visible_employee(request, request.query_params.get("employee"))
        first, last = _month_bounds(request.query_params.get("month") or timezone.localdate().strftime("%Y-%m"))
        rows = tacho.day_rows(emp, first, last)
        keys = ("driving", "work", "availability", "rest", "unknown", "km")
        return Response({"employee": emp.pk, "name": emp.full_name(), "days": rows,
                         "totals": {k: sum(r[k] for r in rows) for k in keys},
                         "findings": [f for r in rows for f in r["findings"]]})


class TachoFindingsView(APIView):
    """GET ?month=AAAA-LL[&employee=] — constatările lunii pentru șoferii văzuți (cu date de pe card)."""

    perm_module = "transport"

    def get(self, request):
        from datetime import datetime, time, timedelta

        from . import tacho

        first, last = _month_bounds(request.query_params.get("month") or timezone.localdate().strftime("%Y-%m"))
        lo = timezone.make_aware(datetime.combine(first, time.min))
        hi = timezone.make_aware(datetime.combine(last + timedelta(days=1), time.min))
        visible = staff.scope_employees(Employee.objects.all(), request.user, "transport")
        people = visible.filter(tacho_days__day__gte=first - timedelta(days=1), tacho_days__day__lte=last + timedelta(days=1))
        if request.query_params.get("employee"):
            people = people.filter(pk=request.query_params["employee"])
        out = []
        for e in people.distinct().order_by("last_name", "first_name"):
            for f in tacho.findings(e, lo, hi):
                out.append({"employee": e.pk, "name": e.full_name(), **f.as_dict()})
        out.sort(key=lambda x: (x["start"], x["name"]))
        return Response({"rows": out})


# --- GPS-ul vehiculelor (pasul c) --------------------------------------------------------------------------------------------
class GpsDayViewSet(viewsets.ModelViewSet):
    """Zilele vehiculelor din GPS: GET ?vehicle=&month=AAAA-LL; DELETE — o zi (importată greșit)."""

    perm_module = "transport"
    http_method_names = ["get", "delete", "head", "options"]
    pagination_class = None

    def get_serializer_class(self):
        from .serializers import GpsDaySerializer

        return GpsDaySerializer

    def get_queryset(self):
        from .models import GpsDay

        qs = GpsDay.objects.select_related("vehicle")
        p = self.request.query_params
        if p.get("vehicle"):
            qs = qs.filter(vehicle_id=p["vehicle"])
        if p.get("month"):
            first, last = _month_bounds(p["month"])
            qs = qs.filter(day__gte=first, day__lte=last)
        return qs.order_by("vehicle__plate", "day")


class GpsImportView(APIView):
    """Importul zilelor din GPS (Excel / CSV exportat din sistemul de monitorizare): GET …/template/ — șablonul; POST —
    verificarea (`dry_run=1`) sau importul (zilele noi se adaugă, cele existente se înlocuiesc)."""

    perm_module = "transport"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        from apps.core import excel_import

        from .gps import gps_spec

        response = HttpResponse(excel_import.template(gps_spec()),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="sablon-gps.xlsx"'
        return response

    def post(self, request):
        from apps.core import excel_import

        from .gps import gps_spec

        if not request.user.has_crm_perm("transport.create"):
            raise PermissionDenied("Zilele din GPS le importă cine are dreptul „creează” la transport.")
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "Alegeți fișierul exportat din GPS (Excel sau CSV)."})
        if upload.size > 10 * 1024 * 1024:
            raise ValidationError({"file": "Fișierul e prea mare (cel mult 10 MB)."})
        dry_run = str(request.data.get("dry_run", "1")) in ("1", "true", "True")
        context = {"user": request.user, "source": (upload.name or "fișier")[:40]}
        return Response(excel_import.run(gps_spec(), upload.read(), dry_run=dry_run, context=context))


# --- evenimentele șoferilor și KPI (pasul c) --------------------------------------------------------------------------------
class DriverIncidentViewSet(viewsets.ModelViewSet):
    perm_module = "transport"
    pagination_class = None

    def get_serializer_class(self):
        from .serializers import DriverIncidentSerializer

        return DriverIncidentSerializer

    def get_queryset(self):
        from .models import DriverIncident

        qs = DriverIncident.objects.select_related("employee", "trip")
        if staff.visible_subdivision_ids(self.request.user, "transport") is not None:
            qs = qs.filter(employee__in=staff.scope_employees(Employee.objects.all(), self.request.user, "transport"))
        p = self.request.query_params
        if p.get("employee"):
            qs = qs.filter(employee_id=p["employee"])
        if p.get("month"):
            first, last = _month_bounds(p["month"])
            qs = qs.filter(date__gte=first, date__lte=last)
        if p.get("kind"):
            qs = qs.filter(kind=p["kind"])
        return qs

    def _check(self, serializer):
        emp = serializer.validated_data.get("employee")
        if emp is not None and not staff.can_see(emp, self.request.user, "transport"):
            raise PermissionDenied("Angajatul nu este în subdiviziunile dvs.")
        self._closed(serializer.validated_data.get("date"), emp)

    def _closed(self, day, emp, instance=None):
        """Evenimentul unei luni cu fișa KPI aprobată nu se mai schimbă (prima e socotită)."""
        from .models import KpiLine

        for d, e in ((day, emp), (instance.date, instance.employee) if instance is not None else (None, None)):
            if d is None or e is None:
                continue
            sheet = (KpiLine.objects.filter(sheet__status="approved", sheet__deletion_mark=False, sheet__year=d.year,
                                            sheet__month=d.month, employee=e).select_related("sheet").first())
            if sheet is not None:
                raise ValidationError({"detail": f"Fișa KPI {sheet.sheet.reference()} e aprobată pentru {e.full_name()}: anulați "
                                                 f"întâi aprobarea ei."})

    def perform_create(self, serializer):
        self._check(serializer)
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        self._closed(None, None, serializer.instance)
        self._check(serializer)
        serializer.save()

    def perform_destroy(self, instance):
        self._closed(None, None, instance)
        instance.delete()


class KpiIndicatorViewSet(viewsets.ModelViewSet):
    perm_module = "transport"
    perm_actions = CATALOG_ACTIONS
    pagination_class = None

    def get_serializer_class(self):
        from .serializers import KpiIndicatorSerializer

        return KpiIndicatorSerializer

    def get_queryset(self):
        from .models import KpiIndicator

        return KpiIndicator.objects.all()

    def perform_destroy(self, instance):
        from .models import KpiSchemeItem

        if KpiSchemeItem.objects.filter(indicator=instance).exists():
            raise ValidationError({"detail": "Indicatorul e într-o schemă KPI; scoateți-l de acolo sau faceți-l inactiv."})
        instance.delete()


class KpiSchemeViewSet(viewsets.ModelViewSet):
    perm_module = "transport"
    perm_actions = CATALOG_ACTIONS
    pagination_class = None

    def get_serializer_class(self):
        from .serializers import KpiSchemeSerializer

        return KpiSchemeSerializer

    def get_queryset(self):
        from .models import KpiScheme

        return KpiScheme.objects.prefetch_related("items__indicator", "assignments__occupation", "assignments__employment__employee",
                                                  "assignments__employment__occupation")

    def perform_destroy(self, instance):
        from .models import KpiLine

        if KpiLine.objects.filter(scheme=instance).exists():
            raise ValidationError({"detail": "Schema e folosită în fișe KPI; faceți-o inactivă în loc să o ștergeți."})
        instance.delete()


class KpiAssignmentViewSet(viewsets.ModelViewSet):
    perm_module = "transport"
    perm_actions = CATALOG_ACTIONS
    pagination_class = None

    def get_serializer_class(self):
        from .serializers import KpiAssignmentSerializer

        return KpiAssignmentSerializer

    def get_queryset(self):
        from .models import KpiAssignment

        qs = KpiAssignment.objects.select_related("scheme", "occupation", "employment__employee", "employment__occupation")
        if self.request.query_params.get("scheme"):
            qs = qs.filter(scheme_id=self.request.query_params["scheme"])
        return qs


class KpiSheetViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    """Fișele KPI ale lunii: ciornă → „Completează” (șoferii cu schemă, valorile din curse / evenimente / tahograf) → valorile
    de mână pe rânduri → aprobare (prima intră în salariul lunii)."""

    perm_module = "transport"
    perm_actions = {"approve": "approve", "unapprove": "approve", "fill": "edit", "line": "edit", "print": "view"}

    def get_serializer_class(self):
        from .serializers import KpiSheetSerializer

        return KpiSheetSerializer

    def get_queryset(self):
        from .models import KpiSheet

        qs = KpiSheet.objects.select_related("subdivision")
        p = self.request.query_params
        if p.get("year"):
            qs = qs.filter(year=p["year"])
        if p.get("month"):
            qs = qs.filter(month=p["month"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        return qs

    def _visible_jobs(self):
        """Raporturile de muncă văzute de utilizator (None — toate)."""
        if staff.visible_subdivision_ids(self.request.user, "transport") is None:
            return None
        visible = staff.scope_employees(Employee.objects.all(), self.request.user, "transport")
        return set(Employment.objects.filter(employee__in=visible).values_list("pk", flat=True))

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "detail": self.action != "list", "visible_jobs": self._visible_jobs()}

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, number=NumberSeries.next_number("kpi_sheet"))

    def perform_update(self, serializer):
        from . import kpi

        kpi.editable(serializer.instance)
        serializer.save()

    def check_delete(self, instance):
        from . import kpi

        kpi.editable(instance)

    def _fresh(self, pk):
        from .models import KpiSheet

        return self.get_serializer(KpiSheet.objects.get(pk=pk)).data

    @action(detail=True, methods=["post"])
    def fill(self, request, pk=None):
        from . import kpi

        doc = self.get_object()
        kpi.fill(doc, jobs_visible=self._visible_jobs())
        return Response(self._fresh(doc.pk))

    @action(detail=True, methods=["post"])
    def line(self, request, pk=None):
        """POST {line, overrides: {COD: valoare | null}} — valorile scrise de mână ale rândului."""
        from . import kpi
        from .models import KpiLine

        doc = self.get_object()
        ln = KpiLine.objects.filter(sheet=doc, pk=request.data.get("line")).select_related("scheme", "employment", "sheet").first()
        visible = self._visible_jobs()
        if ln is None or (visible is not None and ln.employment_id not in visible):
            raise ValidationError({"line": "Rândul nu există în fișă."})
        kpi.set_overrides(ln, request.data.get("overrides") or {})
        return Response(self._fresh(doc.pk))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from . import kpi
        from .models import KpiSheet

        if self._visible_jobs() is not None:
            raise PermissionDenied("Fișa KPI a întreprinderii o aprobă cine vede toate subdiviziunile.")
        with transaction.atomic():
            doc = KpiSheet.objects.select_for_update().get(pk=self.get_object().pk)
            kpi.approve(doc, request.user)
        return Response(self._fresh(doc.pk))

    @action(detail=True, methods=["post"])
    def unapprove(self, request, pk=None):
        from . import kpi
        from .models import KpiSheet

        with transaction.atomic():
            doc = KpiSheet.objects.select_for_update().get(pk=self.get_object().pk)
            kpi.unapprove(doc)
        return Response(self._fresh(doc.pk))

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        from .printing import print_kpi

        return print_kpi(request, self.get_object())
