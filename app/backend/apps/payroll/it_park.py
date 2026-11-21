"""Regimul fiscal IT Park (Legea 77/2016 privind parcurile pentru tehnologia informației, modif. Legea 415/2023; Codul fiscal,
titlul X, cap. 1, art. 367–379).

- **Regimul pe luni** (`FiscalRegime`): general sau IT Park, din luna următoare obținerii / retragerii statutului (art. 375).
  Salariul calculat într-un regim și plătit în altul rămâne în regimul lunii calculului (`PayrollLine.it_park`).
- **Salariul din CIM** în regim e impozitat final (art. 377 alin. (1)): fără impozit pe venit, CNAM, CAS și scutiri; salariul
  minim (completarea MINIM) rămâne obligatoriu. Plățile care nu sunt salariu — contractele de prestări servicii — rămân în
  regimul general (art. 372 alin. (2)).
- **Impozitul unic** (art. 370–371): 7 % din venitul lunar din vânzări, dar cel puțin 30 % × salariul mediu lunar prognozat ×
  numărul angajaților (cu CIM, cel puțin o zi lucrată în lună — art. 369 alin. (2)); lunar, necumulativ.
- **Asigurarea socială** (Legea 77/2016 art. 16 alin. (1); HG 108/2005 pct. 70¹): venitul asigurat al angajatului e 68 % ×
  salariul mediu, o dată pe persoană, în fiecare lună cu măcar o zi lucrată; în IPC21 se împarte pe categorii după zile
  (162 — muncă, 160 — concediul plătit, 15311 / 15321 — zilele de boală ale angajatorului).
- **Declarațiile:** IU17 (lunar, până la 25), ISAPTI17 (anual, până la 25 ianuarie) și nota anuală pentru fiecare angajat
  (până la 1 martie) — formularele aprobate prin OMF 135/2017. Anexa 8 (fișa personală) nu se ține pentru salariile din regim.

Ce nu e confirmat din textul oficial e marcat „de verificat” în constante și în instrucțiuni.
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

ZERO, CENT = Decimal("0"), Decimal("0.01")
IT_PARK, GENERAL = "it_park", "general"
FINAL_NOTE = "Impozitat final — impozit unic IT Park (Codul fiscal, art. 377)"
CATEGORY_WORK, CATEGORY_LEAVE, CATEGORY_EXTRA_LEAVE = "162", "160", "16012"
PAID_LEAVE = {"annual": CATEGORY_LEAVE, "extra": CATEGORY_EXTRA_LEAVE}  # concediile plătite de angajator (IPC21, col. 7)


def q(value) -> Decimal:
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def month_bounds(year: int, month: int):
    first = date(year, month, 1)
    last = (first.replace(month=month % 12 + 1, year=year + (month == 12)) - timedelta(days=1))
    return first, last


# --- regimul ----------------------------------------------------------------------------------------------------------
def regime_on(day: date) -> str:
    """Regimul fiscal în vigoare în luna zilei date (ultimul cu „în vigoare din” ≤ prima zi a lunii); fără istoric — general."""
    from .models import FiscalRegime

    r = FiscalRegime.objects.filter(date_from__lte=day.replace(day=1)).order_by("-date_from").first()
    return r.regime if r else GENERAL


def is_it_park(year: int, month: int) -> bool:
    return regime_on(date(year, month, 1)) == IT_PARK


def it_park_months(first: date, last: date) -> set:
    """Lunile (an, lună) în regim IT Park dintre `first` și `last` (inclusiv)."""
    from .models import FiscalRegime

    history = list(FiscalRegime.objects.order_by("date_from").values_list("date_from", "regime"))
    out, cur = set(), first.replace(day=1)
    while cur <= last:
        regime = GENERAL
        for since, value in history:
            if since <= cur:
                regime = value
        if regime == IT_PARK:
            out.add((cur.year, cur.month))
        cur = (cur + timedelta(days=32)).replace(day=1)
    return out


def ever_it_park() -> bool:
    from .models import FiscalRegime

    return FiscalRegime.objects.filter(regime=IT_PARK).exists()


def insured_income(c) -> Decimal:
    """Venitul asigurat lunar al angajatului rezidentului: % din salariul mediu lunar prognozat (68 % × 17 400 = 11 832)."""
    return q(c("avg_salary") * c("it_park_insured_pct", "68") / 100)


def sick_covered(c) -> bool:
    """Zilele de boală plătite de angajator sunt plăți salariale acoperite de impozitul unic (constanta, de verificat)."""
    return c("it_park_sick_covered", "1") != 0


# --- numărul angajaților (IU17, rândul 020) --------------------------------------------------------------------------------
def _jobs(ctx):
    """Raporturile de muncă din lună în toată întreprinderea (fără dubluri), cu zilele lor."""
    from apps.org.models import Subdivision

    out, seen = [], set()
    for sub in Subdivision.objects.filter(parent__isnull=True):
        for jd in ctx.jobs(sub):
            if jd.job.pk not in seen:
                seen.add(jd.job.pk)
                out.append(jd)
    return out


def headcount(year: int, month: int) -> list:
    """Angajații cu CIM care contează la impozitul unic minim: cel puțin o zi lucrată în lună (art. 369 alin. (2); IU17 rd. 020),
    fără proporționalizare la timp parțial și o singură dată pe persoană (cu mai multe raporturi). Zilele lucrate — din pontaj
    (tabela secției), fără pontaj — zilele lucrătoare ale raportului fără absențe și suspendare. Cine n-a lucrat nicio zi, dar e
    în concediu de maternitate, se numără după constanta `it_park_count_maternity` (de verificat)."""
    from apps.leave.models import SickLeave
    from apps.worktime import services as worktime
    from apps.worktime.models import TimesheetLine

    from .engine import Constants

    first, last = month_bounds(year, month)
    c = Constants(last)
    count_maternity = c("it_park_count_maternity", "1") != 0
    ctx = worktime.Context(year, month)
    sheets = {ln.employment_id: ln.totals or {} for ln in TimesheetLine.objects.filter(
        timesheet__year=year, timesheet__month=month, timesheet__deletion_mark=False)}
    pregnancy = set(SickLeave.objects.filter(kind="pregnancy", deletion_mark=False, date_from__lte=last, date_to__gte=first)
                    .values_list("employee_id", flat=True))
    people: dict = {}
    for jd in _jobs(ctx):
        job = jd.job
        if job.kind == "contractor":
            continue
        if job.pk in sheets and "days" in sheets[job.pk]:
            worked, source = int(sheets[job.pk].get("days") or 0), "timesheet"
        else:
            worked, source = 0, "calendar"
            for d in jd.days:
                a = jd.absence(d)
                if ctx.cal.is_working(d) and not jd.is_suspended(d) and (a is None or a.kind in ("travel", "training")):
                    worked += 1
        maternity = any(a.kind == "maternity" for a in jd.absences if a.date_from <= last and a.date_to >= first) \
            or job.employee_id in pregnancy
        p = people.setdefault(job.employee_id, {
            "employee": job.employee_id, "name": job.employee.full_name(), "tab_number": job.employee.tab_number,
            "idnp": job.employee.idnp, "worked_days": 0, "maternity": False, "jobs": [], "source": source})
        p["worked_days"] += worked
        p["maternity"] = p["maternity"] or maternity
        p["jobs"].append(f"{job.get_kind_display()}: {job.occupation.name_ro}" + (f" ({float(job.rate):g})" if job.rate != 1 else ""))
        if source == "timesheet":
            p["source"] = source
    out = []
    for p in sorted(people.values(), key=lambda x: x["name"]):
        if p["worked_days"] > 0:
            p["counted"], p["reason"] = True, f"{p['worked_days']} zile lucrate"
        elif p["maternity"] and count_maternity:
            p["counted"], p["reason"] = True, "concediu de maternitate (se numără — de verificat)"
        else:
            p["counted"], p["reason"] = False, "nicio zi lucrată în lună"
        out.append(p)
    return out


# --- impozitul unic pe lună (IU17) ------------------------------------------------------------------------------------------
def month_tax(year: int, month: int, with_people=True) -> dict:
    """Calculul impozitului unic al lunii: rd. 010 — venitul din vânzări × 7 %, rd. 020 — angajații × 30 % din salariul mediu,
    rd. 030 — impozitul datorat (cel mai mare). Venitul din vânzări îl scrie contabilul; fără el — doar minimul."""
    from .engine import Constants
    from .models import ItParkMonth

    first, last = month_bounds(year, month)
    c = Constants(last)
    doc = ItParkMonth.objects.filter(year=year, month=month).first()
    people = headcount(year, month)
    n = sum(1 for p in people if p["counted"])
    pct, min_pct, avg = c("it_park_tax_pct", "7"), c("it_park_min_pct", "30"), c("avg_salary")
    per_employee = q(avg * min_pct / 100)
    sales = doc.sales_income if doc and doc.sales_income is not None else None
    by_sales = q((sales or ZERO) * pct / 100)
    minimum = q(per_employee * n)
    due = max(by_sales, minimum)
    rows = [
        {"code": "010", "label": "Venitul din vânzări", "base": sales, "rate": f"{_n(pct)} %", "amount": by_sales,
         "basis": "Codul fiscal, art. 369 alin. (1), art. 370 alin. (1)"},
        {"code": "020", "label": "Numărul de salariați (cel puțin o zi lucrată în lună)", "base": Decimal(n),
         "rate": f"{_n(min_pct)} % × {_n(avg)} = {_n(per_employee)} lei", "amount": minimum,
         "basis": "Codul fiscal, art. 369 alin. (2), art. 370 alin. (2)"},
        {"code": "030", "label": "Impozitul unic de plată (cel mai mare dintre rd. 010 și rd. 020)", "base": None, "rate": "",
         "amount": due, "basis": "Codul fiscal, art. 370, 371"},
    ]
    deadline = (last + timedelta(days=25))
    out = {"year": year, "month": month, "it_park": is_it_park(year, month), "sales_income": sales,
           "sales_entered": sales is not None, "submitted_on": doc.submitted_on if doc else None, "note": doc.note if doc else "",
           "employees": n, "per_employee": per_employee, "tax_pct": pct, "min_pct": min_pct, "avg_salary": avg,
           "by_sales": by_sales, "minimum": minimum, "due": due, "rule": "sales" if by_sales > minimum else "minimum",
           "deadline": deadline, "rows": rows, "persons": len(people)}
    if with_people:
        out["people"] = people
    return out


def _n(value) -> str:
    return format(Decimal(value or 0).normalize(), "f")


def year_overview(year: int) -> list:
    """Lunile anului în regim IT Park (și cele cu venitul scris), cu impozitul calculat — pentru lista de pe ecran."""
    from .models import ItParkMonth

    months = {m for (y, m) in it_park_months(date(year, 1, 1), date(year, 12, 31)) if y == year}
    months |= set(ItParkMonth.objects.filter(year=year).values_list("month", flat=True))
    return [month_tax(year, m, with_people=False) for m in sorted(months)]


# --- ISAPTI17 și nota anuală (anexa 5) ---------------------------------------------------------------------------------------
def annual_rows(year: int, employee_ids=None) -> list:
    """Pe angajat: salariul din regim îndreptat spre achitare în an (din îndreptările achitate în an — partea impozitată final)
    și numărul lunilor în care a activat în regim (lunile anului cu un raport CIM calculat în regim, aprobat)."""
    from apps.staff.models import Employee

    from .models import PaymentLine, PayrollLine

    income = defaultdict(lambda: ZERO)
    qs = PaymentLine.objects.filter(payment__status="paid", payment__deletion_mark=False, payment__paid_on__year=year,
                                    final_gross__gt=0)
    if employee_ids is not None:
        qs = qs.filter(employee_id__in=list(employee_ids))
    for ln in qs:
        income[ln.employee_id] += ln.final_gross
    months = defaultdict(set)
    lines = PayrollLine.objects.filter(payroll__status="approved", payroll__deletion_mark=False, payroll__year=year, it_park=True)
    if employee_ids is not None:
        lines = lines.filter(employee_id__in=list(employee_ids))
    for ln in lines.select_related("payroll"):
        months[ln.employee_id].add(ln.payroll.month)
    ids = set(income) | set(months)
    people = {e.pk: e for e in Employee.objects.filter(pk__in=ids)}
    rows = []
    for n, pk in enumerate(sorted(ids, key=lambda k: (people[k].last_name, people[k].first_name, k)), start=1):
        e = people[pk]
        rows.append({"no": n, "employee": pk, "idnp": e.idnp, "name": e.full_name(), "tab_number": e.tab_number,
                     "income": q(income[pk]), "months": len(months[pk]), "month_list": sorted(months[pk]),
                     "missing_idnp": not e.idnp})
    return rows


def isapti17(year: int) -> dict:
    from .reports import header_problems

    rows = annual_rows(year)
    return {"year": year, "rows": [{**r, "income": float(r["income"])} for r in rows], "header_missing": header_problems(),
            "total": {"persons": len(rows), "income": float(sum((r["income"] for r in rows), ZERO))},
            "missing_idnp": sum(1 for r in rows if r["missing_idnp"])}


# --- venitul asigurat în IPC21 (tabelul 2) ---------------------------------------------------------------------------------
def ipc21_person_rows(e, lines, first: date, last: date, c, absences: list) -> tuple:
    """Rândurile tabelului 2 pentru raporturile CIM ale persoanei calculate în regim: venitul asigurat (o dată pe persoană)
    împărțit pe categorii proporțional cu zilele calendaristice — 162 (muncă), 160 (concediul de odihnă plătit), 15311 /
    15321 (zilele de boală plătite de angajator); fără nicio zi lucrată sau plătită în lună — fără venit asigurat (concediul
    neplătit pe toată luna: 159). Tariful și CAS — 0: contribuția e cuprinsă în impozitul unic (de verificat).
    Întoarce (rânduri [(categoria, de la, până la, baza, indemnizația)], codul funcției)."""
    from .engine import employer_sick_days

    start = max(min(ln.employment.date_from for ln in lines), first)
    end = min(max((ln.employment.end_date or last) for ln in lines), last)
    active = {start + timedelta(days=i) for i in range((end - start).days + 1)} if end >= start else set()
    code = next((ln.employment.occupation.code for ln in lines if ln.employment.occupation_id and ln.employment.occupation.code), "")
    sick_amount = {"illness": ZERO, "work_accident": ZERO}
    for ln in lines:
        for it in ln.items.all():
            if it.pay_type.auto == "sick":
                sick_amount["illness"] += it.amount
            elif it.pay_type.auto == "sick_accident":
                sick_amount["work_accident"] += it.amount
    leave = {CATEGORY_LEAVE: set(), CATEGORY_EXTRA_LEAVE: set()}  # concediul de odihnă anual / suplimentar plătit
    other_days = set()
    for a in absences:
        if a.kind in ("travel", "training"):
            continue
        days = {d for d in active if a.date_from <= d <= a.date_to}
        if a.kind in PAID_LEAVE:
            leave[PAID_LEAVE[a.kind]] |= days
        else:
            other_days |= days
    leave_days = leave[CATEGORY_LEAVE] | leave[CATEGORY_EXTRA_LEAVE]
    sick_days = {}
    for kind, n, _note in employer_sick_days(e, first, last, c):
        sick_days[kind] = n
    sick_total = sum(sick_days.values())
    leave_n = len(leave_days)
    leave[CATEGORY_EXTRA_LEAVE] -= leave[CATEGORY_LEAVE]
    work_n = len(active - leave_days - other_days)  # zilele de boală (și ale angajatorului) sunt printre absențe
    paid = work_n + leave_n + sick_total
    rows = []
    if paid <= 0:
        unpaid = [a for a in absences if a.kind == "unpaid" and a.date_from <= first and a.date_to >= last]
        if unpaid:  # concediul neplătit pe toată luna, fără nicio zi lucrată
            rows.append(("159", first, last, ZERO, ZERO))
        return rows, code
    insured = insured_income(c)
    parts = [(CATEGORY_WORK, work_n, start, end)] + [(cat, len(days), min(days), max(days)) for cat, days in leave.items() if days]
    from .xml_export import SICK_ACCIDENT_CATEGORY, SICK_EMPLOYER_CATEGORY

    parts += [(SICK_EMPLOYER_CATEGORY, sick_days.get("illness", 0), None, None),
              (SICK_ACCIDENT_CATEGORY, sick_days.get("work_accident", 0), None, None)]
    parts = [p for p in parts if p[1] > 0]
    left = insured
    sick_dates = [a for a in absences if a.kind == "sick"]
    for i, (cat, n, s, f) in enumerate(parts):
        base = left if i == len(parts) - 1 else q(insured * n / paid)
        left -= base
        if cat in (SICK_EMPLOYER_CATEGORY, SICK_ACCIDENT_CATEGORY):
            s = max(sick_dates[0].date_from, first) if sick_dates else first
            f = min(sick_dates[-1].date_to, last) if sick_dates else last
        sick = sick_amount["illness"] if cat == SICK_EMPLOYER_CATEGORY else (
            sick_amount["work_accident"] if cat == SICK_ACCIDENT_CATEGORY else ZERO)
        rows.append((cat, s, f, base, sick))
    return rows, code
