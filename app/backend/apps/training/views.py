from django.db.models import Count, Prefetch, Q, Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.core.deletion import DeletionMarkMixin, ensure_not_marked
from apps.staff import services as staff
from apps.staff.models import Employee, Employment

from . import services
from .models import TrainingPlan, TrainingPlanLine, TrainingRecord
from .serializers import PlanLineSerializer, PlanSerializer, TrainingRecordSerializer


def _visible(user):
    return staff.scope_employees(Employee.objects.all(), user)


def _sub_ids(request):
    """Subdiviziunile văzute, restrânse la cea aleasă în filtru (cu sub-subdiviziunile)."""
    from apps.org.models import Subdivision

    ids = staff.visible_subdivision_ids(request.user, "employees")
    sub = request.query_params.get("subdivision")
    if sub:
        obj = Subdivision.objects.filter(pk=sub).first()
        if obj is None:
            raise NotFound()
        chosen = obj.descendant_ids()
        ids = chosen if ids is None else ids & chosen
    return ids


def _date(request, name, default):
    from datetime import date

    value = request.query_params.get(name)
    try:
        return date.fromisoformat(value) if value else default
    except ValueError as exc:
        raise ValidationError({name: "Data nu este corectă."}) from exc


class TrainingRecordViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    """Registrul formării profesionale: activitățile de formare ale angajaților vizibili."""

    perm_module = "training"
    serializer_class = TrainingRecordSerializer

    def get_queryset(self):
        p = self.request.query_params
        qs = TrainingRecord.objects.filter(employee__in=_visible(self.request.user)).select_related(
            "employee", "specialty", "order_item__order")
        if p.get("employee"):
            qs = qs.filter(employee_id=p["employee"])
            self.pagination_class = None
        if p.get("date_from"):
            qs = qs.filter(Q(date_to__gte=p["date_from"]) | Q(date_to__isnull=True, date_from__gte=p["date_from"]))
        if p.get("date_to"):
            qs = qs.filter(date_from__lte=p["date_to"])
        if p.get("kind"):
            qs = qs.filter(kind=p["kind"])
        if p.get("valid_until"):  # certificatele care expiră până la data dată
            qs = qs.filter(valid_until__lte=p["valid_until"])
        if p.get("subdivision"):
            ids = _sub_ids(self.request)
            qs = qs.filter(employee__employments__subdivision_id__in=ids).distinct()
        if p.get("q"):
            q = p["q"].strip()
            qs = qs.filter(Q(employee__last_name__icontains=q) | Q(employee__first_name__icontains=q) | Q(title__icontains=q)
                           | Q(provider__icontains=q) | Q(employee__tab_number=q))
        return qs

    def _check(self, employee):
        if not staff.can_see(employee, self.request.user):
            raise NotFound()

    def perform_create(self, serializer):
        self._check(serializer.validated_data["employee"])
        record = serializer.save()
        services.link_record(record)

    def perform_update(self, serializer):
        self._check(serializer.validated_data.get("employee", serializer.instance.employee))
        serializer.save()

    def check_delete(self, instance):
        if instance.order_item_id:
            raise ValidationError({"detail": "Activitatea vine din ordinul de trimitere; se anulează odată cu ordinul."})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Totalul orelor și al persoanelor din lista filtrată."""
        agg = self.get_queryset().aggregate(hours=Sum("hours"), people=Count("employee", distinct=True))
        return Response({k: float(v or 0) for k, v in agg.items()})


class PlanViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "training"
    perm_actions = {"fill": "edit", "approve": "edit", "reopen": "edit", "print": "view"}
    serializer_class = PlanSerializer
    pagination_class = None

    def get_queryset(self):
        return TrainingPlan.objects.annotate(
            lines_count=Count("lines", distinct=True), done_count=Count("lines", filter=Q(lines__record__isnull=False), distinct=True),
            hours_total=Sum("lines__hours"))

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def check_delete(self, instance):
        if instance.status == "approved":
            raise ValidationError({"detail": "Planul aprobat nu se șterge; întoarceți-l întâi în ciornă."})

    @action(detail=True, methods=["post"])
    def fill(self, request, pk=None):
        plan = self.get_object()
        return Response({"added": services.fill_plan(plan)})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        plan = self.get_object()
        plan.status, plan.approved_at = "approved", timezone.now()
        plan.save(update_fields=["status", "approved_at"])
        return Response(PlanSerializer(self.get_queryset().get(pk=plan.pk)).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        plan = self.get_object()
        plan.status, plan.approved_at = "draft", None
        plan.save(update_fields=["status", "approved_at"])
        return Response(PlanSerializer(self.get_queryset().get(pk=plan.pk)).data)

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        from apps.printing.views import print_document
        from apps.reports import output

        plan = self.get_object()
        months = ["", "ian.", "feb.", "mar.", "apr.", "mai", "iun.", "iul.", "aug.", "sep.", "oct.", "noi.", "dec."]
        lines = plan.lines.select_related("employee", "record").prefetch_related("employee__employments__subdivision",
                                                                                  "employee__employments__occupation")
        rows = []
        for ln in lines:
            job = next((e for e in ln.employee.employments.all() if e.status != "ended"), None)
            rows.append({"name": ln.employee.full_name(), "occ": job.occupation.name_ro if job else "",
                         "sub": job.subdivision.name_ro if job else "", "title": ln.title, "provider": ln.provider,
                         "month": months[ln.month] if ln.month else "", "hours": float(ln.hours),
                         "done": "realizat" if ln.record_id else ""})
        data = {"title": f"PLANUL ANUAL DE FORMARE PROFESIONALĂ A ANGAJAȚILOR PE ANUL {plan.year}",
                "subtitle": f"Nr. {plan.number} din {plan.date:%d.%m.%Y}" if plan.number else "",
                "columns": [{"key": "name", "title": "Numele, prenumele", "type": "text"}, {"key": "occ", "title": "Funcția", "type": "text"},
                            {"key": "sub", "title": "Subdiviziunea", "type": "text"}, {"key": "title", "title": "Cursul / tematica", "type": "text"},
                            {"key": "provider", "title": "Organizatorul", "type": "text"}, {"key": "month", "title": "Luna", "type": "text"},
                            {"key": "hours", "title": "Ore", "type": "num"}, {"key": "done", "title": "Realizare", "type": "text"}],
                "rows": rows, "totals": {"name": "Total", "hours": sum(r["hours"] for r in rows)},
                "summary": []}
        return print_document(request, "report", output.print_context(data), title=data["title"])


class PlanLineViewSet(viewsets.ModelViewSet):
    perm_module = "training"
    serializer_class = PlanLineSerializer
    pagination_class = None

    def get_queryset(self):
        qs = TrainingPlanLine.objects.filter(employee__in=_visible(self.request.user)).select_related(
            "employee", "record").prefetch_related(Prefetch("employee__employments", queryset=Employment.objects.select_related("subdivision")))
        plan = self.request.query_params.get("plan")
        if self.action == "list":
            if not plan:
                return qs.none()
            qs = qs.filter(plan_id=plan)
        return qs

    def _editable(self, plan):
        ensure_not_marked(plan)
        if plan.status == "approved":
            raise ValidationError({"detail": "Planul este aprobat; întoarceți-l în ciornă ca să-l schimbați."})

    def perform_create(self, serializer):
        self._editable(serializer.validated_data["plan"])
        if not staff.can_see(serializer.validated_data["employee"], self.request.user):
            raise NotFound()
        serializer.save()

    def perform_update(self, serializer):
        self._editable(serializer.instance.plan)
        serializer.save()

    def perform_destroy(self, instance):
        self._editable(instance.plan)
        instance.delete()
