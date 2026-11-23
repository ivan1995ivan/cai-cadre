from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from . import services
from .models import (Brigade, BrigadeMember, Operation, OperationRate, ProductionLine, ProductionMember, ProductionReport, TariffGrid,
                     TariffRank)


def _text(exc: ValidationError) -> str:
    detail = exc.detail
    return str(detail.get("detail") if isinstance(detail, dict) else detail)


def job_label(j) -> str:
    return f"{j.get_kind_display()}: {j.occupation.name_ro}" if j else ""


# --- grila tarifară ----------------------------------------------------------------------------------------------------
class TariffRankSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    hourly = serializers.SerializerMethodField()

    class Meta:
        model = TariffRank
        fields = ["id", "rank", "coefficient", "rate", "hourly"]

    def get_hourly(self, obj):
        return obj.hourly() if obj.grid_id else None


class TariffGridSerializer(serializers.ModelSerializer):
    """Grila cu categoriile ei (se trimit cu grila și o înlocuiesc întreagă)."""

    deletion_mark = serializers.BooleanField(read_only=True)
    ranks = TariffRankSerializer(many=True, required=False)

    class Meta:
        model = TariffGrid
        fields = ["id", "deletion_mark", "code", "name", "date_from", "base_rate", "document", "note", "ranks"]

    def validate_code(self, value):
        value = (value or "").strip().upper()
        if not value or not all(ch.isalnum() or ch in "_-" for ch in value):
            raise serializers.ValidationError("Codul: litere latine, cifre, „_” și „-”.")
        return value

    def validate(self, attrs):
        if attrs.get("base_rate") is not None and attrs["base_rate"] <= 0:
            raise serializers.ValidationError({"base_rate": "Tariful categoriei I este mai mare decât 0."})
        ranks = attrs.get("ranks")
        if ranks is not None:
            seen = set()
            for r in ranks:
                if r["rank"] < 1 or r["rank"] > 30:
                    raise serializers.ValidationError({"ranks": "Categoriile sunt de la 1 la 30."})
                if r["rank"] in seen:
                    raise serializers.ValidationError({"ranks": f"Categoria {r['rank']} apare de două ori."})
                seen.add(r["rank"])
                if r.get("coefficient") is None or r["coefficient"] <= 0:
                    raise serializers.ValidationError({"ranks": f"Categoria {r['rank']}: coeficientul este mai mare decât 0."})
                if r.get("rate") is not None and r["rate"] <= 0:
                    raise serializers.ValidationError({"ranks": f"Categoria {r['rank']}: tariful scris direct este mai mare decât 0."})
        return attrs

    def _save_ranks(self, grid, rows):
        if rows is None:
            return
        keep = []
        for data in rows:
            data = dict(data)
            data.pop("id", None)
            obj, _ = TariffRank.objects.update_or_create(grid=grid, rank=data["rank"], defaults={
                "coefficient": data.get("coefficient") or Decimal("1"), "rate": data.get("rate")})
            keep.append(obj.pk)
        grid.ranks.exclude(pk__in=keep).delete()

    @transaction.atomic
    def create(self, validated_data):
        rows = validated_data.pop("ranks", [])
        grid = super().create(validated_data)
        self._save_ranks(grid, rows)
        return grid

    @transaction.atomic
    def update(self, instance, validated_data):
        rows = validated_data.pop("ranks", None)
        grid = super().update(instance, validated_data)
        self._save_ranks(grid, rows)
        return grid


# --- lucrările ---------------------------------------------------------------------------------------------------------
class OperationRateSerializer(serializers.ModelSerializer):
    norm_kind_label = serializers.CharField(source="get_norm_kind_display", read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = OperationRate
        fields = ["id", "operation", "date_from", "norm_kind", "norm_kind_label", "norm_value", "grid_code", "rank", "piece_rate",
                  "document", "price"]

    def get_price(self, obj):
        """Tariful pe unitate la data normei (sau motivul pentru care nu se poate socoti)."""
        try:
            p = services.price(obj.operation, obj.date_from)
        except ValidationError as exc:  # explicația erorii merge în listă, nu oprește lista
            return {"rate": None, "how": _text(exc)}
        return {"rate": p["rate"], "how": p["how"]}

    def validate(self, attrs):
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))  # noqa: E731
        value, piece, grid, rank = get("norm_value"), get("piece_rate"), (get("grid_code") or "").strip().upper(), get("rank")
        if value is None or value <= 0:
            raise serializers.ValidationError({"norm_value": "Norma este mai mare decât 0."})
        if piece is not None and piece <= 0:
            raise serializers.ValidationError({"piece_rate": "Tariful pe unitate este mai mare decât 0."})
        if piece is None and (not grid or rank is None):
            raise serializers.ValidationError({"piece_rate": "Dați tariful pe unitate sau grila tarifară și categoria lucrării."})
        if grid and not TariffGrid.objects.filter(code=grid).exists():
            raise serializers.ValidationError({"grid_code": f"Grila tarifară {grid} nu există."})
        if "grid_code" in attrs:
            attrs["grid_code"] = grid
        return attrs


