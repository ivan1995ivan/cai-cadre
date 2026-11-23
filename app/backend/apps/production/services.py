"""Socotelile producției: tariful pe unitate al lucrării la o dată, suma și orele normate ale rândului, împărțirea sumei
brigăzii, verificarea la aprobare și totalul lunii pe raport de muncă pentru calculul salariului.

- **Tariful pe unitate** (CM art. 170): scris direct în norma lucrării, sau tariful pe oră al categoriei lucrării (grila în
  vigoare la data raportului) × norma de timp (ore pe unitate; la norma de producție — 1 / unități pe oră). Se păstrează cu 4
  zecimale (tarifele de bani pe bucată), sumele — cu 2.
- **Rândul** (CM art. 162): plătit = (cantitatea bună + rebutul fără vina lucrătorului) × tariful + rebutul parțial × tariful ×
  procentul din contractul colectiv; rebutul total din vina lucrătorului nu se plătește. Orele normate = (cantitatea bună +
  rebutul fără vină) × norma de timp — producția primită ca bună.
- **Brigada**: suma tuturor lucrărilor (și partea din ele în acord progresiv, și orele normate) se împarte membrilor după
  ore × coeficientul de participare (× tariful orar al membrului, la împărțirea „după tarif”); bănuții rămași din rotunjire
  merg la membrul cu ponderea cea mai mare, ca totalul să rămână exact.
- **Luna** (`month_summary`): rapoartele aprobate, nemarcate, cu data în lună — pe raport de muncă: suma, partea progresivă,
  orele normate, orele lucrate (dacă toate rândurile le au) și trimiterile la rapoarte pentru explicația rândului din calcul.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from rest_framework.exceptions import ValidationError

from apps.worktime import hour_types

from .models import Operation, ProductionLine, ProductionMember, ProductionReport, TariffGrid

ZERO, CENT, Q4 = Decimal("0"), Decimal("0.01"), Decimal("0.0001")


def q(value) -> Decimal:
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(value, places=None) -> str:
    """Numărul pentru explicații, cu virgulă zecimală: `places=2` — sumele în lei („1 234,50”, „50”), altfel fără zerourile de
    la coadă („0,4567”, „1,5”)."""
    if places == 2:
        return hour_types.fmt(value, True)
    d = Decimal(value or 0)
    if places is not None:
        d = d.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    text = format(d.normalize(), "f")
    return text.replace(".", ",")


def unit_label(op: Operation) -> str:
    return op.get_unit_display()


# --- tariful ------------------------------------------------------------------------------------------------------------
def grid_on(code: str, day: date):
    return TariffGrid.objects.filter(code=code, date_from__lte=day, deletion_mark=False).order_by("-date_from").first()


def rank_hourly(code: str, rank: int, day: date):
    """Tariful pe oră al categoriei din grila în vigoare la data dată: (tariful, explicația) sau (None, motivul)."""
    grid = grid_on(code, day)
    if grid is None:
        return None, f"grila tarifară {code} nu are o versiune în vigoare la {day:%d.%m.%Y}"
    r = grid.ranks.filter(rank=rank).first()
    if r is None:
        return None, f"grila tarifară {code} din {grid.date_from:%d.%m.%Y} nu are categoria {rank}"
    return r.hourly(), f"categoria {rank} ({code} din {grid.date_from:%d.%m.%Y})"


def rate_on(operation: Operation, day: date):
    return operation.rates.filter(date_from__lte=day).order_by("-date_from").first()


def price(operation: Operation, day: date) -> dict:
    """Tariful pe unitate și norma de timp ale lucrării la data dată, cu explicația; eroare dacă lipsesc."""
    r = rate_on(operation, day)
    if r is None:
        raise ValidationError({"detail": f"Lucrarea {operation.code} nu are normă și tarif în vigoare la {day:%d.%m.%Y} "
                                         f"(Setări → Lucrările în acord)."})
    nt = r.norm_time()
    unit = unit_label(operation)
    if not nt:
        raise ValidationError({"detail": f"Lucrarea {operation.code}: norma din {r.date_from:%d.%m.%Y} este 0."})
    norm_text = (f"norma de timp {fmt(nt)} ore" if r.norm_kind == "time"
                 else f"norma de producție {fmt(r.norm_value)} {unit} pe oră")
    if r.piece_rate is not None:
        return {"rate": r.piece_rate.quantize(Q4), "norm_time": nt, "how": f"tariful {fmt(r.piece_rate)} lei / {unit}; {norm_text}"}
    if not r.grid_code or r.rank is None:
        raise ValidationError({"detail": f"Lucrarea {operation.code}: norma din {r.date_from:%d.%m.%Y} n-are nici tarif pe unitate, "
                                         f"nici categoria din grila tarifară."})
    hourly, how = rank_hourly(r.grid_code, r.rank, day)
    if hourly is None:
        raise ValidationError({"detail": f"Lucrarea {operation.code}: {how}."})
    rate = (hourly * nt).quantize(Q4, rounding=ROUND_HALF_UP)
    if r.norm_kind == "time":
        text = f"{how} {fmt(hourly)} lei/oră × {norm_text} = {fmt(rate)} lei / {unit}"
    else:
        text = f"{how} {fmt(hourly)} lei/oră ÷ {fmt(r.norm_value)} {unit} pe oră = {fmt(rate)} lei / {unit}"
    return {"rate": rate, "norm_time": nt, "how": text}


# --- rândurile ----------------------------------------------------------------------------------------------------------
def line_problem(line: ProductionLine) -> str:
    for name in ("quantity", "defect_nofault", "defect_partial", "defect_worker"):
        if getattr(line, name) is None or getattr(line, name) < 0:
            return "cantitățile nu pot fi negative"
    if line.hours is not None and (line.hours < 0 or line.hours > 744):
        return "orele sunt între 0 și 744"
    if line.defect_partial and line.defect_partial_pct is None:
        return "la rebutul parțial dați procentul de plată din contractul colectiv (CM art. 162 alin. (3))"
    if line.defect_partial_pct is not None and not (0 <= line.defect_partial_pct <= 100):
        return "procentul de plată a rebutului parțial este între 0 și 100"
    if not (line.quantity or line.defect_nofault or line.defect_partial or line.defect_worker):
        return "rândul n-are nicio cantitate"
    return ""


def compute_line(line: ProductionLine, day: date) -> None:
    """Tariful, norma de timp, suma, orele normate și explicația rândului (fără salvare)."""
    p = price(line.operation, day)
    rate, nt = p["rate"], p["norm_time"]
    paid = line.quantity + line.defect_nofault
    partial_pct = line.defect_partial_pct or ZERO
    amount = rate * paid + rate * line.defect_partial * partial_pct / 100
    unit = unit_label(line.operation)
    parts = [f"{fmt(paid)} {unit} × {fmt(rate)}"]
    if line.defect_nofault:
        parts[0] += f" (din ele rebut fără vină {fmt(line.defect_nofault)})"
    if line.defect_partial:
        parts.append(f"rebut parțial {fmt(line.defect_partial)} × {fmt(rate)} × {fmt(partial_pct)} %")
    if line.defect_worker:
        parts.append(f"rebut din vina lucrătorului {fmt(line.defect_worker)} — neplătit")
    line.rate, line.norm_time = rate, nt.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    line.amount = q(amount)
    line.normed_hours = q(nt * paid)
    line.how = ("; ".join(parts) + f" = {fmt(line.amount, 2)} lei; {p['how']}")[:300]


def member_hourly(employment, day: date) -> Decimal:
    """Tariful orar al membrului la data dată (din istoricul raportului de muncă)."""
    rec = employment.history.filter(date__lte=day).order_by("-date", "-id").first()
    return Decimal(rec.hourly_rate if rec else employment.hourly_rate or 0)


def _split(total: Decimal, weights: list, places=CENT) -> list:
    """Împarte `total` după ponderi, rotunjit; restul din rotunjire — la ponderea cea mai mare."""
    whole = sum(weights, ZERO)
    if not whole:
        return [ZERO for _ in weights]
    parts = [(total * w / whole).quantize(places, rounding=ROUND_HALF_UP) for w in weights]
    diff = total - sum(parts, ZERO)
    if diff:
        k = max(range(len(weights)), key=lambda i: weights[i])
        parts[k] += diff
    return parts


def distribute(report: ProductionReport, lines: list, members: list) -> None:
    """Partea fiecărui membru din suma brigăzii, din partea progresivă și din orele normate (fără salvare)."""
    tariff = report.brigade is not None and report.brigade.distribution == "tariff"
    weights = []
    for m in members:
        m.hourly = member_hourly(m.employment, report.date) if tariff else None
        weights.append(m.hours * m.coefficient * (m.hourly or ZERO) if tariff else m.hours * m.coefficient)
    total = sum((ln.amount for ln in lines), ZERO)
    prog = sum((ln.amount for ln in lines if ln.operation.progressive), ZERO)
    normed = sum((ln.normed_hours for ln in lines), ZERO)
    for m, a, p, n in zip(members, _split(total, weights), _split(prog, weights), _split(normed, weights)):
        m.amount, m.progressive_amount, m.normed_hours = a, p, n


def members_problem(report: ProductionReport, members: list) -> str:
    if not members:
        return "raportul pe brigadă are nevoie de membri (cu orele și coeficientul lor)"
    seen = set()
    for n, m in enumerate(members, start=1):
        if m.employment_id in seen:
            return f"membrul {n} ({m.employment.employee.full_name()}) apare de două ori"
        seen.add(m.employment_id)
        if m.hours is None or m.hours < 0 or m.hours > 744:
            return f"membrul {n}: orele sunt între 0 și 744"
        if m.coefficient is None or m.coefficient < 0 or m.coefficient > 10:
            return f"membrul {n}: coeficientul de participare este între 0 și 10"
    if not any(m.hours and m.coefficient for m in members):
        return "niciun membru n-are ore și coeficient: suma brigăzii nu are cui se împărți"
    if report.brigade is not None and report.brigade.distribution == "tariff":
        for m in members:
            if m.hours and m.coefficient and not member_hourly(m.employment, report.date):
                return (f"{m.employment.employee.full_name()} n-are tariful orar în raportul de muncă (împărțirea „după tarif” "
                        f"îl folosește)")
    return ""


def recompute(report: ProductionReport, strict: bool = False) -> list:
    """Socotește din nou rândurile și membrii raportului (și-i salvează). La ciornă, un rând care nu se poate socoti (lucrarea
    fără normă) rămâne cu suma 0 și explicația erorii; `strict` (la aprobare) oprește cu eroare. Întoarce problemele găsite."""
    problems = []
    lines = list(report.lines.select_related("operation", "employment__employee").order_by("sort", "id"))
    for n, ln in enumerate(lines, start=1):
        who = f"Rândul {n} ({ln.operation.code})"
        bad = line_problem(ln)
        if bad:
            problems.append(f"{who}: {bad}")
        if report.kind == "individual":
            if ln.employment_id is None:
                problems.append(f"{who}: alegeți angajatul (raportul de muncă)")
            elif not ln.employment.is_active_on(report.date):
                problems.append(f"{who}: raportul de muncă al lui {ln.employment.employee.full_name()} nu e activ la "
                                f"{report.date:%d.%m.%Y}")
        elif ln.employment_id is not None:
            problems.append(f"{who}: la raportul pe brigadă rândurile nu au angajat (suma se împarte membrilor)")
        if ln.operation.progressive and report.kind == "individual" and ln.hours is None:
            problems.append(f"{who}: lucrarea în acord progresiv cere orele lucrate (din ele se socotește îndeplinirea normei)")
        try:
            compute_line(ln, report.date)
        except ValidationError as exc:
            text = exc.detail.get("detail") if isinstance(exc.detail, dict) else exc.detail
            problems.append(str(text))
            ln.rate = ln.norm_time = None
            ln.amount = ln.normed_hours = ZERO
            ln.how = str(text)[:300]
        ln.save(update_fields=["rate", "norm_time", "amount", "normed_hours", "how"])
    members = list(report.members.select_related("employment__employee").order_by("sort", "id"))
    if report.kind == "brigade":
        if report.brigade_id is None:
            problems.append("alegeți brigada")
        bad = members_problem(report, members)
        if bad:
            problems.append(bad[0].upper() + bad[1:])
        for m in members:
            if not m.employment.is_active_on(report.date):
                problems.append(f"Raportul de muncă al lui {m.employment.employee.full_name()} nu e activ la {report.date:%d.%m.%Y}")
        distribute(report, lines, members)
        for m in members:
            m.save(update_fields=["hourly", "amount", "progressive_amount", "normed_hours"])
    elif members:
        report.members.all().delete()
    if not lines:
        problems.append("Raportul nu are lucrări")
    if strict and problems:
        raise ValidationError({"detail": "; ".join(problems)})
    return problems


def totals(report: ProductionReport) -> dict:
    lines = list(report.lines.all())
    return {"amount": float(sum((ln.amount for ln in lines), ZERO)), "normed_hours": float(sum((ln.normed_hours for ln in lines), ZERO)),
            "hours": float(sum((ln.hours or ZERO for ln in lines), ZERO)) if report.kind == "individual"
            else float(sum((m.hours for m in report.members.all()), ZERO)), "lines": len(lines)}


# --- luna, pentru calculul salariului ----------------------------------------------------------------------------------
@dataclass
class JobMonth:
    amount: Decimal = ZERO
    progressive: Decimal = ZERO
    normed_hours: Decimal = ZERO
    hours: Decimal = ZERO
    hours_complete: bool = True  # toate rândurile au orele lucrate
    refs: list = field(default_factory=list)  # [(referința raportului, suma)]

    def note(self) -> str:
        parts = [f"{ref}: {fmt(amount, 2)} lei" for ref, amount in self.refs[:6]]
        more = len(self.refs) - 6
        return "rapoartele de producție " + "; ".join(parts) + (f" și încă {more}" if more > 0 else "")


def month_summary(first: date, last: date, employment_ids=None) -> dict:
    """{employment_id: JobMonth} — rapoartele de producție aprobate (nemarcate) cu data în lună."""
    out = defaultdict(JobMonth)
    reports = ProductionReport.objects.filter(status="approved", deletion_mark=False, date__gte=first, date__lte=last)
    per_ref = defaultdict(lambda: ZERO)
    lines = ProductionLine.objects.filter(report__in=reports, employment__isnull=False).select_related("operation", "report")
    members = ProductionMember.objects.filter(report__in=reports).select_related("report")
    if employment_ids is not None:
        lines, members = lines.filter(employment_id__in=employment_ids), members.filter(employment_id__in=employment_ids)
    for ln in lines.order_by("report__date", "report_id", "sort", "id"):
        s = out[ln.employment_id]
        s.amount += ln.amount
        if ln.operation.progressive:
            s.progressive += ln.amount
        s.normed_hours += ln.normed_hours
        if ln.hours is None:
            s.hours_complete = False
        else:
            s.hours += ln.hours
        per_ref[(ln.employment_id, ln.report.date, ln.report_id, ln.report.reference())] += ln.amount
    for m in members.order_by("report__date", "report_id", "sort", "id"):
        s = out[m.employment_id]
        s.amount += m.amount
        s.progressive += m.progressive_amount
        s.normed_hours += m.normed_hours
        s.hours += m.hours
        per_ref[(m.employment_id, m.report.date, m.report_id, m.report.reference() + " (brigada)")] += m.amount
    for (job_id, _day, _pk, ref), amount in sorted(per_ref.items(), key=lambda kv: (kv[0][1], kv[0][2])):
        out[job_id].refs.append((ref, amount))
    return dict(out)


def fulfillment(s: JobMonth, timesheet_hours: Decimal):
    """Îndeplinirea normei (%), orele din care s-a socotit și de unde: orele din rapoarte (dacă toate rândurile le au), altfel
    orele lucrate din pontaj. (None, 0, motivul) — fără ore."""
    if s.hours_complete and s.hours:
        basis, source = s.hours, "orele din rapoarte"
    elif timesheet_hours:
        basis, source = timesheet_hours, "orele lucrate din pontaj"
    else:
        return None, ZERO, "fără ore lucrate"
    return (s.normed_hours / basis * 100), basis, source


def progressive_increment(prog_amount: Decimal, pct: Decimal, steps: list):
    """Sporul acordului progresiv: pentru fiecare treaptă {from: % îndeplinire, pct: spor %}, producția din intervalul
    [treapta; treapta următoare) — partea (min(îndeplinirea, următoarea) − treapta) / îndeplinire din suma progresivă — primește
    sporul treptei. Întoarce (sporul, explicația)."""
    if not prog_amount or pct is None or not steps:
        return ZERO, ""
    ordered = sorted((Decimal(str(s["from"])), Decimal(str(s["pct"]))) for s in steps)
    total, parts = ZERO, []
    for i, (lo, spor) in enumerate(ordered):
        if pct <= lo:
            break
        hi = ordered[i + 1][0] if i + 1 < len(ordered) else None
        band = (min(pct, hi) if hi is not None else pct) - lo
        if band <= 0 or not spor:
            continue
        part = prog_amount * band / pct * spor / 100
        total += part
        parts.append(f"peste {fmt(lo)} %: {fmt(band, 2)} p.p. × {fmt(spor)} %")
    return q(total), "; ".join(parts)

