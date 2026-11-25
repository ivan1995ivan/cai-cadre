"""Socoteala cursei: tariful pe km, km parcurși, documentele șoferului la data cursei, problemele (ce oprește aprobarea),
diurna pe zile (apps.transport.per_diem) și ce intră în calculul salariului lunii."""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import KmRate, Trip, TripDiem

ZERO, CENT = Decimal("0"), Decimal("0.01")


def q(value) -> Decimal:
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(value, places=None) -> str:
    d = Decimal(value or 0)
    if places is not None:
        d = d.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    text = format(d.normalize(), "f") if d != d.to_integral_value() else format(d.to_integral_value(), "f")
    return text.replace(".", ",")


def local_day(dt) -> date:
    return timezone.localtime(dt).date()


# --- tariful pe km ------------------------------------------------------------------------------------------------------
def km_rate(trip: Trip):
    """Rândul tarifului pe km în vigoare la plecare, cel mai potrivit cursei: felul cursei, aria, felul vehiculului — fiecare
    potrivire exactă cântărește mai mult decât „oricare”; la egalitate — cel mai nou. None — fără tarif."""
    day = local_day(trip.departure)
    best, best_key = None, None
    for r in KmRate.objects.filter(date_from__lte=day):
        checks = ((r.trip_kind, trip.kind), (r.scope, trip.scope), (r.vehicle_kind, trip.vehicle.kind if trip.vehicle_id else ""))
        if any(want and want != have for want, have in checks):
            continue
        key = (sum(1 for want, _ in checks if want), r.date_from, r.pk)
        if best_key is None or key > best_key:
            best, best_key = r, key
    return best


def trip_km(trip: Trip) -> Decimal:
    """Km parcurși: din kilometraj (întoarcere − plecare), dacă ambele sunt scrise; altfel cei scriși de mână."""
    if trip.odometer_out is not None and trip.odometer_in is not None:
        return Decimal(trip.odometer_in - trip.odometer_out)
    return Decimal(trip.km or 0)


# --- documentele șoferului --------------------------------------------------------------------------------------------------
def driver_docs(trip: Trip) -> list:
    """Avertismentele despre actele șoferilor la data cursei (permisul, CPC, cardul tahografului, certificatul medical, ADR):
    lipsă sau expirate la întoarcere. Nu opresc aprobarea — le vede dispecerul / contabilul."""
    from apps.staff.models import EmployeeDocument

    need = ["driving_licence", "cpc", "medical_cert"]
    if trip.vehicle_id and trip.vehicle.tachograph:
        need.append("tachograph_card")
    if trip.adr:
        need.append("adr")
    names = {"driving_licence": "permisul de conducere", "cpc": "certificatul de competență profesională (CPC)",
             "medical_cert": "certificatul medical", "tachograph_card": "cardul de conducător pentru tahograf",
             "adr": "certificatul ADR"}
    end = local_day(trip.arrival)
    out = []
    for job in (trip.driver, trip.co_driver):
        if job is None:
            continue
        docs = defaultdict(list)
        for d in EmployeeDocument.objects.filter(employee=job.employee, doc_type__code__in=need).select_related("doc_type"):
            docs[d.doc_type.code].append(d)
        who = job.employee.full_name()
        for code in need:
            have = docs.get(code)
            if not have:
                out.append(f"{who}: lipsește {names[code]} în dosar")
            elif all(d.expiry_date and d.expiry_date < end for d in have):
                last = max(d.expiry_date for d in have)
                out.append(f"{who}: {names[code]} a expirat la {last:%d.%m.%Y}")
    return out