class OperationSerializer(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)
    unit_label = serializers.CharField(source="get_unit_display", read_only=True)
    subdivision_name = serializers.CharField(source="subdivision.name_ro", read_only=True, default="")
    current = serializers.SerializerMethodField()

    class Meta:
        model = Operation
        fields = ["id", "deletion_mark", "code", "name_ro", "name_ru", "name_en", "unit", "unit_label", "subdivision", "subdivision_name",
                  "progressive", "note", "sort", "is_active", "current"]

    def validate_code(self, value):
        value = (value or "").strip().upper()
        if not value or not all(ch.isalnum() or ch in "_-." for ch in value):
            raise serializers.ValidationError("Codul: litere latine, cifre, „_”, „-” și „.”.")
        return value

    def get_current(self, obj):
        """Norma și tariful în vigoare azi (pentru listă)."""
        from django.utils import timezone

        day = timezone.localdate()
        r = services.rate_on(obj, day)
        if r is None:
            return None
        try:
            p = services.price(obj, day)
            rate, how = p["rate"], p["how"]
        except ValidationError as exc:
            rate, how = None, _text(exc)
        return {"date_from": r.date_from, "norm_kind": r.norm_kind, "norm_value": r.norm_value, "rate": rate, "how": how}


# --- brigăzile ---------------------------------------------------------------------------------------------------------
class BrigadeMemberSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    employee = serializers.IntegerField(source="employment.employee_id", read_only=True)
    employee_name = serializers.CharField(source="employment.employee.full_name", read_only=True)
    tab_number = serializers.CharField(source="employment.employee.tab_number", read_only=True)
    employment_label = serializers.SerializerMethodField()

    class Meta:
        model = BrigadeMember
        fields = ["id", "employment", "employee", "employee_name", "tab_number", "employment_label", "coefficient", "date_from", "date_to"]

    def get_employment_label(self, obj):
        return job_label(obj.employment)


class BrigadeSerializer(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)
    members = BrigadeMemberSerializer(many=True, required=False)
    distribution_label = serializers.CharField(source="get_distribution_display", read_only=True)
    subdivision_name = serializers.CharField(source="subdivision.name_ro", read_only=True, default="")
    leader_name = serializers.CharField(source="leader.employee.full_name", read_only=True, default="")

    class Meta:
        model = Brigade
        fields = ["id", "deletion_mark", "code", "name", "subdivision", "subdivision_name", "distribution", "distribution_label", "leader",
                  "leader_name", "note", "is_active", "members"]

    def validate_code(self, value):
        value = (value or "").strip().upper()
        if not value or not all(ch.isalnum() or ch in "_-" for ch in value):
            raise serializers.ValidationError("Codul: litere latine, cifre, „_” și „-”.")
        return value

    def validate(self, attrs):
        for n, m in enumerate(attrs.get("members") or [], start=1):
            if m.get("coefficient") is None or m["coefficient"] < 0 or m["coefficient"] > 10:
                raise serializers.ValidationError({"members": f"Membrul {n}: coeficientul de participare este între 0 și 10."})
            if m.get("date_to") and m["date_to"] < m["date_from"]:
                raise serializers.ValidationError({"members": f"Membrul {n}: „până la” este înaintea lui „de la”."})
        return attrs

    def _save_members(self, brigade, rows):
        if rows is None:
            return
        keep = []
        for data in rows:
            data = dict(data)
            pk = data.pop("id", None)
            obj = brigade.members.filter(pk=pk).first() if pk else None
            if obj is None:
                obj = BrigadeMember(brigade=brigade)
            for k, v in data.items():
                setattr(obj, k, v)
            obj.save()
            keep.append(obj.pk)
        brigade.members.exclude(pk__in=keep).delete()

    @transaction.atomic
    def create(self, validated_data):
        rows = validated_data.pop("members", [])
        obj = super().create(validated_data)
        self._save_members(obj, rows)
        return obj

    @transaction.atomic
    def update(self, instance, validated_data):
        rows = validated_data.pop("members", None)
        obj = super().update(instance, validated_data)
        self._save_members(obj, rows)
        return obj


# --- raportul de producție ---------------------------------------------------------------------------------------------
class ProductionLineSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    employee = serializers.IntegerField(source="employment.employee_id", read_only=True, default=None)
    employee_name = serializers.CharField(source="employment.employee.full_name", read_only=True, default="")
    tab_number = serializers.CharField(source="employment.employee.tab_number", read_only=True, default="")
    employment_label = serializers.SerializerMethodField()
    operation_code = serializers.CharField(source="operation.code", read_only=True)
    operation_name = serializers.CharField(source="operation.name_ro", read_only=True)
    unit_label = serializers.CharField(source="operation.get_unit_display", read_only=True)
    progressive = serializers.BooleanField(source="operation.progressive", read_only=True)

    class Meta:
        model = ProductionLine
        fields = ["id", "employment", "employee", "employee_name", "tab_number", "employment_label", "operation", "operation_code",
                  "operation_name", "unit_label", "progressive", "quantity", "defect_nofault", "defect_partial", "defect_partial_pct",
                  "defect_worker", "hours", "note", "rate", "norm_time", "amount", "normed_hours", "how", "sort"]
        read_only_fields = ["rate", "norm_time", "amount", "normed_hours", "how", "sort"]

    def get_employment_label(self, obj):
        return job_label(obj.employment)


class ProductionMemberSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    employee = serializers.IntegerField(source="employment.employee_id", read_only=True)
    employee_name = serializers.CharField(source="employment.employee.full_name", read_only=True)
    tab_number = serializers.CharField(source="employment.employee.tab_number", read_only=True)
    employment_label = serializers.SerializerMethodField()

    class Meta:
        model = ProductionMember
        fields = ["id", "employment", "employee", "employee_name", "tab_number", "employment_label", "hours", "coefficient", "hourly",
                  "amount", "progressive_amount", "normed_hours", "sort"]
        read_only_fields = ["hourly", "amount", "progressive_amount", "normed_hours", "sort"]

    def get_employment_label(self, obj):
        return job_label(obj.employment)


class ProductionReportSerializer(serializers.ModelSerializer):
    """Raportul cu lucrările și membrii lui (se trimit cu raportul și îl înlocuiesc întreg); la salvare se socotesc din nou."""

    deletion_mark = serializers.BooleanField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    brigade_name = serializers.CharField(source="brigade.name", read_only=True, default="")
    subdivision_name = serializers.CharField(source="subdivision.name_ro", read_only=True, default="")
    lines = ProductionLineSerializer(many=True, required=False)
    members = ProductionMemberSerializer(many=True, required=False)
    totals = serializers.SerializerMethodField()
    problems = serializers.SerializerMethodField()
    who = serializers.SerializerMethodField()

    class Meta:
        model = ProductionReport
        fields = ["id", "deletion_mark", "number", "date", "kind", "kind_label", "subdivision", "subdivision_name", "brigade",
                  "brigade_name", "status", "status_label", "note", "created_at", "approved_at", "lines", "members", "totals",
                  "problems", "who"]
        read_only_fields = ["number", "status", "created_at", "approved_at"]

    def get_totals(self, obj):
        return services.totals(obj)

    def get_problems(self, obj):
        return getattr(obj, "_problems", [])

    def get_who(self, obj):
        if obj.kind == "brigade":
            return obj.brigade.name if obj.brigade_id else ""
        names = list(dict.fromkeys(ln.employment.employee.short_name() for ln in obj.lines.all() if ln.employment_id))
        return ", ".join(names[:4]) + (f" și încă {len(names) - 4}" if len(names) > 4 else "")

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", "individual"))
        brigade = attrs.get("brigade", getattr(self.instance, "brigade", None))
        if kind == "brigade" and brigade is None:
            raise serializers.ValidationError({"brigade": "Alegeți brigada."})
        if kind == "individual":
            attrs["brigade"] = None
        for n, ln in enumerate(attrs.get("lines") or [], start=1):
            for key in ("quantity", "defect_nofault", "defect_partial", "defect_worker", "hours", "defect_partial_pct"):
                if ln.get(key) is not None and ln[key] < 0:
                    raise serializers.ValidationError({"lines": f"Rândul {n}: valorile nu pot fi negative."})
            if kind == "brigade":
                ln["employment"] = None
        if kind == "brigade":
            seen = set()
            for n, m in enumerate(attrs.get("members") or [], start=1):
                if m["employment"].pk in seen:
                    raise serializers.ValidationError({"members": f"Membrul {n} apare de două ori."})
                seen.add(m["employment"].pk)
        else:
            attrs["members"] = []
        return attrs

    def _save_rows(self, parent_rows, rows, model, **fk):
        if rows is None:
            return
        keep = []
        for n, data in enumerate(rows, start=1):
            data = dict(data)
            pk = data.pop("id", None)
            obj = parent_rows.filter(pk=pk).first() if pk else None
            if obj is None:
                obj = model(**fk)
            for k, v in data.items():
                setattr(obj, k, v)
            obj.sort = n * 10
            obj.save()
            keep.append(obj.pk)
        parent_rows.exclude(pk__in=keep).delete()

    def _save_all(self, doc, lines, members):
        self._save_rows(doc.lines, lines, ProductionLine, report=doc)
        if members is not None:
            if doc.kind == "brigade":
                self._save_rows(doc.members, members, ProductionMember, report=doc)
            else:
                doc.members.all().delete()
        doc._problems = services.recompute(doc)

    @transaction.atomic
    def create(self, validated_data):
        lines, members = validated_data.pop("lines", []), validated_data.pop("members", [])
        doc = super().create(validated_data)
        self._save_all(doc, lines, members)
        return doc

    @transaction.atomic
    def update(self, instance, validated_data):
        lines, members = validated_data.pop("lines", None), validated_data.pop("members", None)
        doc = super().update(instance, validated_data)
        self._save_all(doc, lines, members)
        return doc
