from rest_framework import serializers

from .models import CalendarDay, JobSchedule, Roster, RosterLine, ShiftType, Timesheet, TimesheetLine, WorkSchedule


class ShiftTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftType
        fields = ["id", "code", "name", "hours", "night_hours", "start", "is_duty", "color", "sort", "is_active"]

    def validate(self, attrs):
        hours = attrs.get("hours", getattr(self.instance, "hours", None))
        night = attrs.get("night_hours", getattr(self.instance, "night_hours", 0))
        if hours is not None and night > hours:
            raise serializers.ValidationError({"night_hours": "Orele de noapte nu pot fi mai multe decât orele turei."})
        return attrs


class WorkScheduleSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    jobs_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = WorkSchedule
        fields = ["id", "code", "name", "kind", "kind_label", "weekly_hours", "week", "cycle", "cycle_start", "holidays_off",
                  "note", "is_active", "jobs_count"]

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", "week"))
        week = attrs.get("week", getattr(self.instance, "week", []))
        cycle = attrs.get("cycle", getattr(self.instance, "cycle", []))
        if kind == "week" and len(week or []) != 7:
            raise serializers.ValidationError({"week": "Graficul săptămânal are 7 zile (luni–duminică)."})
        if kind == "cycle" and not cycle:
            raise serializers.ValidationError({"cycle": "Dați turele ciclului (de ex. Z12, N12, liber, liber)."})
        codes = {s.code for s in ShiftType.objects.all()}
        for code in [*(week or []), *(cycle or [])]:
            if code and code not in codes and not str(code).replace(",", ".").replace(".", "").isdigit():
                raise serializers.ValidationError({"week": f"Tura „{code}” nu există în clasificatorul de ture."})
        return attrs


class JobScheduleSerializer(serializers.ModelSerializer):
    schedule_name = serializers.CharField(source="schedule.name", read_only=True)

    class Meta:
        model = JobSchedule
        fields = ["id", "employment", "schedule", "schedule_name", "date_from", "cycle_offset"]


class CalendarDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarDay
        fields = ["id", "date", "working", "hours_less", "note"]


class _MonthDoc(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)  # marcat pentru ștergere (formele documentelor)
    subdivision_name = serializers.CharField(source="subdivision.name_ro", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    lines_count = serializers.IntegerField(read_only=True, default=0)

    def validate(self, attrs):
        month = attrs.get("month", getattr(self.instance, "month", 1))
        if not 1 <= month <= 12:
            raise serializers.ValidationError({"month": "Luna este între 1 și 12."})
        return attrs


class RosterSerializer(_MonthDoc):
    class Meta:
        model = Roster
        fields = ["id", "deletion_mark", "subdivision", "subdivision_name", "year", "month", "status", "status_label", "approved_at", "note",
                  "lines_count", "created_at"]
        read_only_fields = ["status", "approved_at"]


class RosterLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = RosterLine
        fields = ["id", "roster", "employment", "days", "note", "sort"]

    def validate_days(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Zilele sunt un obiect {zi: cod}.")
        return {str(k): str(v).strip() for k, v in value.items() if str(v).strip()}


class TimesheetSerializer(_MonthDoc):
    class Meta:
        model = Timesheet
        fields = ["id", "deletion_mark", "subdivision", "subdivision_name", "year", "month", "status", "status_label", "submitted_at", "closed_at",
                  "note", "lines_count", "created_at"]
        read_only_fields = ["status", "submitted_at", "closed_at"]


class TimesheetLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimesheetLine
        fields = ["id", "timesheet", "employment", "days", "totals", "note", "sort"]
        read_only_fields = ["days", "totals"]
