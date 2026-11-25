from datetime import date

from rest_framework import serializers

from apps.staff.models import Employment

from . import services
from .models import (Country, DriverIncident, GpsDay, KmRate, KpiAssignment, KpiIndicator, KpiLine, KpiScheme, KpiSchemeItem,
                     KpiSheet, PerDiemNorm, TachoFile, Trip, TripDiem, TripLeg, Vehicle)


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
                  "gps_id", "subdivision", "subdivision_name", "note", "is_active"]

    def validate_plate(self, value):
        value = " ".join(value.upper().split())
        if not value:
            raise serializers.ValidationError("Scrieți numărul de înmatriculare.")
        return value

    def validate_gps_id(self, value):
        value = (value or "").strip()
        clash = Vehicle.objects.filter(gps_id=value) if value else Vehicle.objects.none()
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(f"Identificatorul din GPS e deja al vehiculului {clash.first().plate}.")
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
                  "odometer_out", "odometer_in", "km", "adr", "meals_provided", "per_diem_pct", "fuel_out", "fuel_added", "fuel_in",
                  "fuel_used", "fuel_adj_pct", "fuel_source", "fuel_norm_l", "docs_submitted", "status", "status_label", "note",
                  "km_rate", "km_amount", "how", "created_at", "approved_at", "legs", "diems", "totals", "problems", "warnings"]
        read_only_fields = ["number", "status", "km_rate", "km_amount", "how", "created_at", "approved_at", "fuel_source",
                            "fuel_norm_l"]

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
        if not self.context.get("detail"):
            return []
        from . import gps, tacho

        return services.driver_docs(obj) + tacho.trip_warnings(obj) + gps.trip_warnings(obj)

    def validate(self, attrs):
        dep = attrs.get("departure", getattr(self.instance, "departure", None))
        arr = attrs.get("arrival", getattr(self.instance, "arrival", None))
        if dep and arr and arr <= dep:
            raise serializers.ValidationError({"arrival": "Întoarcerea este înaintea plecării."})
        for name in ("fuel_out", "fuel_added", "fuel_in", "fuel_used"):
            if attrs.get(name) is not None and attrs[name] < 0:
                raise serializers.ValidationError({name: "Litrii nu pot fi negativi."})
        adj = attrs.get("fuel_adj_pct")
        if adj is not None and not (-50 <= adj <= 100):
            raise serializers.ValidationError({"fuel_adj_pct": "Corecția normei e între −50 % și 100 %."})
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
        if validated.get("fuel_used") is not None:
            validated["fuel_source"] = "manual"
        trip = Trip.objects.create(**validated)
        self._save_legs(trip, legs)
        trip._problems = services.compute(trip)
        return trip

    def update(self, instance, validated):
        legs = validated.pop("legs", None)
        if "fuel_used" in validated and validated["fuel_used"] != instance.fuel_used:
            # consumul schimbat de mână rămâne (dacă foaia n-are rămășițele rezervorului); golit — se ia iar din GPS
            instance.fuel_source = "manual" if validated["fuel_used"] is not None else ""
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


class TachoFileSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    holder = serializers.CharField(read_only=True)

    class Meta:
        model = TachoFile
        fields = ["id", "name", "size", "generation", "version", "card_number", "card_nation", "authority", "card_issue",
                  "card_expiry", "holder", "holder_surname", "holder_first_names", "birth_date", "licence_number", "downloaded_at",
                  "first_day", "last_day", "days", "employee", "employee_name", "matched_by", "uploaded_at"]
        read_only_fields = fields

    def get_employee_name(self, obj):
        return obj.employee.full_name() if obj.employee_id else ""


# --- GPS, evenimentele, KPI (pasul c) ------------------------------------------------------------------------------------
class GpsDaySerializer(serializers.ModelSerializer):
    plate = serializers.CharField(source="vehicle.plate", read_only=True)

    class Meta:
        model = GpsDay
        fields = ["id", "vehicle", "plate", "day", "km", "moving_min", "engine_min", "first_start", "last_stop", "fuel_l",
                  "odometer_start", "odometer_end", "countries", "source", "imported_at"]
        read_only_fields = fields


class DriverIncidentSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    trip_label = serializers.SerializerMethodField()

    class Meta:
        model = DriverIncident
        fields = ["id", "employee", "employee_name", "trip", "trip_label", "date", "kind", "kind_label", "at_fault", "amount",
                  "document", "note", "created_at"]
        read_only_fields = ["created_at"]

    def get_trip_label(self, obj):
        return obj.trip.reference() if obj.trip_id else ""

    def validate_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Suma nu poate fi negativă.")
        return value

    def validate(self, attrs):
        trip = attrs.get("trip", getattr(self.instance, "trip", None))
        emp = attrs.get("employee", getattr(self.instance, "employee", None))
        if trip is not None and emp is not None and emp.pk not in (trip.driver.employee_id,
                                                                   trip.co_driver.employee_id if trip.co_driver_id else None):
            raise serializers.ValidationError({"trip": "Angajatul nu e șofer în această cursă."})
        return attrs


class KpiIndicatorSerializer(serializers.ModelSerializer):
    source_label = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = KpiIndicator
        fields = ["id", "code", "name_ro", "name_ru", "name_en", "source", "source_label", "kinds", "measure", "mode", "full_at",
                  "zero_at", "unit", "description", "sort", "is_active"]

    def validate_code(self, value):
        value = (value or "").strip().upper()
        if not value or not all(c.isalnum() or c == "_" for c in value):
            raise serializers.ValidationError("Codul — litere latine, cifre și „_”.")
        return value

    def validate_kinds(self, value):
        known = {k for k, _ in DriverIncident.KINDS}
        if not isinstance(value, list) or any(k not in known for k in value):
            raise serializers.ValidationError("Felurile evenimentelor: " + ", ".join(sorted(known)) + ".")
        return value

    def validate(self, attrs):
        source = attrs.get("source", getattr(self.instance, "source", None))
        if self.instance is not None and "source" in attrs and attrs["source"] != self.instance.source:
            if KpiLine.objects.filter(sheet__status="approved", scheme__items__indicator=self.instance).exists():
                raise serializers.ValidationError({"source": "Indicatorul e în fișe KPI aprobate: faceți unul nou în loc să-i "
                                                             "schimbați ce măsoară."})
        if source != "incidents":
            attrs["kinds"] = []
        return attrs


class KpiSchemeItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    indicator_code = serializers.CharField(source="indicator.code", read_only=True)
    indicator_name = serializers.CharField(source="indicator.name_ro", read_only=True)

    class Meta:
        model = KpiSchemeItem
        fields = ["id", "indicator", "indicator_code", "indicator_name", "weight", "mode", "full_at", "zero_at"]


class KpiAssignmentSerializer(serializers.ModelSerializer):
    occupation_name = serializers.CharField(source="occupation.name_ro", read_only=True, default="")
    employment_label = serializers.SerializerMethodField()
    scheme_code = serializers.CharField(source="scheme.code", read_only=True)

    class Meta:
        model = KpiAssignment
        fields = ["id", "scheme", "scheme_code", "occupation", "occupation_name", "employment", "employment_label", "date_from",
                  "date_to"]

    def get_employment_label(self, obj):
        return job_label(obj.employment)

    def validate(self, attrs):
        occ = attrs.get("occupation", getattr(self.instance, "occupation", None))
        job = attrs.get("employment", getattr(self.instance, "employment", None))
        if bool(occ) == bool(job):
            raise serializers.ValidationError({"occupation": "Alegeți funcția sau raportul de muncă (unul din ele)."})
        a = attrs.get("date_from", getattr(self.instance, "date_from", None))
        b = attrs.get("date_to", getattr(self.instance, "date_to", None))
        if a and b and b < a:
            raise serializers.ValidationError({"date_to": "„Până la” e înaintea lui „De la”."})
        clash = KpiAssignment.objects.filter(occupation=occ, employment=job, date_from__lte=b or date.max).exclude(date_to__lt=a)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({"date_from": "Pentru aceeași funcție / raport există deja o schemă în această "
                                                            "perioadă: închideți-o cu „Până la”."})
        return attrs


