from rest_framework import serializers

from apps.org.serializers import user_lang

from .models import Attestation, TrainingPlan, TrainingPlanLine, TrainingRecord


def _name(obj, lang):
    return obj.local_name(lang) if obj else ""


class _EmployeeMixin(serializers.Serializer):
    employee_name = serializers.SerializerMethodField()
    tab_number = serializers.SerializerMethodField()

    def get_employee_name(self, obj):
        return obj.employee.full_name()

    def get_tab_number(self, obj):
        return obj.employee.tab_number


class TrainingRecordSerializer(_EmployeeMixin, serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    specialty_name = serializers.SerializerMethodField()
    order_ref = serializers.SerializerMethodField()

    class Meta:
        model = TrainingRecord
        fields = ["id", "employee", "employee_name", "tab_number", "kind", "kind_label", "title", "provider", "specialty",
                  "specialty_name", "date_from", "date_to", "hours", "credits", "certificate_number", "certificate_date",
                  "order_item", "order_ref", "note"]
        read_only_fields = ["order_item"]

    def get_specialty_name(self, obj):
        return _name(obj.specialty, user_lang(self))

    def get_order_ref(self, obj):
        return obj.order_item.order.reference() if obj.order_item_id else ""

    def validate(self, attrs):
        start, end = attrs.get("date_from", getattr(self.instance, "date_from", None)), attrs.get("date_to", getattr(self.instance, "date_to", None))
        if start and end and end < start:
            raise serializers.ValidationError({"date_to": "Sfârșitul este înaintea începutului."})
        return attrs


class PlanLineSerializer(_EmployeeMixin, serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    done = serializers.SerializerMethodField()
    subdivision = serializers.SerializerMethodField()

    class Meta:
        model = TrainingPlanLine
        fields = ["id", "plan", "employee", "employee_name", "tab_number", "subdivision", "kind", "kind_label", "title", "provider",
                  "month", "hours", "credits", "record", "done", "note", "sort"]
        read_only_fields = ["record"]

    def get_done(self, obj):
        if not obj.record_id:
            return ""
        r = obj.record
        return f"{r.title} ({r.date_from:%d.%m.%Y}, {r.credits} cr.)"

    def get_subdivision(self, obj):
        job = next((e for e in obj.employee.employments.all() if e.status != "ended"), None)
        return _name(job.subdivision, user_lang(self)) if job else ""

    def validate_month(self, value):
        if value is not None and not 1 <= value <= 12:
            raise serializers.ValidationError("Luna 1–12.")
        return value


class PlanSerializer(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)  # marcat pentru ștergere (formele documentelor)
    lines_count = serializers.IntegerField(read_only=True)
    done_count = serializers.IntegerField(read_only=True)
    credits_total = serializers.DecimalField(max_digits=10, decimal_places=1, read_only=True)

    class Meta:
        model = TrainingPlan
        fields = ["id", "deletion_mark", "year", "number", "date", "status", "note", "approved_at", "lines_count", "done_count", "credits_total"]
        read_only_fields = ["status", "approved_at"]


class AttestationSerializer(_EmployeeMixin, serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    specialty_name = serializers.SerializerMethodField()
    current_category_name = serializers.SerializerMethodField()
    requested_category_name = serializers.SerializerMethodField()
    result_category_name = serializers.SerializerMethodField()
    order_ref = serializers.SerializerMethodField()
    order_id = serializers.SerializerMethodField()
    subdivision = serializers.SerializerMethodField()

    class Meta:
        model = Attestation
        fields = ["id", "employee", "employee_name", "tab_number", "subdivision", "specialty", "specialty_name", "current_category",
                  "current_category_name", "due_date", "requested_category", "requested_category_name", "session_date",
                  "submitted_on", "status", "status_label", "result_category", "result_category_name", "result_date", "decision",
                  "order_item", "order_ref", "order_id", "note"]
        read_only_fields = ["order_item", "current_category", "due_date"]

    def get_specialty_name(self, obj):
        return _name(obj.specialty, user_lang(self))

    def get_current_category_name(self, obj):
        return _name(obj.current_category, user_lang(self))

    def get_requested_category_name(self, obj):
        return _name(obj.requested_category, user_lang(self))

    def get_result_category_name(self, obj):
        return _name(obj.result_category, user_lang(self))

    def get_order_ref(self, obj):
        return obj.order_item.order.reference() if obj.order_item_id else ""

    def get_order_id(self, obj):
        return obj.order_item.order_id if obj.order_item_id else None

    def get_subdivision(self, obj):
        job = next((e for e in obj.employee.employments.all() if e.status != "ended"), None)
        return _name(job.subdivision, user_lang(self)) if job else ""

    def validate(self, attrs):
        status = attrs.get("status", getattr(self.instance, "status", "planned"))
        if status in Attestation.POSITIVE:
            result = attrs.get("result_category", getattr(self.instance, "result_category", None))
            day = attrs.get("result_date", getattr(self.instance, "result_date", None))
            if not result or not day:
                raise serializers.ValidationError({"result_category": "Pentru rezultatul pozitiv scrieți categoria și data deciziei."})
        if self.instance and self.instance.order_item_id and any(k in attrs for k in ("result_category", "result_date", "status")):
            raise serializers.ValidationError({"detail": "Ordinul de conferire este deja făcut; rezultatul nu se mai schimbă."})
        return attrs
