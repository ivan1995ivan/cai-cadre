from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.deletion import DeletionMarkMixin
from apps.org.serializers import user_lang
from apps.staff import services as staff
from apps.training.views import _date, _sub_ids, _visible

from . import services
from .models import MedicalExam, SafetyBriefing, Vaccination


class _Base(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    tab_number = serializers.SerializerMethodField()

    def get_employee_name(self, obj):
        return obj.employee.full_name()

    def get_tab_number(self, obj):
        return obj.employee.tab_number

    def validate(self, attrs):
        start = attrs.get("date", getattr(self.instance, "date", None))
        nxt = attrs.get("next_date", getattr(self.instance, "next_date", None))
        if start and nxt and nxt < start:
            raise serializers.ValidationError({"next_date": "Termenul următor este înaintea datei."})
        return attrs


class ExamSerializer(_Base):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    conclusion_label = serializers.CharField(source="get_conclusion_display", read_only=True)

    class Meta:
        model = MedicalExam
        fields = ["id", "employee", "employee_name", "tab_number", "kind", "kind_label", "date", "institution", "conclusion",
                  "conclusion_label", "restrictions", "next_date", "document", "note"]


class VaccinationSerializer(_Base):
    vaccine_name = serializers.SerializerMethodField()

    class Meta:
        model = Vaccination
        fields = ["id", "employee", "employee_name", "tab_number", "vaccine", "vaccine_name", "dose", "date", "series", "next_date",
                  "refused", "note"]

    def get_vaccine_name(self, obj):
        return obj.vaccine.local_name(user_lang(self))

    def validate_vaccine(self, value):
        if value.kind != "vaccine":
            raise serializers.ValidationError("Alegeți vaccinul din clasificator.")
        return value


class BriefingSerializer(_Base):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = SafetyBriefing
        fields = ["id", "employee", "employee_name", "tab_number", "kind", "kind_label", "date", "instructor", "topic", "next_date",
                  "note"]


class _HealthViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    """Examenele / vaccinările / instructajele angajaților vizibili; termenul următor se completează singur."""

    perm_module = "health"
    model = None

    def get_queryset(self):
        p = self.request.query_params
        qs = self.model.objects.filter(employee__in=_visible(self.request.user)).select_related("employee")
        if p.get("employee"):
            qs = qs.filter(employee_id=p["employee"])
            self.pagination_class = None
        if p.get("date_from"):
            qs = qs.filter(date__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(date__lte=p["date_to"])
        if p.get("subdivision"):
            qs = qs.filter(employee__employments__subdivision_id__in=_sub_ids(self.request)).distinct()
        if p.get("q"):
            q = p["q"].strip()
            qs = qs.filter(Q(employee__last_name__icontains=q) | Q(employee__first_name__icontains=q) | Q(employee__tab_number=q))
        return qs

    def _save(self, serializer):
        employee = serializer.validated_data.get("employee") or serializer.instance.employee
        if not staff.can_see(employee, self.request.user):
            raise NotFound()
        obj = serializer.save()
        if not obj.next_date:
            services.fill_next_date(obj)
            if obj.next_date:
                obj.save(update_fields=["next_date"])

    perform_create = perform_update = _save


class ExamViewSet(_HealthViewSet):
    model = MedicalExam
    serializer_class = ExamSerializer


class VaccinationViewSet(_HealthViewSet):
    model = Vaccination
    serializer_class = VaccinationSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("vaccine")


class BriefingViewSet(_HealthViewSet):
    model = SafetyBriefing
    serializer_class = BriefingSerializer


class DueView(APIView):
    """Termenele: examenul medical, instructajul SSM, vaccinurile — depășite, lipsă sau în următoarele zile."""

    perm_module = "health"

    def _rows(self, request):
        horizon = request.query_params.get("horizon")
        try:
            horizon = int(horizon) if horizon not in (None, "") else None
        except ValueError as exc:
            raise ValidationError({"horizon": "Număr de zile."}) from exc
        what = request.query_params.get("what") or None
        if what not in (None, "exam", "briefing", "vaccine"):
            raise ValidationError({"what": "exam, briefing sau vaccine."})
        from django.utils import timezone

        return services.due_rows(_date(request, "on_date", timezone.localdate()), _sub_ids(request), what,
                                 request.user.language or "ro", horizon)

    def get(self, request):
        rows = self._rows(request)
        if request.query_params.get("export") == "print":
            from apps.printing.views import print_document
            from apps.reports import output

            data = {"title": "LISTA NOMINALĂ A ANGAJAȚILOR CARE URMEAZĂ SĂ FIE TRIMIȘI",
                    "subtitle": "la examenul medical / instructajul SSM / vaccinare",
                    "columns": [{"key": "name", "title": "Numele, prenumele", "type": "text"},
                                {"key": "occupation", "title": "Funcția", "type": "text"},
                                {"key": "subdivision", "title": "Subdiviziunea", "type": "text"},
                                {"key": "label", "title": "Ce", "type": "text"}, {"key": "last", "title": "Ultima dată", "type": "date"},
                                {"key": "due", "title": "Termenul", "type": "date"}, {"key": "detail", "title": "Mențiuni", "type": "text"}],
                    "rows": [{**r, "last": r["last"].isoformat() if r["last"] else None, "due": r["due"].isoformat() if r["due"] else None}
                             for r in rows], "totals": None, "summary": []}
            return print_document(request, "report", output.print_context(data), title="Lista pentru medicina muncii")
        counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("overdue", "missing", "due")}
        return Response({"rows": rows, "counts": counts, "settings": services.get_settings()})

    def post(self, request):
        """Ordinul de trimitere la examenul medical pentru angajații aleși."""
        if not request.user.has_crm_perm("orders.create"):
            raise PermissionDenied("Nu aveți dreptul să faceți ordine.")
        ids = request.data.get("employees") or []
        people = list(_visible(request.user).filter(pk__in=ids))
        order = services.make_exam_order(people, request.user)
        return Response({"order": order.id})


class SettingsView(APIView):
    perm_module = "health"

    def get(self, request):
        return Response(services.get_settings())

    def put(self, request):
        if not request.user.has_crm_perm("settings.edit"):
            raise PermissionDenied("Setările le schimbă administratorul.")
        return Response(services.save_settings(request.data))