# --- verificarea și socoteala --------------------------------------------------------------------------------------------
def problems(trip: Trip) -> list:
    """Ce oprește aprobarea cursei."""
    from apps.leave.models import Absence

    out = []
    if trip.arrival <= trip.departure:
        out.append("Întoarcerea este înaintea plecării.")
    if trip.odometer_out is not None and trip.odometer_in is not None and trip.odometer_in < trip.odometer_out:
        out.append("Kilometrajul la întoarcere e mai mic decât la plecare.")
    if trip_km(trip) <= 0:
        out.append("Cursa n-are km (kilometrajul sau km de mână).")
    if trip.co_driver_id and trip.co_driver_id == trip.driver_id:
        out.append("Al doilea șofer e același cu primul.")
    if trip.trailer_id and trip.trailer.kind != "trailer":
        out.append(f"{trip.trailer.plate} nu e remorcă / semiremorcă.")
    if trip.vehicle_id and trip.vehicle.kind == "trailer":
        out.append(f"{trip.vehicle.plate} e remorcă: alegeți vehiculul tractor la „Vehiculul”.")
    start, end = local_day(trip.departure), local_day(trip.arrival)
    for job in (trip.driver, trip.co_driver):
        if job is None:
            continue
        if not (job.is_active_on(start) and job.is_active_on(end)):
            out.append(f"Raportul de muncă al lui {job.employee.full_name()} nu e activ pe toată cursa.")
        busy = (Absence.objects.filter(employee=job.employee, date_from__lte=end, date_to__gte=start)
                .exclude(kind__in=("travel", "training")).first())
        if busy is not None:
            out.append(f"{job.employee.full_name()} are {busy.get_kind_display().lower()} {busy.date_from:%d.%m.%Y}–"
                       f"{busy.date_to:%d.%m.%Y} în timpul cursei.")
        clash = (Trip.objects.filter(Q(driver=job) | Q(co_driver=job), departure__lt=trip.arrival, arrival__gt=trip.departure,
                                     deletion_mark=False).exclude(pk=trip.pk).first())
        if clash is not None:
            out.append(f"{job.employee.full_name()} are și cursa {clash.reference()} în aceeași perioadă.")
    legs = list(trip.legs.select_related("country").order_by("entered", "id"))
    if trip.scope == "international" and not legs:
        out.append("Cursa internațională n-are țările (segmentele cu intrarea și ieșirea).")
    for n, leg in enumerate(legs, start=1):
        label = f"Segmentul {n} ({leg.country.code})"
        if leg.left <= leg.entered:
            out.append(f"{label}: ieșirea e înaintea intrării.")
        if leg.entered < trip.departure or leg.left > trip.arrival:
            out.append(f"{label}: e în afara cursei (plecarea – întoarcerea).")
        if n > 1 and leg.entered < legs[n - 2].left:
            out.append(f"{label}: se suprapune cu segmentul de dinainte.")
        if leg.country.code == "MD":
            out.append(f"{label}: Republica Moldova nu e segment în străinătate — timpul din țară e în afara segmentelor.")
    if trip.scope == "domestic" and legs:
        out.append("Cursa în țară nu are segmente în străinătate: alegeți aria „Internațional”.")
    used = tank_fuel(trip)
    if used is not None and used < 0:
        out.append("Combustibilul: rămășița la întoarcere e mai mare decât rămășița la plecare plus alimentarea.")
    if trip.fuel_used is not None and trip.fuel_used < 0:
        out.append("Combustibilul consumat nu poate fi negativ.")
    if trip.docs_submitted is not None and trip.docs_submitted < local_day(trip.departure):
        out.append("Actele cursei sunt predate înaintea plecării.")
    return out


# --- combustibilul -------------------------------------------------------------------------------------------------------
def tank_fuel(trip: Trip):
    """Consumul din rezervor: rămășița la plecare + alimentat − rămășița la întoarcere (None — lipsește o rămășiță)."""
    if trip.fuel_out is None or trip.fuel_in is None:
        return None
    return trip.fuel_out + (trip.fuel_added or ZERO) - trip.fuel_in


def fuel(trip: Trip) -> None:
    """Consumul cursei și consumul normat: din rezervor (rămășițele foii) → scris de mână → din GPS (fiecare zi a cursei cu
    combustibil); normat = norma vehiculului × km / 100 × (1 + corecția %). Nu salvează."""
    from . import gps

    used = tank_fuel(trip)
    if used is not None:
        trip.fuel_used, trip.fuel_source = q(used), "tank"
    elif trip.fuel_used is not None and trip.fuel_source in ("", "manual"):
        trip.fuel_source = "manual"
    else:
        g = gps.trip_fuel(trip)
        trip.fuel_used, trip.fuel_source = (q(g), "gps") if g is not None else (None, "")
    norm = trip.vehicle.fuel_norm if trip.vehicle_id else None
    if norm and trip.km:
        trip.fuel_norm_l = q(norm * trip.km / 100 * (1 + (trip.fuel_adj_pct or ZERO) / 100))
    else:
        trip.fuel_norm_l = None


def docs_due(trip: Trip) -> date:
    """Termenul predării actelor cursei: ziua întoarcerii + C.kpi_docs_days zile."""
    from datetime import timedelta

    from apps.payroll.engine import Constants

    end = local_day(trip.arrival)
    return end + timedelta(days=int(Constants(end)("kpi_docs_days", "3")))


