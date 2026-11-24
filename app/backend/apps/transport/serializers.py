from rest_framework import serializers

from apps.staff.models import Employment

from . import services
from .models import Country, KmRate, PerDiemNorm, Trip, TripDiem, TripLeg, Vehicle


def job_label(job) -> str:
    if job is None:
        return ""
    return f"{job.employee.full_name()} — {job.get_kind_display()}, {job.occupation.name_ro}"


class VehicleSerializer(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    subdivision_name = serializers.CharField(source="subdivision.name_ro", read_only=True, default="")

    class Meta:
        model = Vehicle
        fields = ["id", "deletion_mark", "plate", "kind", "kind_label", "brand", "model", "category", "tachograph", "fuel_norm",
                  "subdivision", "subdivision_name", "note", "is_active"]

    def validate_plate(self, value):
        value = " ".join(value.upper().split())
        if not value:
            raise serializers.ValidationError("Scrieți numărul de înmatriculare.")
        return value


class KmRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KmRate
        fields = ["id", "date_from", "trip_kind", "scope", "vehicle_kind", "rate", "document"]

    def validate_rate(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("Tariful nu poate fi negativ.")
        return value


class PerDiemNormSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name_ro", read_only=True)
    country_code = serializers.CharField(source="country.code", read_only=True)

    class Meta:
        model = PerDiemNorm
        fields = ["id", "country", "country_code", "country_name", "date_from", "currency", "amount", "document"]

    def validate_currency(self, value):
        value = (value or "").upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Valuta — codul din trei litere (EUR, USD…).")
        return value

    def validate_amount(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Norma e mai mare decât 0.")
        return value

    def validate(self, attrs):
        country = attrs.get("country", getattr(self.instance, "country", None))
        day = attrs.get("date_from", getattr(self.instance, "date_from", None))
        clash = PerDiemNorm.objects.filter(country=country, date_from=day)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({"date_from": "Țara are deja o normă din această dată."})
        return attrs


class CountrySerializer(serializers.ModelSerializer):
    current = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = ["id", "code", "name_ro", "name_ru", "name_en", "sort", "is_active", "current"]

    def validate_code(self, value):
        value = (value or "").upper()
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError("Codul țării are două litere (ISO 3166-1): DE, PL, RO…")
        return value

    def get_current(self, obj):
        from django.utils import timezone

        today = timezone.localdate()
        norms = [n for n in obj.norms.all() if n.date_from <= today]
        n = max(norms, key=lambda x: x.date_from, default=None)
        return {"amount": float(n.amount), "currency": n.currency, "date_from": n.date_from} if n else None


class TripLegSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    country_code = serializers.CharField(source="country.code", read_only=True)
    country_name = serializers.CharField(source="country.name_ro", read_only=True)

    class Meta:
        model = TripLeg
        fields = ["id", "country", "country_code", "country_name", "entered", "left", "loading", "unloading", "meals", "km", "note"]


class TripDiemSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(source="country.code", read_only=True, default="")
    employee_name = serializers.CharField(source="employment.employee.full_name", read_only=True)

    class Meta:
        model = TripDiem
        fields = ["id", "employment", "employee_name", "day", "country", "country_code", "hours", "pct", "norm", "currency",
                  "fx_rate", "amount", "taxable", "how"]


class TripSerializer(serializers.ModelSerializer):
    """Cursa cu segmentele ei (se trimit cu cursa și o înlocuiesc întreg); la salvare se socotește din nou."""

    deletion_mark = serializers.BooleanField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    scope_label = serializers.CharField(source="get_scope_display", read_only=True)
    driver_label = serializers.SerializerMethodField()
    co_driver_label = serializers.SerializerMethodField()
    vehicle_plate = serializers.CharField(source="vehicle.plate", read_only=True)
    trailer_plate = serializers.CharField(source="trailer.plate", read_only=True, default="")
    legs = TripLegSerializer(many=True, required=False)
    diems = TripDiemSerializer(many=True, read_only=True)
    totals = serializers.SerializerMethodField()
    problems = serializers.SerializerMethodField()
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = ["id", "deletion_mark", "number", "driver", "driver_label", "co_driver", "co_driver_label", "vehicle", "vehicle_plate",
                  "trailer", "trailer_plate", "kind", "kind_label", "scope", "scope_label", "departure", "arrival", "route",
                  "odometer_out", "odometer_in", "km", "adr", "meals_provided", "per_diem_pct", "status", "status_label", "note",
                  "km_rate", "km_amount", "how", "created_at", "approved_at", "legs", "diems", "totals", "problems", "warnings"]
        read_only_fields = ["number", "status", "km_rate", "km_amount", "how", "created_at", "approved_at"]

    def get_driver_label(self, obj):
        return job_label(obj.driver)

    def get_co_driver_label(self, obj):
        return job_label(obj.co_driver)

    def get_totals(self, obj):
        return services.totals(obj)

    def get_problems(self, obj):
        return getattr(obj, "_problems", None) if getattr(obj, "_problems", None) is not None else (
            services.problems(obj) if obj.status == "draft" and self.context.get("detail") else [])

    def get_warnings(self, obj):
        return services.driver_docs(obj) if self.context.get("detail") else []

    def validate(self, attrs):
        dep = attrs.get("departure", getattr(self.instance, "departure", None))
        arr = attrs.get("arrival", getattr(self.instance, "arrival", None))
        if dep and arr and arr <= dep:
            raise serializers.ValidationError({"arrival": "Întoarcerea este înaintea plecării."})
        pct = attrs.get("per_diem_pct")
        if pct is not None and not (0 <= pct <= 300):
            raise serializers.ValidationError({"per_diem_pct": "Procentul diurnei este între 0 și 300."})
        for name in ("driver", "co_driver"):
            job = attrs.get(name)
            if job is not None and job.kind == "contractor":
                raise serializers.ValidationError({name: "Cursa se face pe un raport de muncă, nu pe contractul de prestări servicii."})
        for n, leg in enumerate(attrs.get("legs") or [], start=1):
            if leg["left"] <= leg["entered"]:
                raise serializers.ValidationError({"legs": f"Segmentul {n}: ieșirea e înaintea intrării."})
            if leg.get("km") is not None and leg["km"] < 0:
                raise serializers.ValidationError({"legs": f"Segmentul {n}: km nu pot fi negativi."})
        return attrs

    def _save_legs(self, trip, rows):
        if rows is None:
            return
        keep = []
        for n, row in enumerate(rows, start=1):
            pk = row.pop("id", None)
            leg = trip.legs.filter(pk=pk).first() if pk else None
            if leg is None:
                leg = TripLeg(trip=trip)
            for k, v in row.items():
                setattr(leg, k, v)
            leg.sort = n * 10
            leg.save()
            keep.append(leg.pk)
        trip.legs.exclude(pk__in=keep).delete()

    def create(self, validated):
        legs = validated.pop("legs", [])
        trip = Trip.objects.create(**validated)
        self._save_legs(trip, legs)
        trip._problems = services.compute(trip)
        return trip

    def update(self, instance, validated):
        legs = validated.pop("legs", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        instance.save()
        self._save_legs(instance, legs)
        instance._problems = services.compute(instance)
        return instance


class JobChoiceSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = Employment
        fields = ["id", "label"]

    def get_label(self, obj):
        return job_label(obj)