class KpiSchemeSerializer(serializers.ModelSerializer):
    items = KpiSchemeItemSerializer(many=True, required=False)
    assignments = KpiAssignmentSerializer(many=True, read_only=True)
    base_kind_label = serializers.CharField(source="get_base_kind_display", read_only=True)

    class Meta:
        model = KpiScheme
        fields = ["id", "code", "name", "base_kind", "base_kind_label", "base_amount", "base_pct", "min_score", "prorate",
                  "needs_trips", "document", "is_active", "items", "assignments"]

    def validate_code(self, value):
        value = (value or "").strip().upper()
        if not value or not all(c.isalnum() or c == "_" for c in value):
            raise serializers.ValidationError("Codul — litere latine, cifre și „_”.")
        return value

    def validate(self, attrs):
        for name in ("base_amount", "base_pct"):
            if attrs.get(name) is not None and attrs[name] < 0:
                raise serializers.ValidationError({name: "Baza nu poate fi negativă."})
        ms = attrs.get("min_score")
        if ms is not None and not (0 <= ms <= 100):
            raise serializers.ValidationError({"min_score": "Pragul e între 0 și 100 %."})
        items = attrs.get("items")
        if items is not None:
            seen = set()
            for row in items:
                if row["indicator"].pk in seen:
                    raise serializers.ValidationError({"items": f"Indicatorul {row['indicator'].code} e de două ori în schemă."})
                seen.add(row["indicator"].pk)
                if row["weight"] is None or row["weight"] <= 0:
                    raise serializers.ValidationError({"items": f"{row['indicator'].code}: ponderea e mai mare decât 0."})
        return attrs

    def _save_items(self, scheme, rows):
        if rows is None:
            return
        keep = []
        for n, row in enumerate(rows, start=1):
            row.pop("id", None)
            item, _ = KpiSchemeItem.objects.update_or_create(scheme=scheme, indicator=row.pop("indicator"),
                                                             defaults={**row, "sort": n * 10})
            keep.append(item.pk)
        scheme.items.exclude(pk__in=keep).delete()

    def create(self, validated):
        items = validated.pop("items", [])
        scheme = KpiScheme.objects.create(**validated)
        self._save_items(scheme, items)
        return scheme

    def update(self, instance, validated):
        items = validated.pop("items", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        instance.save()
        self._save_items(instance, items)
        return instance


class KpiLineSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    tab_number = serializers.CharField(source="employee.tab_number", read_only=True)
    occupation = serializers.CharField(source="employment.occupation.name_ro", read_only=True)
    scheme_code = serializers.CharField(source="scheme.code", read_only=True)

    class Meta:
        model = KpiLine
        fields = ["id", "employee", "employee_name", "tab_number", "employment", "occupation", "scheme", "scheme_code", "base",
                  "score", "amount", "prorate", "details", "overrides", "note"]
        read_only_fields = fields


class KpiSheetSerializer(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    subdivision_name = serializers.CharField(source="subdivision.name_ro", read_only=True, default="")
    lines = serializers.SerializerMethodField()
    totals = serializers.SerializerMethodField()

    class Meta:
        model = KpiSheet
        fields = ["id", "deletion_mark", "number", "date", "year", "month", "subdivision", "subdivision_name", "status",
                  "status_label", "note", "created_at", "approved_at", "lines", "totals"]
        read_only_fields = ["number", "status", "created_at", "approved_at"]

    def get_lines(self, obj):
        if not self.context.get("detail"):
            return []
        qs = obj.lines.select_related("employee", "employment__occupation", "scheme")
        visible = self.context.get("visible_jobs")
        if visible is not None:
            qs = qs.filter(employment_id__in=visible)
        return KpiLineSerializer(qs, many=True).data

    def get_totals(self, obj):
        from . import kpi

        return kpi.totals(obj)

    def validate_month(self, value):
        if not 1 <= value <= 12:
            raise serializers.ValidationError("Luna e între 1 și 12.")
        return value
