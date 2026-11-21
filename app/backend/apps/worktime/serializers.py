import re

from rest_framework import serializers

from .models import (CalendarDay, HourType, JobHourRate, JobSchedule, OccupationHourRate, Roster, RosterLine, ShiftType, Timesheet,
                     TimesheetLine, WorkSchedule)


class HourTypeSerializer(serializers.ModelSerializer):
    """Tipul de ore: codul (și în formule — `Ore.COD`), grupa, legătura cu orele lucrate, cum se introduce, profilul."""

    group_label = serializers.CharField(source="get_group_display", read_only=True)
    work_time_label = serializers.CharField(source="get_work_time_display", read_only=True)
    entry_label = serializers.CharField(source="get_entry_display", read_only=True)
    profile_label = serializers.CharField(source="get_profile_display", read_only=True)
    pay_type_code = serializers.CharField(source="pay_type.code", read_only=True, default="")

    class Meta:
        model = HourType
        fields = ["id", "code", "name_ro", "name_ru", "name_en", "group", "group_label", "work_time", "work_time_label", "entry",
                  "entry_label", "profile", "profile_label", "in_all_timesheets", "pay_type", "pay_type_code", "sort", "is_active",
                  "is_system"]
        read_only_fields = ["is_system"]

    def validate_code(self, value):
        value = (value or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9_]{1,16}", value):
            raise serializers.ValidationError("Codul: litere latine, cifre și „_” (în formule se scrie Ore.COD).")
        if self.instance is not None and value != self.instance.code and self.instance.job_rates.exists():
            raise serializers.ValidationError("Tipul are tarife pe raporturi de muncă; codul nu se mai schimbă.")
        return value

    def validate_pay_type(self, value):
        if value is not None and (value.formula != "auto" or value.auto != "hour_types"):
            raise serializers.ValidationError("Tipul de calcul trebuie să fie automat, „Ore pe tipuri”.")
        return value


class _RateFields(serializers.ModelSerializer):
    hour_type_code = serializers.CharField(source="hour_type.code", read_only=True)
    hour_type_name = serializers.CharField(source="hour_type.name_ro", read_only=True)

    def validate(self, attrs):
        for key in ("rate", "guaranteed_hours"):
            if attrs.get(key) is not None and attrs[key] < 0:
                raise serializers.ValidationError({key: "Nu poate fi negativ."})
        g = attrs.get("guaranteed_hours")
        if g is not None and g > 744:
            raise serializers.ValidationError({"guaranteed_hours": "Cel mult 744 de ore pe lună."})
        return attrs


class JobHourRateSerializer(_RateFields):
    """Tariful pe tipul de ore al raportului. Cel venit din ordin nu se schimbă de mână (se schimbă printr-un ordin nou)."""

    source = serializers.SerializerMethodField()

    class Meta:
        model = JobHourRate
        fields = ["id", "employment", "hour_type", "hour_type_code", "hour_type_name", "rate", "guaranteed_hours", "date_from",
                  "date_to", "document", "source"]

    def get_source(self, obj):
        if obj.order_item_id:
            order = obj.order_item.order
            return {"kind": "order", "id": order.pk, "label": f"Ordinul nr. {order.reference()}", "status": order.status}
        return {"kind": "manual", "id": None, "label": "", "status": ""}

    def validate(self, attrs):
        from . import rates

        attrs = super().validate(attrs)
        if self.instance is not None and self.instance.order_item_id:
            raise serializers.ValidationError({"detail": "Tariful vine dintr-un ordin; se modifică / se oprește printr-un ordin nou "
                                                         "(tabelul „Tarife pe tipuri de ore”) sau prin anularea ordinului."})
        job = attrs.get("employment", getattr(self.instance, "employment", None))
        ht = attrs.get("hour_type", getattr(self.instance, "hour_type", None))
        start = attrs.get("date_from", getattr(self.instance, "date_from", None))
        end = attrs.get("date_to", getattr(self.instance, "date_to", None))
        if attrs.get("rate", getattr(self.instance, "rate", None)) is None:
            raise serializers.ValidationError({"rate": "Dați tariful pe oră."})
        if end and start and end < start:
            raise serializers.ValidationError({"date_to": "„Până la” este înaintea lui „de la”."})
        if job is not None and ht is not None and start is not None:
            if start < job.date_from:
                raise serializers.ValidationError({"date_from": "Tariful începe înaintea raportului de muncă."})
            who = f"{job.employee.full_name()}, {ht.code}"
            rates.check_mode(job, start, who)
            rates.check_overlap(job, ht, start, end, who, exclude=getattr(self.instance, "pk", None))
        return attrs


class OccupationHourRateSerializer(_RateFields):
    class Meta:
        model = OccupationHourRate
        fields = ["id", "occupation", "hour_type", "hour_type_code", "hour_type_name", "rate", "guaranteed_hours", "sort"]


class ShiftTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftType
        fields = ["id", "code", "name", "hours", "night_hours", "start", "color", "sort", "is_active"]

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
