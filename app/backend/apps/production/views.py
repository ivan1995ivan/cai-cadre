"""API-ul producției: grila tarifară, lucrările (cu normele și tarifele lor), brigăzile și rapoartele de producție (ciornă →
aprobat → în calculul salariului), cu importul lucrărilor / membrilor din Excel și tiparul raportului."""
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.deletion import DeletionMarkMixin, ensure_not_marked
from apps.core.models import NumberSeries
from apps.staff import services as staff
from apps.staff.models import Employee, Employment

from . import services
from .models import Brigade, Operation, OperationRate, ProductionReport, TariffGrid
from .serializers import (BrigadeSerializer, OperationRateSerializer, OperationSerializer, ProductionReportSerializer,
                          TariffGridSerializer)

# clasificatoarele producției le modifică cine are „modifică” la producție
CATALOG_ACTIONS = {"create": "edit", "update": "edit", "partial_update": "edit", "destroy": "edit", "unmark": "edit"}


class TariffGridViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "production"
    perm_actions = CATALOG_ACTIONS
    serializer_class = TariffGridSerializer
    pagination_class = None

    def get_queryset(self):
        qs = TariffGrid.objects.prefetch_related("ranks")
        code = self.request.query_params.get("code")
        return qs.filter(code=code.upper()) if code else qs


class OperationViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "production"
    perm_actions = CATALOG_ACTIONS
    serializer_class = OperationSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Operation.objects.select_related("subdivision")
        p = self.request.query_params
        if p.get("active") in ("1", "true"):
            qs = qs.filter(is_active=True, deletion_mark=False)
        if p.get("search"):
            s = p["search"]
            qs = qs.filter(Q(code__icontains=s) | Q(name_ro__icontains=s) | Q(name_ru__icontains=s))
        return qs


