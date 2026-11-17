from rest_framework import serializers

from apps.org import calendar

from .models import LeaveAdjustment, LeaveRequest, LeaveRight, LeaveSchedule, LeaveScheduleLine, SickLeave
from .services import period


def _order_ref(item):
    return {"id": item.order_id, "label": item.order.reference() or "ciornă", "status": item.order.status} if item else None


class LeaveRightSerializer(serializers.ModelSerializer):
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)

    class Meta:
        model = LeaveRight
        fields = ["id", "employee", "reason", "reason_label", "days", "date_from", "date_to", "note"]

    def validate(self, attrs):
        start, end = attrs.get("date_from"), attrs.get("date_to")
        if start and end and end < start:
            raise serializers.ValidationError({"date_to": "Sfârșitul este înaintea începutului."})
        return attrs


class LeaveAdjustmentSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    order = serializers.SerializerMethodField()

    class Meta:
        model = LeaveAdjustment
        fields = ["id", "employee", "kind", "kind_label", "date", "work_year_from", "days", "note", "order"]

    def get_order(self, obj):
        return _order_ref(obj.order_item)

    def validate_days(self, value):
        if value == 0:
            raise serializers.ValidationError("Zilele nu pot fi 0.")
        return value


class LeaveScheduleSerializer(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)  # marcat pentru ștergere (formele documentelor)
    subdivision_name = serializers.CharField(source="subdivision.name_ro", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    lines_count = serializers.IntegerField(read_only=True, default=0)
    planned_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = LeaveSchedule
        fields = ["id", "deletion_mark", "year", "subdivision", "subdivision_name", "status", "status_label", "approved_by", "approved_at", "note",
                  "lines_count", "planned_count", "created_at"]
        read_only_fields = ["status", "approved_at"]


class LeaveScheduleLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveScheduleLine
        fields = ["id", "schedule", "employee", "date_from", "days", "date_to", "moved_to", "note", "sort"]
        read_only_fields = ["date_to"]

    def validate(self, attrs):
        start = attrs.get("date_from", getattr(self.instance, "date_from", None))
        days = attrs.get("days", getattr(self.instance, "days", 0))
        schedule = attrs.get("schedule", getattr(self.instance, "schedule", None))
        if start and schedule and start.year != schedule.year:
            raise serializers.ValidationError({"date_from": f"Data trebuie să fie în anul {schedule.year}."})
        attrs["date_to"] = calendar.leave_end(start, days) if start and days else None
        return attrs


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_tab = serializers.CharField(source="employee.tab_number", read_only=True)
    subdivision = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    decided_by_name = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = ["id", "employee", "employee_name", "employee_tab", "subdivision", "kind", "kind_label", "date_from", "days",
                  "date_to", "work_year_from", "work_year_to", "reason", "status", "status_label", "decided_by_name",
                  "decided_at", "decision_note", "order", "created_at"]
        read_only_fields = ["status", "decided_at", "decision_note"]
        extra_kwargs = {"date_to": {"required": False}, "days": {"required": False}}

    def get_subdivision(self, obj):
        job = obj.employee.main_employment()
        return job.subdivision.name_ro if job else ""

    def get_decided_by_name(self, obj):
        return (obj.decided_by.get_full_name() or obj.decided_by.username) if obj.decided_by_id else ""

    def get_order(self, obj):
        return _order_ref(obj.order_item)

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", "annual"))
        start = attrs.get("date_from", getattr(self.instance, "date_from", None))
        if "date_to" in attrs and "days" not in attrs:
            start, end, days = period(kind, start, end=attrs["date_to"])
        else:
            start, end, days = period(kind, start, days=attrs.get("days", getattr(self.instance, "days", 0)))
        attrs.update({"date_from": start, "date_to": end, "days": days})
        return attrs


class SickLeaveSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_tab = serializers.CharField(source="employee.tab_number", read_only=True)
    subdivision = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    continuation_label = serializers.SerializerMethodField()
    continued_by = serializers.SerializerMethodField()

    class Meta:
        model = SickLeave
        fields = ["id", "employee", "employee_name", "employee_tab", "subdivision", "series", "number", "issued_on", "issued_by",
                  "kind", "kind_label", "date_from", "date_to", "days", "continuation_of", "continuation_label", "continued_by",
                  "return_date", "file", "note", "absence", "created_at"]
        read_only_fields = ["days", "absence"]

    def get_subdivision(self, obj):
        job = obj.employee.main_employment()
        return job.subdivision.name_ro if job else ""

    def get_continuation_label(self, obj):
        return str(obj.continuation_of) if obj.continuation_of_id else ""

    def get_continued_by(self, obj):
        """Certificatul care îl continuă (nemarcat pentru ștergere): cel continuat e încheiat, chiar fără data prezentării."""
        found = getattr(obj, "live_continuations", None)  # lista îl aduce o dată pentru toate rândurile
        if found is None:
            found = obj.continuations.filter(deletion_mark=False) if obj.pk else []
        nxt = min(found, key=lambda c: (c.date_from, c.pk), default=None)
        return str(nxt) if nxt else ""

    def validate(self, attrs):
        prev = attrs.get("continuation_of")
        employee = attrs.get("employee", getattr(self.instance, "employee", None))
        if prev is not None and prev.employee_id != getattr(employee, "pk", None):
            raise serializers.ValidationError({"continuation_of": "Certificatul continuat este al altui angajat."})
        return attrs
