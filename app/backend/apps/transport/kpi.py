"""KPI-ul șoferilor (S6b pasul c): fișa KPI a lunii.

Schema KPI (Setări → Schemele KPI) se aplică unei funcții sau unui raport de muncă anume (acesta are întâietate), din data
dată. Pentru fiecare șofer cu schemă, activ în lună, fișa măsoară indicatorii schemei:

- `fuel` — litrii consumați / consumul normat × 100, din cursele aprobate cu întoarcerea în lună (unde există și consumul, și
  norma vehiculului); în cursa cu doi șoferi — ambilor;
- `incidents` — evenimentele lunii din vina șoferului (Salarizare → Evenimentele șoferilor), felurile indicatorului: numărul
  sau suma;
- `documents` — cursele aprobate ale lunii cu actele predate în termen (C.kpi_docs_days zile de la întoarcere) / cursele cu
  termenul trecut sau actele predate × 100 (cursele cu termenul încă neajuns nu se socotesc);
- `tacho` — încălcările limitelor AETR din lună (constatările de nivel „încălcare”), doar pentru cine are zile de pe card;
- `manual` — valoarea scrisă în fișă.

Nota indicatorului (0–100 %): liniar între valoarea cu nota 100 % și cea cu nota 0 % (în ambele sensuri: mai puțin e mai bine
sau mai mult e mai bine) sau prag (îndeplinit — 100 %, altfel 0). Indicatorul fără date (fără curse cu consum, fără card) nu
intră în punctaj — ponderile celorlalte se împart din nou. Punctajul = Σ pondere × nota / Σ ponderi. Prima = baza (sumă fixă
sau % din salariul de funcție pentru norma raportului) × punctajul; sub pragul schemei — 0; fără curse aprobate în lună — 0, dacă
schema cere curse (implicit: „0 daune, 0 amenzi” fără nicio cursă nu e o performanță). În salariu (tipul KPI) prima se
înmulțește cu partea lucrată din normă, dacă schema o cere.

Fiecare valoare se poate scrie de mână în fișă (rămâne la completarea din nou). Aprobată, fișa se fixează.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.staff.models import Employment

from .models import DriverIncident, KpiAssignment, KpiLine, KpiSheet, TachoDay, Trip
from .services import docs_due, fmt, local_day, q

ZERO, HUNDRED = Decimal("0"), Decimal("100")


def month_bounds(year: int, month: int):
    first = date(year, month, 1)
    return first, date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)


# --- schema ------------------------------------------------------------------------------------------------------------------
def scheme_for(job: Employment, day: date, assignments=None):
    """Schema KPI a raportului de muncă la data dată: cea pe raport, altfel cea pe funcție; la mai multe — cea mai nouă."""
    rows = assignments if assignments is not None else KpiAssignment.objects.filter(
        Q(employment=job) | Q(occupation_id=job.occupation_id)).select_related("scheme")
    live = [a for a in rows if a.date_from <= day and (a.date_to is None or a.date_to >= day) and a.scheme.is_active
            and (a.employment_id == job.pk or (a.employment_id is None and a.occupation_id == job.occupation_id))]
    if not live:
        return None
    return max(live, key=lambda a: (a.employment_id is not None, a.date_from, a.pk)).scheme


def item_params(item) -> tuple:
    ind = item.indicator
    return (item.mode or ind.mode, item.full_at if item.full_at is not None else ind.full_at,
            item.zero_at if item.zero_at is not None else ind.zero_at)


def grade(value: Decimal, mode: str, full: Decimal, zero: Decimal) -> Decimal:
    """Nota 0–100 % a valorii. „Mai puțin e mai bine” când valoarea cu nota 100 % e cel mult cea cu nota 0 %."""
    lower_better = full <= zero
    if mode == "step" or full == zero:
        ok = value <= full if lower_better else value >= full
        return HUNDRED if ok else ZERO
    if lower_better:
        if value <= full:
            return HUNDRED
        if value >= zero:
            return ZERO
        share = (zero - value) / (zero - full)
    else:
        if value >= full:
            return HUNDRED
        if value <= zero:
            return ZERO
        share = (value - zero) / (full - zero)
    return (share * HUNDRED).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --- măsurarea -----------------------------------------------------------------------------------------------------------------
def _trips(job: Employment, first: date, last: date) -> list:
    return [t for t in Trip.objects.filter(Q(driver=job) | Q(co_driver=job), status="approved", deletion_mark=False)
            .select_related("vehicle").order_by("arrival", "id") if first <= local_day(t.arrival) <= last]


def measure(source: str, ind, job: Employment, first: date, last: date, today: date, cache: dict):
    """(valoarea sau None — fără date, explicația)."""
    if source in ("fuel", "documents") and "trips" not in cache:
        cache["trips"] = _trips(job, first, last)
    if source == "fuel":
        rows = [t for t in cache["trips"] if t.fuel_used is not None and t.fuel_norm_l]
        if not rows:
            return None, "fără curse aprobate cu consumul și norma vehiculului"
        used = sum((t.fuel_used for t in rows), ZERO)
        norm = sum((t.fuel_norm_l for t in rows), ZERO)
        value = (used / norm * HUNDRED).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return value, f"{len(rows)} curse: {fmt(used, 2)} l consumați / {fmt(norm, 2)} l normați"
    if source == "documents":
        on_time = late = pending = 0
        for t in cache["trips"]:
            due = docs_due(t)
            if t.docs_submitted is not None:
                on_time, late = (on_time + 1, late) if t.docs_submitted <= due else (on_time, late + 1)
            elif due < today:
                late += 1
            else:
                pending += 1
        if not on_time + late:
            return None, ("fără curse cu termenul actelor trecut" + (f" ({pending} în termen)" if pending else "")
                          if cache["trips"] else "fără curse aprobate în lună")
        value = (Decimal(on_time) / (on_time + late) * HUNDRED).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return value, f"{on_time} din {on_time + late} curse cu actele la timp" + (f", {pending} în termen" if pending else "")
    if source == "incidents":
        qs = DriverIncident.objects.filter(employee_id=job.employee_id, date__gte=first, date__lte=last, at_fault=True)
        if ind.kinds:
            qs = qs.filter(kind__in=ind.kinds)
        rows = list(qs)
        if ind.measure == "amount":
            total = sum((r.amount for r in rows), ZERO)
            return total, f"{len(rows)} evenimente, {fmt(total, 2)} lei"
        return Decimal(len(rows)), (f"{len(rows)} evenimente" if rows else "niciun eveniment")
    if source == "tacho":
        if not TachoDay.objects.filter(employee_id=job.employee_id, day__gte=first - timedelta(days=1),
                                       day__lte=last + timedelta(days=1)).exists():
            return None, "fără zile de pe cardul de tahograf în lună"
        from . import tacho

        lo = timezone.make_aware(datetime.combine(first, time.min))
        hi = timezone.make_aware(datetime.combine(last + timedelta(days=1), time.min))
        found = [f for f in tacho.findings(job.employee, lo, hi) if f.level == "error"]
        return Decimal(len(found)), (f"{len(found)} încălcări" if found else "nicio încălcare")
    return None, "se scrie de mână"


def compute_line(line: KpiLine, sheet: KpiSheet, today: date | None = None) -> None:
    """Indicatorii, punctajul și prima rândului (nu salvează)."""
    first, last = month_bounds(sheet.year, sheet.month)
    today = today or timezone.localdate()
    scheme, job = line.scheme, line.employment
    cache, details = {}, []
    num = den = ZERO
    overrides = line.overrides or {}
    for item in scheme.items.select_related("indicator").order_by("sort", "id"):
        ind = item.indicator
        mode, full, zero = item_params(item)
        value, how = measure(ind.source, ind, job, first, last, today, cache)
        manual = ind.code in overrides and overrides[ind.code] not in (None, "")
        if manual:
            value, how = Decimal(str(overrides[ind.code])), "scris de mână" + (f" (din date: {how})" if ind.source != "manual" else "")
        score = grade(value, mode, full, zero) if value is not None else None
        if score is not None:
            num += item.weight * score
            den += item.weight
        details.append({"code": ind.code, "name": ind.name_ro, "source": ind.source, "unit": ind.unit, "weight": float(item.weight),
                        "mode": mode, "full_at": float(full), "zero_at": float(zero),
                        "value": float(value) if value is not None else None, "score": float(score) if score is not None else None,
                        "manual": manual, "how": how})
    line.details = details
    if scheme.base_kind == "pct":
        salary = q(job.base_salary * job.rate)
        line.base = q(salary * scheme.base_pct / HUNDRED)
        base_how = f"{fmt(scheme.base_pct, 2)} % din salariul de funcție {fmt(salary, 2)} lei"
    else:
        line.base = q(scheme.base_amount)
        base_how = f"suma fixă {fmt(line.base, 2)} lei"
    line.prorate = scheme.prorate
    if scheme.needs_trips and not (cache["trips"] if "trips" in cache else _trips(job, first, last)):
        # „0 daune, 0 amenzi” fără nicio cursă nu e o performanță: prima nu se socotește
        line.score, line.amount = None, ZERO
        line.note = "Fără curse aprobate cu întoarcerea în lună: prima nu se socotește (schema cere curse)."
        return
    if not den:
        line.score, line.amount = None, ZERO
        line.note = "Niciun indicator nu are date în lună: prima nu se socotește."
        return
    line.score = (num / den).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if line.score < scheme.min_score:
        line.amount = ZERO
        line.note = f"Punctajul {fmt(line.score, 2)} % e sub pragul schemei {fmt(scheme.min_score, 2)} %: prima nu se plătește."
    else:
        line.amount = q(line.base * line.score / HUNDRED)
        line.note = (f"{base_how} × punctajul {fmt(line.score, 2)} % = {fmt(line.amount, 2)} lei"
                     + ("; în salariu — proporțional cu timpul lucrat" if scheme.prorate else ""))[:400]


# --- fișa ----------------------------------------------------------------------------------------------------------------------
def _jobs(sheet: KpiSheet) -> list:
    """(raportul de muncă, schema) — activi în lună, fără prestări servicii, cu schemă la sfârșitul lunii (sau la ultima zi a
    raportului); cu subdiviziunea — doar cei din ea."""
    first, last = month_bounds(sheet.year, sheet.month)
    qs = (Employment.objects.filter(date_from__lte=last).exclude(end_date__lt=first).exclude(kind="contractor")
          .select_related("employee", "occupation", "subdivision"))
    if sheet.subdivision_id:
        qs = qs.filter(subdivision_id__in=sheet.subdivision.descendant_ids())
    assignments = list(KpiAssignment.objects.select_related("scheme"))
    by_job = defaultdict(list)
    for a in assignments:
        by_job[("e", a.employment_id) if a.employment_id else ("o", a.occupation_id)].append(a)
    out = []
    for job in qs:
        rows = by_job.get(("e", job.pk), []) + by_job.get(("o", job.occupation_id), [])
        if not rows:
            continue
        day = min(last, job.end_date) if job.end_date else last
        scheme = scheme_for(job, day, rows)
        if scheme is not None:
            out.append((job, scheme))
    return sorted(out, key=lambda x: (x[0].employee.last_name, x[0].employee.first_name, x[0].pk))


def editable(sheet: KpiSheet):
    from apps.core.deletion import ensure_not_marked

    ensure_not_marked(sheet)
    if sheet.status != "draft":
        raise ValidationError({"detail": "Fișa KPI este aprobată; anulați întâi aprobarea."})


@transaction.atomic
def fill(sheet: KpiSheet, jobs_visible=None) -> int:
    """Completează fișa: rândurile lipsă se adaugă, toate se socotesc din nou (valorile scrise de mână rămân); rândurile celor
    fără schemă în lună se scot. `jobs_visible` — doar raporturile acestea (subdiviziunile utilizatorului). Întoarce câte
    rânduri are."""
    editable(sheet)
    existing = {ln.employment_id: ln for ln in KpiLine.objects.filter(sheet=sheet)}
    keep = set()
    for n, (job, scheme) in enumerate(_jobs(sheet), start=1):
        if jobs_visible is not None and job.pk not in jobs_visible:
            if job.pk in existing:
                keep.add(job.pk)
            continue
        ln = existing.get(job.pk) or KpiLine(sheet=sheet, employee=job.employee, employment=job)
        ln.scheme = scheme
        ln.sort = n * 10
        compute_line(ln, sheet)
        ln.save()
        keep.add(job.pk)
    KpiLine.objects.filter(sheet=sheet).exclude(employment_id__in=keep).delete()
    return len(keep)


def set_overrides(line: KpiLine, values: dict) -> KpiLine:
    """Valorile scrise de mână ale rândului ({cod: valoare | None}); None / gol — înapoi la valoarea din date."""
    editable(line.sheet)
    codes = {i.indicator.code for i in line.scheme.items.select_related("indicator")}
    out = dict(line.overrides or {})
    for code, value in (values or {}).items():
        if code not in codes:
            raise ValidationError({"overrides": f"Indicatorul {code} nu e în schema {line.scheme.code}."})
        if value in (None, ""):
            out.pop(code, None)
            continue
        try:
            v = Decimal(str(value).replace(",", "."))
        except Exception:  # noqa: BLE001
            raise ValidationError({"overrides": f"{code}: „{value}” nu e un număr."}) from None
        if v < 0:
            raise ValidationError({"overrides": f"{code}: valoarea nu poate fi negativă."})
        out[code] = str(v)
    line.overrides = out
    compute_line(line, line.sheet)
    line.save()
    return line


def payroll_closed(sheet: KpiSheet):
    from apps.payroll.models import Payroll

    jobs = list(KpiLine.objects.filter(sheet=sheet).values_list("employment_id", flat=True))
    closed = Payroll.objects.filter(year=sheet.year, month=sheet.month, status="approved", deletion_mark=False,
                                    lines__employment_id__in=jobs).distinct()
    if closed.exists():
        refs = ", ".join(f"nr. {p.number}" for p in closed[:3])
        raise ValidationError({"detail": f"Calculul salariului pe {sheet.month:02d}.{sheet.year} ({refs}) e aprobat pentru acești "
                                         f"șoferi; redeschideți-l întâi, apoi recalculați-l după fișa KPI."})


def problems(sheet: KpiSheet) -> list:
    out = []
    lines = list(KpiLine.objects.filter(sheet=sheet).select_related("employee", "scheme"))
    if not lines:
        out.append("Fișa nu are rânduri: completați-o (șoferii cu schemă KPI — Setări → Schemele KPI).")
    dup = (KpiLine.objects.filter(sheet__status="approved", sheet__deletion_mark=False, sheet__year=sheet.year,
                                  sheet__month=sheet.month, employment_id__in=[ln.employment_id for ln in lines])
           .exclude(sheet=sheet).select_related("employee", "sheet"))
    for d in dup[:5]:
        out.append(f"{d.employee.full_name()} are deja prima KPI pe {sheet.month:02d}.{sheet.year} în fișa {d.sheet.reference()}.")
    for ln in lines:
        if ln.scheme.base_kind == "fixed" and ln.scheme.base_amount <= 0 or ln.scheme.base_kind == "pct" and ln.scheme.base_pct <= 0:
            out.append(f"Schema {ln.scheme.code} n-are baza primei (suma sau procentul): Setări → Schemele KPI.")
            break
    return out


def approve(sheet: KpiSheet, user):
    editable(sheet)
    for ln in KpiLine.objects.filter(sheet=sheet).select_related("scheme", "employment"):  # socotite din nou la aprobare
        compute_line(ln, sheet)
        ln.save()
    found = problems(sheet)
    if found:
        raise ValidationError({"detail": " ".join(found)})
    payroll_closed(sheet)
    sheet.status, sheet.approved_by, sheet.approved_at = "approved", user, timezone.now()
    sheet.save(update_fields=["status", "approved_by", "approved_at"])


def unapprove(sheet: KpiSheet):
    if sheet.status != "approved":
        raise ValidationError({"detail": "Fișa KPI nu este aprobată."})
    payroll_closed(sheet)
    sheet.status, sheet.approved_by, sheet.approved_at = "draft", None, None
    sheet.save(update_fields=["status", "approved_by", "approved_at"])


def totals(sheet: KpiSheet) -> dict:
    lines = list(sheet.lines.all())
    scored = [ln.score for ln in lines if ln.score is not None]
    return {"people": len(lines), "amount": float(sum((ln.amount for ln in lines), ZERO)),
            "avg_score": float(sum(scored, ZERO) / len(scored)) if scored else None}


def month_lines(year: int, month: int) -> dict:
    """{employment_id: [rândurile fișelor KPI aprobate ale lunii]} — pentru calculul salariului."""
    out = defaultdict(list)
    for ln in (KpiLine.objects.filter(sheet__status="approved", sheet__deletion_mark=False, sheet__year=year, sheet__month=month)
               .select_related("sheet", "scheme").order_by("sheet_id", "id")):
        out[ln.employment_id].append(ln)
    return dict(out)