class OperationRateViewSet(viewsets.ModelViewSet):
    perm_module = "production"
    perm_actions = CATALOG_ACTIONS
    serializer_class = OperationRateSerializer
    pagination_class = None

    def get_queryset(self):
        qs = OperationRate.objects.select_related("operation")
        op = self.request.query_params.get("operation")
        if op:
            return qs.filter(operation_id=op)
        return qs if self.action != "list" else qs.none()

    def _check(self, serializer):
        op = serializer.validated_data.get("operation") or serializer.instance.operation
        day = serializer.validated_data.get("date_from") or serializer.instance.date_from
        clash = OperationRate.objects.filter(operation=op, date_from=day)
        if serializer.instance is not None:
            clash = clash.exclude(pk=serializer.instance.pk)
        if clash.exists():
            raise ValidationError({"date_from": f"Lucrarea {op.code} are deja o normă din {day:%d.%m.%Y}."})

    def perform_create(self, serializer):
        self._check(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._check(serializer)
        serializer.save()


class BrigadeViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "production"
    perm_actions = CATALOG_ACTIONS
    serializer_class = BrigadeSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Brigade.objects.select_related("subdivision", "leader__employee").prefetch_related(
            "members__employment__employee", "members__employment__occupation")
        if self.request.query_params.get("active") in ("1", "true"):
            qs = qs.filter(is_active=True, deletion_mark=False)
        return qs

    def _check(self, serializer):
        for m in serializer.validated_data.get("members") or []:
            if not staff.can_see(m["employment"].employee, self.request.user, "production"):
                raise PermissionDenied("Angajatul nu este în subdiviziunile dvs.")

    def perform_create(self, serializer):
        self._check(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._check(serializer)
        serializer.save()


class ProductionReportViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "production"
    serializer_class = ProductionReportSerializer
    perm_actions = {"approve": "approve", "unapprove": "approve", "print": "view", "fill_members": "edit"}

    def get_queryset(self):
        qs = ProductionReport.objects.select_related("brigade", "subdivision").prefetch_related(
            "lines__employment__employee", "lines__employment__occupation", "lines__operation",
            "members__employment__employee", "members__employment__occupation")
        if staff.visible_subdivision_ids(self.request.user, "production") is not None:  # doar rapoartele angajaților văzuți
            visible = staff.scope_employees(Employee.objects.all(), self.request.user, "production")
            hidden = Employment.objects.exclude(employee__in=visible)
            qs = qs.exclude(lines__employment__in=hidden).exclude(members__employment__in=hidden)
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("year"):
            qs = qs.filter(date__year=p["year"])
        if p.get("month"):
            qs = qs.filter(date__month=p["month"])
        if p.get("kind"):
            qs = qs.filter(kind=p["kind"])
        if p.get("brigade"):
            qs = qs.filter(brigade_id=p["brigade"])
        if p.get("employee"):
            qs = qs.filter(Q(lines__employment__employee_id=p["employee"]) | Q(members__employment__employee_id=p["employee"]))
        return qs.distinct()

    def _check_people(self, serializer):
        for ln in serializer.validated_data.get("lines") or []:
            if ln.get("employment") is not None and not staff.can_see(ln["employment"].employee, self.request.user, "production"):
                raise PermissionDenied("Angajatul nu este în subdiviziunile dvs.")
        for m in serializer.validated_data.get("members") or []:
            if not staff.can_see(m["employment"].employee, self.request.user, "production"):
                raise PermissionDenied("Angajatul nu este în subdiviziunile dvs.")

    def perform_create(self, serializer):
        self._check_people(serializer)
        serializer.save(created_by=self.request.user, number=NumberSeries.next_number("production_report"))

    def _editable(self, doc):
        ensure_not_marked(doc)
        if doc.status != "draft":
            raise ValidationError({"detail": "Raportul este aprobat; anulați întâi aprobarea (drept de aprobare)."})

    def perform_update(self, serializer):
        self._editable(serializer.instance)
        self._check_people(serializer)
        serializer.save()

    def check_delete(self, instance):
        self._editable(instance)

    @staticmethod
    def _payroll_closed(doc):
        """Luna raportului are deja un calcul al salariului aprobat: raportul nu se mai aprobă / nu se mai anulează până nu se
        redeschide calculul (altfel salariul aprobat n-ar mai corespunde rapoartelor)."""
        from apps.payroll.models import Payroll

        jobs = {ln.employment_id for ln in doc.lines.all() if ln.employment_id} | {m.employment_id for m in doc.members.all()}
        closed = Payroll.objects.filter(year=doc.date.year, month=doc.date.month, status="approved", deletion_mark=False,
                                        lines__employment_id__in=jobs).distinct()
        if closed.exists():
            refs = ", ".join(f"nr. {p.number}" for p in closed[:3])
            raise ValidationError({"detail": f"Calculul salariului pe {doc.date:%m.%Y} ({refs}) e aprobat pentru acești angajați; "
                                             f"redeschideți-l întâi, apoi recalculați-l după raport."})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Aprobarea: rândurile și membrii se socotesc din nou, cu verificarea completă (orice problemă oprește), iar tarifele
        se fixează; raportul intră în calculul salariului lunii lui."""
        with transaction.atomic():
            doc = ProductionReport.objects.select_for_update().get(pk=self.get_object().pk)
            self._editable(doc)
            services.recompute(doc, strict=True)
            self._payroll_closed(doc)
            doc.status, doc.approved_by, doc.approved_at = "approved", request.user, timezone.now()
            doc.save(update_fields=["status", "approved_by", "approved_at"])
        return Response(ProductionReportSerializer(doc).data)

    @action(detail=True, methods=["post"])
    def unapprove(self, request, pk=None):
        with transaction.atomic():
            doc = ProductionReport.objects.select_for_update().get(pk=self.get_object().pk)
            if doc.status != "approved":
                raise ValidationError({"detail": "Raportul nu este aprobat."})
            self._payroll_closed(doc)
            doc.status, doc.approved_by, doc.approved_at = "draft", None, None
            doc.save(update_fields=["status", "approved_by", "approved_at"])
        return Response(ProductionReportSerializer(doc).data)

    @action(detail=True, methods=["post"], url_path="fill-members")
    def fill_members(self, request, pk=None):
        """Membrii raportului pe brigadă din componența brigăzii la data raportului, cu coeficientul lor; orele — din tabela
        de pontaj a lunii (dacă raportul de muncă e în ea), altfel 0. Membrii scriși deja rămân (li se completează doar orele
        goale, dacă se cere `hours=1`)."""
        from apps.worktime.models import TimesheetLine

        from .models import ProductionMember

        doc = self.get_object()
        self._editable(doc)
        if doc.kind != "brigade" or doc.brigade_id is None:
            raise ValidationError({"detail": "Completarea membrilor e doar la raportul pe brigadă, cu brigada aleasă."})
        with transaction.atomic():
            present = {m.employment_id: m for m in doc.members.all()}
            hours = {ln.employment_id: (ln.totals or {}).get("hours") for ln in TimesheetLine.objects.filter(
                timesheet__year=doc.date.year, timesheet__month=doc.date.month, timesheet__deletion_mark=False)}
            n = doc.members.count()
            for bm in doc.brigade.members.select_related("employment__employee").order_by("date_from", "id"):
                if not bm.in_force(doc.date) or not bm.employment.is_active_on(doc.date):
                    continue
                if not staff.can_see(bm.employment.employee, request.user, "production"):
                    continue
                h = hours.get(bm.employment_id)
                if bm.employment_id in present:
                    m = present[bm.employment_id]
                    if not m.hours and h:
                        m.hours = h
                        m.save(update_fields=["hours"])
                    continue
                n += 1
                ProductionMember.objects.create(report=doc, employment=bm.employment, coefficient=bm.coefficient, hours=h or 0, sort=n * 10)
            fresh = ProductionReport.objects.get(pk=doc.pk)  # fără rândurile preîncărcate de dinainte
            fresh._problems = services.recompute(fresh)
        return Response(ProductionReportSerializer(fresh).data)

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        from .printing import print_report

        return print_report(request, self.get_object())


def _report_for_import(request, pk):
    doc = ProductionReport.objects.filter(pk=pk).first()
    if doc is None:
        raise NotFound()
    return doc


class ReportImportView(APIView):
    """Importul lucrărilor (`lines`) sau al membrilor brigăzii (`members`) dintr-un fișier Excel în raportul-ciornă:
    GET …/template/ — șablonul; POST (fișierul) — verificarea (`dry_run=1`) sau importul."""

    perm_module = "production"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @staticmethod
    def _spec(code):
        from .imports import lines_spec, members_spec

        if code not in ("lines", "members"):
            raise NotFound()
        return lines_spec() if code == "lines" else members_spec()

    def get(self, request, pk, code):
        from apps.core import excel_import

        _report_for_import(request, pk)
        response = HttpResponse(excel_import.template(self._spec(code)),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="sablon-raport-productie-{code}.xlsx"'
        return response

    def post(self, request, pk, code):
        from apps.core import excel_import

        if not request.user.has_crm_perm("production.edit"):
            raise PermissionDenied("Raportul de producție îl completează cine are dreptul „modifică” la producție.")
        doc = _report_for_import(request, pk)
        ensure_not_marked(doc)
        if doc.status != "draft":
            raise ValidationError({"detail": "Raportul este aprobat; anulați întâi aprobarea."})
        spec = self._spec(code)
        if code == "members" and doc.kind != "brigade":
            raise ValidationError({"detail": "Membrii se importă doar în raportul pe brigadă."})
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "Alegeți fișierul Excel (.xlsx)."})
        if upload.size > 10 * 1024 * 1024:
            raise ValidationError({"file": "Fișierul e prea mare (cel mult 10 MB)."})
        dry_run = str(request.data.get("dry_run", "1")) in ("1", "true", "True")
        result = excel_import.run(spec, upload.read(), dry_run=dry_run, context={"report": doc, "user": request.user})
        if not dry_run:
            services.recompute(doc)
        return Response(result)