def compute(trip: Trip, strict: bool = False) -> list:
    """Km, tariful și plata pe km, diurna pe zile (rândurile TripDiem refăcute); salvează. `strict` (la aprobare) — orice
    problemă oprește. Întoarce problemele."""
    from . import per_diem

    found = problems(trip)
    trip.km = trip_km(trip)
    rate = km_rate(trip)
    if rate is None:
        found.append("Nu există tarif pe km pentru această cursă (Setări → Tarife pe km).")
        trip.km_rate, trip.km_amount = None, ZERO
        trip.how = "fără tarif pe km"
    else:
        trip.km_rate = rate.rate
        trip.km_amount = q(trip.km * rate.rate)
        trip.how = (f"{fmt(trip.km)} km × {fmt(rate.rate)} lei/km = {fmt(trip.km_amount, 2)} lei"
                    + (f" ({rate.document})" if rate.document else ""))[:300]
    fuel(trip)
    trip.save(update_fields=["km", "km_rate", "km_amount", "how", "fuel_used", "fuel_source", "fuel_norm_l"])
    TripDiem.objects.filter(trip=trip).delete()
    try:
        rows = per_diem.calculate(trip)
    except ValidationError as exc:
        text = exc.detail.get("detail") if isinstance(exc.detail, dict) else exc.detail
        found.append(str(text))
        rows = []
    if not found or not strict:
        for n, row in enumerate(rows, start=1):
            TripDiem.objects.create(trip=trip, sort=n, **row)
    if strict and found:
        raise ValidationError({"detail": " ".join(found)})
    return found


def totals(trip: Trip) -> dict:
    diems = list(trip.diems.all())
    people = defaultdict(lambda: {"amount": ZERO, "taxable": ZERO})
    for d in diems:
        people[d.employment_id]["amount"] += d.amount
        people[d.employment_id]["taxable"] += d.taxable
    return {"km": float(trip.km or 0), "km_amount": float(trip.km_amount or 0),
            "fuel_used": float(trip.fuel_used) if trip.fuel_used is not None else None,
            "fuel_norm": float(trip.fuel_norm_l) if trip.fuel_norm_l is not None else None,
            "fuel_pct": round(float(trip.fuel_used / trip.fuel_norm_l * 100), 1) if trip.fuel_used is not None and trip.fuel_norm_l
            else None, "fuel_source": trip.fuel_source, "docs_due": docs_due(trip),
            "per_diem": float(sum((d.amount for d in diems), ZERO)), "per_diem_taxable": float(sum((d.taxable for d in diems), ZERO)),
            "people": {str(k): {"amount": float(v["amount"]), "taxable": float(v["taxable"])} for k, v in people.items()}}


# --- în calculul salariului ----------------------------------------------------------------------------------------------
@dataclass
class JobMonth:
    km: Decimal = ZERO
    km_amount: Decimal = ZERO
    per_diem: Decimal = ZERO
    per_diem_taxable: Decimal = ZERO
    days: int = 0
    refs: list = field(default_factory=list)

    def km_note(self) -> str:
        parts = [f"{ref}: {fmt(km)} km × {fmt(rate)}" for ref, km, rate, _d in self.refs[:6]]
        more = len(self.refs) - 6
        return "cursele " + "; ".join(parts) + (f" și încă {more}" if more > 0 else "")


def month_summary(first: date, last: date) -> dict:
    """{employment_id: JobMonth} — cursele aprobate (nemarcate) cu întoarcerea în lună: plata pe km a fiecărui șofer și diurna lui."""
    out = defaultdict(JobMonth)
    trips = [t for t in Trip.objects.filter(status="approved", deletion_mark=False).select_related("vehicle")
             if first <= local_day(t.arrival) <= last]
    ids = [t.pk for t in trips]
    for t in sorted(trips, key=lambda x: (x.arrival, x.pk)):
        for job_id in (t.driver_id, t.co_driver_id):
            if job_id is None:
                continue
            s = out[job_id]
            s.km += t.km
            s.km_amount += t.km_amount
            s.refs.append((t.reference(), t.km, t.km_rate or ZERO, local_day(t.arrival)))
    for d in TripDiem.objects.filter(trip_id__in=ids):
        s = out[d.employment_id]
        s.per_diem += d.amount - d.taxable
        s.per_diem_taxable += d.taxable
        s.days += 1
    return dict(out)
