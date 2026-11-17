from django.db.models import Count, Prefetch, Q, Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.deletion import DeletionMarkMixin, ensure_not_marked
from apps.staff import services as staff
from apps.staff.models import Employee, Employment

from . import services
from .models import Attestation, TrainingPlan, TrainingPlanLine, TrainingRecord
from .serializers import AttestationSerializer, PlanLineSerializer, PlanSerializer, TrainingRecordSerializer


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
    """Registrul EMC: activitățile de formare ale angajaților vizibili."""

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
        """Totalul orelor și creditelor din lista filtrată."""
        agg = self.get_queryset().aggregate(hours=Sum("hours"), credits=Sum("credits"), people=Count("employee", distinct=True))
        return Response({k: float(v or 0) for k, v in agg.items()})


class CreditsView(APIView):
    """Creditele EMC în perioada de atestare curentă, pe angajați (doar categoriile cu credite cerute)."""

    perm_module = "training"

    def get(self, request):
        day = _date(request, "on_date", timezone.localdate())
        rows = services.credits_rows(day, _sub_ids(request), request.query_params.get("category", ""), request.user.language or "ro")
        if request.query_params.get("employee"):
            rows = [r for r in rows if str(r["employee"]) == request.query_params["employee"]]
        status = request.query_params.get("status")
        if status:
            rows = [r for r in rows if r["status"] == status]
        counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("risk", "behind", "ok", "done")}
        return Response({"on_date": day, "rows": rows, "counts": counts})


class AttestationDueView(APIView):
    """Calendarul atestării: categoriile care expiră în următoarele luni."""

    perm_module = "training"

    def get(self, request):
        day = _date(request, "on_date", timezone.localdate())
        try:
            months = max(1, min(int(request.query_params.get("months") or 12), 36))
        except ValueError as exc:
            raise ValidationError({"months": "Număr de luni."}) from exc
        rows = services.attestation_due(day, months, _sub_ids(request), request.query_params.get("category", ""),
                                        request.user.language or "ro")
        return Response({"on_date": day, "rows": rows})


class AttestationViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "training"
    perm_actions = {"plan": "create", "make_order": "edit", "print_list": "view"}
    serializer_class = AttestationSerializer

    def get_queryset(self):
        p = self.request.query_params
        qs = Attestation.objects.filter(employee__in=_visible(self.request.user)).select_related(
            "employee", "specialty", "current_category", "requested_category", "result_category", "order_item__order"
        ).prefetch_related(Prefetch("employee__employments", queryset=Employment.objects.select_related("subdivision")))
        if p.get("status") == "open":
            qs = qs.filter(status__in=("planned", "submitted", "postponed"))
        elif p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("year"):
            qs = qs.filter(Q(session_date__year=p["year"]) | Q(session_date__isnull=True, created_at__year=p["year"]))
        if p.get("employee"):
            qs = qs.filter(employee_id=p["employee"])
        return qs.order_by("session_date", "employee__last_name")

    def perform_create(self, serializer):
        if not staff.can_see(serializer.validated_data["employee"], self.request.user):
            raise NotFound()
        serializer.save()

    def check_delete(self, instance):
        if instance.order_item_id:
            raise ValidationError({"detail": "Ordinul de conferire este făcut; anulați întâi ordinul."})

    @action(detail=False, methods=["post"])
    def plan(self, request):
        ids = [int(x) for x in request.data.get("employees") or []]
        visible = set(_visible(request.user).filter(pk__in=ids).values_list("pk", flat=True))
        session = request.data.get("session_date") or None
        created = services.plan_attestations([i for i in ids if i in visible], session)
        return Response({"created": len(created)})

    @action(detail=False, methods=["post"], url_path="make-order")
    def make_order(self, request):
        if not request.user.has_crm_perm("orders.create"):
            raise PermissionDenied("Nu aveți dreptul să faceți ordine.")
        ids = request.data.get("ids") or []
        atts = list(self.get_queryset().filter(pk__in=ids))
        if not atts:
            raise ValidationError({"detail": "Alegeți atestările cu rezultat pozitiv."})
        orders = services.make_award_orders(atts, request.user)
        return Response({"orders": [{"id": o.id, "number": o.number} for o in orders]})

    @action(detail=False, methods=["get"], url_path="print-list")
    def print_list(self, request):
        """Lista candidaților la atestare (demersul către comisie), pentru atestările filtrate."""
        from apps.printing.views import print_document
        from apps.reports import output

        rows = [{"name": a.employee.full_name(), "occ": next((e.occupation.name_ro for e in a.employee.employments.all()
                                                              if e.status != "ended"), ""),
                 "sub": next((e.subdivision.name_ro for e in a.employee.employments.all() if e.status != "ended"), ""),
                 "specialty": a.specialty.name_ro if a.specialty_id else "",
                 "current": a.current_category.name_ro if a.current_category_id else "fără categorie",
                 "due": a.due_date.isoformat() if a.due_date else None, "requested": a.requested_category.name_ro,
                 "session": a.session_date.isoformat() if a.session_date else None}
                for a in self.get_queryset().prefetch_related("employee__employments__occupation")]
        data = {"title": "LISTA CANDIDAȚILOR PENTRU ATESTARE", "subtitle": "pentru conferirea / confirmarea categoriei de calificare",
                "columns": [{"key": "name", "title": "Numele, prenumele", "type": "text"},
                            {"key": "occ", "title": "Funcția", "type": "text"}, {"key": "sub", "title": "Subdiviziunea", "type": "text"},
                            {"key": "specialty", "title": "Specialitatea", "type": "text"},
                            {"key": "current", "title": "Categoria actuală", "type": "text"},
                            {"key": "due", "title": "Expiră la", "type": "date"},
                            {"key": "requested", "title": "Categoria solicitată", "type": "text"},
                            {"key": "session", "title": "Data comisiei", "type": "date"}],
                "rows": rows, "totals": None, "summary": []}
        return print_document(request, "report", output.print_context(data), title="Lista candidaților pentru atestare")


class PlanViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "training"
    perm_actions = {"fill": "edit", "approve": "edit", "reopen": "edit", "print": "view"}
    serializer_class = PlanSerializer
    pagination_class = None

    def get_queryset(self):
        return TrainingPlan.objects.annotate(
            lines_count=Count("lines", distinct=True), done_count=Count("lines", filter=Q(lines__record__isnull=False), distinct=True),
            credits_total=Sum("lines__credits"))

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def check_delete(self, instance):
        if instance.status == "approved":
            raise ValidationError({"detail": "Planul aprobat nu se șterge; întoarceți-l întâi în ciornă."})

    @action(detail=True, methods=["post"])
    def fill(self, request, pk=None):
        plan = self.get_object()
        return Response({"added": services.fill_plan(plan, only_behind=request.data.get("only_behind", True) is not False)})

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
                         "month": months[ln.month] if ln.month else "", "hours": float(ln.hours), "credits": float(ln.credits),
                         "done": "realizat" if ln.record_id else ""})
        data = {"title": f"PLANUL ANUAL DE FORMARE PROFESIONALĂ CONTINUĂ PE ANUL {plan.year}",
                "subtitle": f"Nr. {plan.number} din {plan.date:%d.%m.%Y}" if plan.number else "",
                "columns": [{"key": "name", "title": "Numele, prenumele", "type": "text"}, {"key": "occ", "title": "Funcția", "type": "text"},
                            {"key": "sub", "title": "Subdiviziunea", "type": "text"}, {"key": "title", "title": "Cursul / tematica", "type": "text"},
                            {"key": "provider", "title": "Organizatorul", "type": "text"}, {"key": "month", "title": "Luna", "type": "text"},
                            {"key": "hours", "title": "Ore", "type": "num"}, {"key": "credits", "title": "Credite", "type": "num"},
                            {"key": "done", "title": "Realizare", "type": "text"}],
                "rows": rows, "totals": {"name": "Total", "hours": sum(r["hours"] for r in rows), "credits": sum(r["credits"] for r in rows)},
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


class SettingsView(APIView):
    perm_module = "training"

    def get(self, request):
        return Response(services.get_settings())

    def put(self, request):
        if not request.user.has_crm_perm("settings.edit"):
            raise PermissionDenied("Setările le schimbă administratorul.")
        return Response(services.save_settings(request.data))
