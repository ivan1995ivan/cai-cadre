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
    perm_actions = {"approve": "approve", "unapprove": "approve", "print": "view", "drivers": "view"}

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
