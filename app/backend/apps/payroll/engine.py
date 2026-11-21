"""Motorul de calcul al salariului pe lună.

Pentru fiecare raport de muncă din lună:
1. pontajul (tabela secției, sau norma întreagă dacă tabela lipsește): ore, noapte, sărbători, suplimentare, absențe;
2. acumulările automate: salariul de funcție pro-rata la ore, sporurile fixe, plata pentru cumul, noaptea, sărbătorile,
   suplimentarele, concediul (media × zile), compensarea, boala (zilele angajatorului), premiile și ajutorul din ordine;
3. sporurile pe trepte de vechime și rândurile personale ale angajatului (sporuri, contract, rețineri);
4. plafoanele neimpozabile, bazele impozitului pe venit și CNAM, celelalte rețineri, CAS al angajatorului.
Impozitul pe venit, scutirea și CNAM nu se calculează aici: se rețin la plată, în îndreptarea spre plată
(apps.payroll.payments), din bazele puse pe rând. Rândurile scrise de mână (manual) rămân la recalculare; restul se refac.
Un rând de mână pe un tip care se calculează singur (salariul, un spor, CAS) îl înlocuiește pe cel calculat; pe un tip fără
calcul automat (premiu unic, reținere) se adaugă. Bazele și CAS se refac din sumele corectate, afară de CAS scris de mână.
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.leave.models import Absence, LeaveAdjustment, SickLeave
from apps.org import calendar as holidays
from apps.orders.models import Incentive
from apps.staff import services as staff
from apps.staff.models import MAIN_KINDS, Employment
from apps.worktime import services as worktime
from apps.worktime.models import TimesheetLine

from .models import EmployeePayItem, PayConstant, Payroll, PayrollItem, PayrollLine, PayType

ZERO, CENT = Decimal("0"), Decimal("0.01")
AT_PAYMENT = ("income_tax", "cnam", "advance")  # tipurile care țin de plată, nu de calcul


def q(value) -> Decimal:
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def num(value) -> str:
    """Numărul fără zerourile de la coadă, pentru explicații (150.0000 → „150”, 0.50 → „0.5”)."""
    return format(Decimal(value or 0).normalize(), "f")


# --- constantele --------------------------------------------------------------------------------------------------
class Constants:
    def __init__(self, on_date: date):
        self.values = {}
        for c in PayConstant.objects.filter(date_from__lte=on_date).order_by("code", "date_from"):
            self.values[c.code] = c.value  # ultima dată ≤ on_date câștigă

    def __call__(self, code: str, default="0") -> Decimal:
        return self.values.get(code, Decimal(default))


def month_bounds(year: int, month: int):
    first = date(year, month, 1)
    last = (first.replace(month=month % 12 + 1, year=year + (month == 12)) - timedelta(days=1))
    return first, last


def add_months(day: date, n: int) -> date:
    m = day.month - 1 + n
    return day.replace(year=day.year + m // 12, month=m % 12 + 1, day=1)


# --- salariul mediu (HG 426/2004, Legea 289/2004) -----------------------------------------------------------------
def average_daily(employment: Employment, year: int, month: int, months: int, fallback_monthly: Decimal) -> tuple:
    """Media pe o zi calendaristică: câștigul din ultimele `months` luni aprobate / zilele calendaristice fără sărbători
    și fără zilele de absență. Fără istoric — salariul lunii / zilele ei calendaristice fără sărbători."""
    first = add_months(date(year, month, 1), -months)
    end = date(year, month, 1) - timedelta(days=1)
    items = (PayrollItem.objects.filter(line__employment=employment, line__payroll__status="approved", pay_type__in_average=True,
                                        line__payroll__year__gte=first.year)
             .select_related("line__payroll"))
    total, used = ZERO, set()
    for it in items:
        p = it.line.payroll
        if first <= date(p.year, p.month, 1) <= end:
            total += it.amount
            used.add((p.year, p.month))
    if not used:
        f, l = month_bounds(year, month)
        days = (l - f).days + 1 - len(holidays.holidays_between(f, l))
        return (q(fallback_monthly / days) if days else ZERO), {"months": 0, "sum": q(fallback_monthly), "days": days}
    start = min(date(y, m, 1) for y, m in used)
    stop = max(month_bounds(y, m)[1] for y, m in used)
    days = (stop - start).days + 1 - len(holidays.holidays_between(start, stop))
    absent = 0
    for a in Absence.objects.filter(employee=employment.employee, date_from__lte=stop, date_to__gte=start).exclude(kind__in=("travel", "training")):
        absent += (min(a.date_to, stop) - max(a.date_from, start)).days + 1
    days = max(days - absent, 1)
    return q(total / days), {"months": len(used), "sum": q(total), "days": days}


# --- incapacitatea temporară de muncă (Legea 289/2004) --------------------------------------------------------------
def _episode_end(sick: SickLeave) -> date:
    """Sfârșitul incapacității: ultimul certificat din lanțul continuărilor (fără cele marcate pentru ștergere)."""
    end, seen, todo = sick.date_to, {sick.pk}, [sick]
    while todo:
        cur = todo.pop()
        for nxt in cur.continuations.filter(deletion_mark=False):
            if nxt.pk not in seen:
                seen.add(nxt.pk)
                end = max(end, nxt.date_to)
                todo.append(nxt)
    return end


def employer_sick_days(employee, first: date, last: date, c) -> list:
    """Zilele plătite de angajator care cad în lună, pe feluri: [(„illness” | „work_accident”, zile, explicația)].
    Boala obișnuită (și celelalte cauze, afară de sarcină): primele `sick_employer_days` zile ale fiecărui certificat
    inițial (cu continuările), cel mult `sick_employer_year_days` pe an calendaristic, în ordinea certificatelor anului;
    accidentul de muncă / boala profesională: primele `sick_accident_days` zile, în afara plafonului anual."""
    per, cap = int(c("sick_employer_days", "5")), int(c("sick_employer_year_days", "15"))
    accident_days = int(c("sick_accident_days", "20"))
    used = defaultdict(int)
    out = {"illness": [0, []], "work_accident": [0, []]}
    certs = (SickLeave.objects.filter(employee=employee, continuation_of__isnull=True, deletion_mark=False,
                                      date_from__year__gte=first.year - 1, date_from__lte=last)
             .exclude(kind="pregnancy").order_by("date_from", "id"))
    for s in certs:
        accident = s.kind == "work_accident"
        length = (_episode_end(s) - s.date_from).days + 1
        if accident:
            allowed = min(accident_days, length)
        else:
            allowed = max(min(per, length, cap - used[s.date_from.year]), 0)
            used[s.date_from.year] += allowed
        if not allowed:
            if s.date_from >= first:
                out["illness"][1].append(f"{s}: plafonul de {cap} zile pe an atins")
            continue
        start, end = max(s.date_from, first), min(s.date_from + timedelta(days=allowed - 1), last)
        if end < start:
            continue
        group = out["work_accident" if accident else "illness"]
        group[0] += (end - start).days + 1
        group[1].append(f"{s} ({start:%d.%m}–{end:%d.%m})" + ("" if accident or allowed == min(per, length)
                                                                  else f", plafonul de {cap} zile pe an"))
    return [(kind, days, "; ".join(notes)) for kind, (days, notes) in out.items() if days]


def sick_average_daily(employment: Employment, year: int, month: int, c, fallback_monthly: Decimal) -> tuple:
    """Venitul mediu zilnic pentru indemnizația de boală (Legea 289/2004, art. 7): venitul asigurat (acumulările din baza
    CAS) din ultimele `sick_avg_months` luni calendaristice aprobate / numărul lunilor (12; mai puține — lunile cu venit),
    cel mult `sick_avg_cap_salaries` salarii medii lunare prognozate pe lună; venitul pe o zi = media lunară / zilele
    calendaristice ale lunii pentru care se plătește (art. 7 alin. (16)). Fără istoric — salariul lunii."""
    months = int(c("sick_avg_months", "12"))
    first = add_months(date(year, month, 1), -months)
    end = date(year, month, 1) - timedelta(days=1)
    per_month = defaultdict(lambda: ZERO)
    for it in (PayrollItem.objects.filter(line__employment=employment, line__payroll__status="approved", pay_type__cas=True,
                                          pay_type__category="accrual", line__payroll__year__gte=first.year)
               .select_related("line__payroll")):
        p = it.line.payroll
        if first <= date(p.year, p.month, 1) <= end:
            per_month[(p.year, p.month)] += it.amount
    n = len(per_month)
    monthly = (sum(per_month.values(), ZERO) / n) if n else fallback_monthly
    cap = c("sick_avg_cap_salaries", "5") * c("avg_salary")
    capped = bool(cap) and monthly > cap
    if capped:
        monthly = cap
    f, l = month_bounds(year, month)
    days = (l - f).days + 1
    note = (f"{n} luni" if n else "fără istoric: salariul lunii") + f", {q(monthly)} lei / {days} zile" + (
        f", plafonul {num(cap)} lei" if capped else "")
    return q(monthly / days), {"months": n, "monthly": q(monthly), "days": days, "note": note}


# --- baza minimă CAS (Legea 489/1999, art. 22 alin. (1)) ---------------------------------------------------------------
def cas_minimum(calcs: list, c) -> None:
    """Baza CAS a salariatului (toate raporturile lui de muncă din calcul, fără contractele de prestări servicii) nu poate fi
    mai mică decât salariul minim proporțional timpului lucrat; la timp parțial (norma totală sub 1) CAS nu poate fi mai mică
    de `cas_min_part_pct` % din CAS-ul pe salariul minim. Fără timp lucrat în lună (concediu neplătit, de îngrijire a
    copilului, boală plătită de CNAS toată luna) — fără bază minimă. Diferența: rândul „CAS pe diferența până la baza
    minimă” pe raportul de bază, cu baza reală și baza minimă în explicație."""
    jobs = [x for x in calcs if x.job.kind != "contractor"]
    if not jobs:
        return
    main = next((x for x in jobs if x.is_main), jobs[0])
    types = main.m.by_auto["cas_min"]
    if not types or any(x.cas_manual for x in jobs):
        return
    minimum, pct = c("min_salary"), c("cas_employer_pct")
    time_share = sum((x.rate * x.worked_share for x in jobs), ZERO)
    if not minimum or not time_share:
        return
    real = sum((x.cas_base for x in jobs), ZERO)
    floor = q(minimum * time_share)
    how = f"salariul minim {num(minimum)} × timpul lucrat {float(time_share) * 100:.4g} %"
    rate = sum((x.rate for x in jobs), ZERO)
    if rate < 1:
        part = q(minimum * c("cas_min_part_pct", "25") / 100)
        if part > floor:
            floor, how = part, f"timp parțial: {num(c('cas_min_part_pct', '25'))} % din salariul minim {num(minimum)}"
    diff = q(floor - real)
    if diff <= 0:
        return
    amount = q(diff * pct / 100)
    main.add(types[0].code, amount, base=diff, percent=pct, note=f"baza reală {q(real)}, baza minimă {floor} ({how})")
    main.line.cas = q(main.line.cas + amount)
    main.info["cas_min"] = {"real": float(q(real)), "minimum": float(floor), "diff": float(diff), "cas": float(amount)}


# --- contextul lunii ------------------------------------------------------------------------------------------------
class Month:
    def __init__(self, payroll: Payroll):
        self.payroll = payroll
        self.year, self.month = payroll.year, payroll.month
        self.first, self.last = month_bounds(self.year, self.month)
        self.const = Constants(self.last)
        self.ctx = worktime.Context(self.year, self.month)
        self.types = {t.code: t for t in PayType.objects.filter(is_active=True).exclude(auto__in=AT_PAYMENT)}
        self.by_auto = defaultdict(list)
        for t in self.types.values():
            if t.formula == "auto" and t.auto != "none":
                self.by_auto[t.auto].append(t)
        self.timesheets = {ln.employment_id: ln.totals or {} for ln in TimesheetLine.objects.filter(
            timesheet__year=self.year, timesheet__month=self.month, timesheet__deletion_mark=False)}
        self.avg_salary = self.const("avg_salary")

    def jobs(self):
        """Raporturile de muncă din lună (toată întreprinderea sau subdiviziunea), cu zilele lor din worktime."""
        if self.payroll.subdivision_id:
            return self.ctx.jobs(self.payroll.subdivision)
        from apps.org.models import Subdivision

        out, seen = [], set()
        for sub in Subdivision.objects.filter(parent__isnull=True):
            for jd in self.ctx.jobs(sub):
                if jd.job.pk not in seen:
                    seen.add(jd.job.pk)
                    out.append(jd)
        out.sort(key=lambda jd: (jd.job.employee.last_name, jd.job.employee.first_name, jd.job.kind != "main", jd.job.pk))
        return out

    def timesheet(self, jd) -> dict:
        t = self.timesheets.get(jd.job.pk)
        if t:
            return t
        norm = self.ctx.norm(jd)
        working = sum(1 for d in jd.days if self.ctx.cal.is_working(d))
        return {"days": working, "hours": float(norm), "night": 0, "holiday": 0, "rest_work": 0, "regular": float(norm),
                "norm": float(norm), "overtime": 0, "overtime_2": 0, "overtime_over": 0, "holiday_in_norm": 0,
                "holiday_over_norm": 0, "missing": 0, "codes": {}, "assumed": True}

    def prior_year_amount(self, employee_id: int, code: str) -> Decimal:
        """Suma tipului pe anul curent din calculele aprobate de dinainte (pentru plafoanele anuale)."""
        qs = PayrollItem.objects.filter(line__employee_id=employee_id, pay_type__code=code, line__payroll__status="approved",
                                        line__payroll__year=self.year, line__payroll__month__lt=self.month)
        return sum((i.amount for i in qs), ZERO)


# --- calculul unui raport de muncă ---------------------------------------------------------------------------------
class LineCalc:
    def __init__(self, month: Month, jd, line: PayrollLine, is_main: bool):
        self.m, self.jd, self.line, self.is_main = month, jd, line, is_main
        self.job = jd.job
        self.ts = month.timesheet(jd)
        self.items: list = []
        self.norm = Decimal(str(self.ts.get("norm") or 0))
        self.hours = Decimal(str(self.ts.get("hours") or 0))
        sub_id, occ_id, rate = jd.values_on(max(jd.days))
        self.rate = Decimal(rate)
        self.salary_full = q(self.job.base_salary * self.rate)  # salariul pentru norma raportului
        self.hourly = q(self.salary_full / self.norm) if self.norm else ZERO
        # orele plătite din salariul lunar: cele obișnuite + cele de sărbătoare / repaus în limita normei; suplimentarele și
        # orele de sărbătoare peste normă se plătesc separat (SUPL, SARB), întregi
        ts = self.ts
        self.salary_hours = (self._d("regular") + self._d("holiday_in_norm")) if "regular" in ts else self.hours
        self.worked_share = (min(self.salary_hours, self.norm) / self.norm) if self.norm else (ZERO if self.job.kind == "contractor" else Decimal("1"))
        occ, sub = month.ctx.occupations.get(occ_id), month.ctx.subdivisions.get(sub_id)
        self.info = {"occupation": occ.name_ro if occ else "", "subdivision": sub.name_ro if sub else "", "kind": self.job.kind,
                     "kind_label": self.job.get_kind_display(), "rate": float(self.rate), "base_salary": float(self.job.base_salary),
                     "salary_full": float(self.salary_full), "hourly": float(self.hourly), "timesheet": self.ts,
                     "tab_number": self.job.employee.tab_number, "name": self.job.employee.full_name(), "is_main": is_main}

    def _d(self, key) -> Decimal:
        return Decimal(str(self.ts.get(key) or 0))

    def add(self, code: str, amount, quantity=None, base=None, percent=None, note="", manual=False):
        t = self.m.types.get(code)
        if t is None or q(amount) == ZERO:
            return None
        item = {"type": t, "amount": q(amount), "quantity": q(quantity) if quantity is not None else None,
                "base": q(base) if base is not None else None, "percent": percent, "note": note[:300], "manual": manual}
        self.items.append(item)
        return item

    def sum_codes(self, codes) -> Decimal:
        return sum((i["amount"] for i in self.items if i["type"].code in codes), ZERO)

    # -- acumulările automate --
    def auto(self):
        m, c = self.m, self.m.const
        share = self.worked_share
        for t in m.by_auto["salary"]:
            if self.job.kind != "contractor":
                self.add(t.code, self.salary_full * share, quantity=self.salary_hours, base=self.salary_full,
                         note=f"{float(self.salary_hours):g} ore din norma {float(self.norm):g}" if self.norm else "")
        for t in m.by_auto["allowance"]:
            if self.job.allowance_pct:
                self.add(t.code, self.salary_full * share * self.job.allowance_pct / 100, base=self.salary_full * share,
                         percent=self.job.allowance_pct)
        for t in m.by_auto["combination"]:
            if self.job.combination_pct:
                self.add(t.code, self.salary_full * share * self.job.combination_pct / 100, base=self.salary_full * share,
                         percent=self.job.combination_pct)
        night = Decimal(str(self.ts.get("night") or 0))
        for t in m.by_auto["night"]:
            if night and self.hourly:
                self.add(t.code, night * self.hourly * c("night_pct") / 100, quantity=night, base=self.hourly, percent=c("night_pct"))
        for t in m.by_auto["holiday"]:
            if self.hourly:
                self._holiday(t.code, self.hourly)
        for t in m.by_auto["overtime"]:
            if self.hourly:
                self._overtime(t.code, self.hourly, full=True)
        self._leave()
        if self.is_main:
            self._sick()
            self._incentives()

    def _holiday(self, code, hourly, hourly_paid=False):
        """Munca în zilele de sărbătoare și de repaus (CM art. 158). Salariul lunar: peste salariu, +100 % pe oră în limita
        normei lunare și +200 % peste normă. Tariful pe oră (rândul „tarif orar × ore”, care plătește deja ora simplă):
        cel puțin dublu — se adaugă diferența până la dublu."""
        c = self.m.const
        if hourly_paid:
            hours = self._d("holiday") + self._d("rest_work")
            pct = c("holiday_hourly_pct", "200") - 100
            if hours and pct > 0:
                self.add(code, hourly * hours * pct / 100, quantity=hours, base=hourly, percent=pct,
                         note=f"{float(hours):g} ore × tarif dublu (CM art. 158)")
            return
        in_norm, over = self._d("holiday_in_norm"), self._d("holiday_over_norm")
        if "holiday_in_norm" not in self.ts:  # pontajele vechi: toate orele de sărbătoare, în limita normei
            in_norm, over = self._d("holiday"), ZERO
        p1, p2 = c("holiday_pct", "100"), c("holiday_over_norm_pct", "200")
        if in_norm or over:
            self.add(code, hourly * (in_norm * p1 + over * p2) / 100, quantity=in_norm + over, base=hourly,
                     percent=p1 if not over else (p2 if not in_norm else None),
                     note=f"{float(in_norm):g} ore în limita normei × {num(p1)} % + {float(over):g} ore peste normă × {num(p2)} %")

    def _overtime(self, code, hourly, full: bool):
        """Orele suplimentare (CM art. 157): primele 2 ore pe zi — cel puțin 150 %, următoarele — 200 % (din pontaj, pe zile).
        `full` — ora întreagă (salariul lunar nu le plătește); altfel doar sporul peste ora simplă (tariful pe oră)."""
        c = self.m.const
        first, nxt = self._d("overtime_2"), self._d("overtime_over")
        if "overtime_2" not in self.ts:  # pontajele vechi: toate cu tariful întâi
            first, nxt = self._d("overtime"), ZERO
        p1, p2 = c("overtime_first_pct", "150"), c("overtime_next_pct", "200")
        if not full:
            p1, p2 = p1 - 100, p2 - 100
        if first or nxt:
            self.add(code, hourly * (first * p1 + nxt * p2) / 100, quantity=first + nxt, base=hourly,
                     percent=p1 if not nxt else (p2 if not first else None),
                     note=f"{float(first):g} ore × {num(p1)} % + {float(nxt):g} ore × {num(p2)} %")

    def _leave(self):
        m = self.m
        leave_days = ZERO
        for a in Absence.objects.filter(employee=self.job.employee, kind__in=("annual", "extra"), date_from__lte=m.last, date_to__gte=m.first):
            if a.employment_id and a.employment_id != self.job.pk:
                continue
            if not a.employment_id and not self.is_main:
                continue
            start, end = max(a.date_from, m.first), min(a.date_to, m.last)
            leave_days += holidays.leave_days(start, end)
        comp_days = ZERO
        for adj in LeaveAdjustment.objects.filter(employee=self.job.employee, kind="compensated", date__gte=m.first, date__lte=m.last):
            if self.is_main:
                comp_days += -adj.days
        if not leave_days and not comp_days:
            return
        monthly = self.salary_full * (Decimal(1) + (self.job.allowance_pct or ZERO) / 100)
        avg, how = average_daily(self.job, m.year, m.month, int(m.const("leave_avg_months", "3")), monthly)
        note = f"media {avg} lei/zi ({how['months']} luni, {how['sum']} lei / {how['days']} zile)"
        for t in m.by_auto["leave"]:
            if leave_days:
                self.add(t.code, avg * leave_days, quantity=leave_days, base=avg, note=note)
        for t in m.by_auto["leave_comp"]:
            if comp_days:
                self.add(t.code, avg * comp_days, quantity=comp_days, base=avg, note=note)

    def _sick(self):
        """Indemnizația pentru incapacitate temporară de muncă din mijloacele angajatorului (Legea 289/2004, art. 4):
        primele 5 zile calendaristice ale fiecărui certificat (cu continuările lui), dar cel mult 15 zile pe an calendaristic,
        numărate din toate certificatele anului, în ordinea lor; accidentul de muncă / boala profesională — primele 20 de zile,
        în afara plafonului de 15. Suma: % × venitul mediu zilnic (art. 7)."""
        m, c = self.m, self.m.const
        for kind, days_left, codes in employer_sick_days(self.job.employee, m.first, m.last, c):
            if not days_left:
                continue
            accident = kind == "work_accident"
            auto = "sick_accident" if accident and m.by_auto["sick_accident"] else "sick"
            pct = c("sick_accident_pct", "100") if accident else c("sick_employer_pct", "75")
            avg, how = sick_average_daily(self.job, m.year, m.month, c, self.salary_full * (Decimal(1) + (self.job.allowance_pct or ZERO) / 100))
            for t in m.by_auto[auto]:
                self.add(t.code, avg * days_left * pct / 100, quantity=days_left, base=avg, percent=pct,
                         note=f"{num(pct)}% din media {avg} lei/zi ({how['note']}); {codes}")

    def _incentives(self):
        m = self.m
        for inc in Incentive.objects.filter(employee=self.job.employee, date__gte=m.first, date__lte=m.last).select_related("kind"):
            kind = inc.kind.code if inc.kind_id else "bonus"
            amount = inc.amount if inc.amount is not None else (self.salary_full * (inc.percent or 0) / 100)
            note = inc.note or (f"ordinul {inc.order_item.order.reference()}" if inc.order_item_id else "")
            for t in m.by_auto["aid" if kind == "aid" else "bonus"]:
                self.add(t.code, amount, base=self.salary_full if inc.amount is None else None, percent=inc.percent, note=note)

    # -- treptele pe vechime --
    def scales(self):
        """Tipurile cu formula „scale”: procentul treptei atinse de vechimea totală în muncă la sfârșitul lunii
        (trepte {"from": ani, "pct": %}, din contractul colectiv / regulamentul de salarizare al întreprinderii)."""
        m = self.m
        years = None
        for t in m.types.values():
            if t.formula != "scale" or t.category != "accrual" or not t.scale:
                continue
            if years is None:
                years = staff.seniority(self.job.employee, m.last)["total"]["years"]
            pct = None
            for threshold, p in sorted((Decimal(str(s["from"])), Decimal(str(s["pct"]))) for s in t.scale if "from" in s):
                if years >= threshold:
                    pct = p
            if pct:
                base = self.sum_codes(t.base_codes or ["SAL"])
                self.add(t.code, base * pct / 100, base=base, percent=pct)

    # -- rândurile personale --
    def personal(self):
        m = self.m
        rows = EmployeePayItem.objects.filter(employee=self.job.employee, date_from__lte=m.last).filter(
            Q(date_to__isnull=True) | Q(date_to__gte=m.first)).select_related("pay_type")
        for r in rows:
            if r.employment_id and r.employment_id != self.job.pk:
                continue
            if not r.employment_id and not self.is_main:
                continue
            t = r.pay_type
            if not t.is_active:
                continue
            pct = r.percent if r.percent is not None else t.percent
            if t.formula == "pct_salary":
                self.add(t.code, self.salary_full * self.worked_share * pct / 100, base=self.salary_full * self.worked_share, percent=pct, note=r.document)
            elif t.formula == "pct_base":
                base = self.sum_codes(t.base_codes)
                self.add(t.code, base * pct / 100, base=base, percent=pct, note=r.document)
            elif t.formula == "hourly":
                rate = r.amount or ZERO
                self.add(t.code, rate * self.hours, quantity=self.hours, base=r.amount, note=r.document)
                if rate:  # tariful pe oră: sporul pentru suplimentare și dublul în zilele de sărbătoare / repaus
                    for x in m.by_auto["overtime"]:
                        self._overtime(x.code, rate, full=False)
                    for x in m.by_auto["holiday"]:
                        self._holiday(x.code, rate, hourly_paid=True)
            else:
                self.add(t.code, r.amount or ZERO, note=r.document)

    # -- bazele, reținerile, CAS --
    def bases(self, manual_items):
        m, c = self.m, self.m.const
        overridden = {it["type"].pk for it in manual_items}
        # rândul de mână înlocuiește rândul calculat de același tip
        self.items = [i for i in self.items if i["type"].pk not in overridden]
        for it in manual_items:  # cele scrise de mână intră în baze
            self.items.append(it)
        self.minimum_completion(overridden)
        cas_fixed = [it["amount"] for it in manual_items if it["type"].auto == "cas"]  # CAS scris de mână: suma lui
        self.cas_manual = bool(cas_fixed)
        gross = tax_base = cnam_base = cas_base = ZERO
        for i in self.items:
            t, amount = i["type"], i["amount"]
            if t.category != "accrual":
                continue
            gross += amount
            limit = ZERO
            if t.exempt_month:
                limit = t.exempt_month
            if t.exempt_avg_pct:
                limit = max(limit, m.avg_salary * t.exempt_avg_pct / 100)
            if t.exempt_year:
                limit = max(limit, t.exempt_year - m.prior_year_amount(self.job.employee_id, t.code))
            taxable_part = max(amount - limit, ZERO) if limit else amount
            i["taxable_part"] = q(taxable_part) if t.taxable else ZERO
            if t.taxable:
                tax_base += taxable_part
            if t.cnam:
                cnam_base += taxable_part
            if t.cas:
                cas_base += taxable_part
        deductions = sum((i["amount"] for i in self.items if i["type"].category == "deduction"), ZERO)
        cas = sum(cas_fixed, ZERO) if cas_fixed else q(cas_base * c("cas_employer_pct") / 100)
        for t in m.by_auto["cas"]:
            if not cas_fixed:
                self.add(t.code, cas, base=cas_base, percent=c("cas_employer_pct"))
        ln = self.line
        ln.gross, ln.taxable, ln.cnam_base, ln.cas, ln.deductions = q(gross), q(tax_base), q(cnam_base), cas, q(deductions)
        ln.net = q(gross - deductions)
        self.cas_base = q(cas_base)
        ln.info = self.info

    def minimum_completion(self, overridden):
        """Completarea până la salariul minim (CM art. 131 alin. (3): în salariul minim nu intră adaosurile, sporurile,
        plățile de stimulare și compensare): salariul de funcție plătit în lună se compară cu salariul minim × norma
        raportului × partea lucrată din normă; diferența — rândul „Completare până la salariul minim”."""
        m = self.m
        if self.job.kind == "contractor" or not self.worked_share:
            return
        types = [t for t in m.by_auto["min_wage"] if t.pk not in overridden]
        if not types:
            return
        minimum = m.const("min_salary")
        target = q(minimum * self.rate * self.worked_share)
        paid = sum((i["amount"] for i in self.items if i["type"].auto == "salary"), ZERO)
        if target > paid:
            self.add(types[0].code, target - paid, base=target,
                     note=f"salariul minim {num(minimum)} × norma {num(self.rate)} × {float(self.worked_share) * 100:.4g} % lucrat = {target}; "
                          f"salariul de funcție {q(paid)}")


TOTALS = ("gross", "taxable", "cnam_base", "cas", "deductions", "net")


@transaction.atomic
def calculate(payroll: Payroll, employee_id: int | None = None) -> dict:
    """Calculul lunii; cu `employee_id` — doar rândurile unui angajat (după o corectare de mână), restul rămân."""
    if payroll.status == "approved":
        from rest_framework.exceptions import ValidationError

        raise ValidationError({"detail": "Calculul aprobat nu se mai recalculează; redeschideți-l întâi."})
    m = Month(payroll)
    lines_qs = payroll.lines.all() if employee_id is None else payroll.lines.filter(employee_id=employee_id)
    existing = {ln.employment_id: ln for ln in lines_qs}
    seen = set()
    main_of = {}
    jobs = m.jobs()
    if employee_id is not None:
        jobs = [jd for jd in jobs if jd.job.employee_id == employee_id]
    order = {jd.job.pk: n for n, jd in enumerate(m.jobs(), start=1)} if employee_id is not None else None
    for jd in jobs:  # raportul de bază al fiecărei persoane: scutirea, boala, premiile merg acolo
        emp_id = jd.job.employee_id
        if emp_id not in main_of or (jd.job.kind in MAIN_KINDS and main_of[emp_id].kind not in MAIN_KINDS):
            main_of[emp_id] = jd.job
    calcs = []
    for n, jd in enumerate(jobs, start=1):
        line = existing.pop(jd.job.pk, None) or PayrollLine(payroll=payroll, employee=jd.job.employee, employment=jd.job)
        line.sort = (order[jd.job.pk] if order else n) * 10
        if line.pk is None:
            line.save()
        manual = [{"type": i.pay_type, "amount": i.amount, "quantity": i.quantity, "base": i.base, "percent": i.percent,
                   "note": i.note, "manual": True} for i in line.items.filter(manual=True).exclude(pay_type__auto__in=AT_PAYMENT).select_related("pay_type")]
        calc = LineCalc(m, jd, line, is_main=main_of[jd.job.employee_id].pk == jd.job.pk)
        calc.auto()
        calc.scales()
        calc.personal()
        calc.bases(manual)
        calcs.append(calc)
    by_employee = defaultdict(list)
    for calc in calcs:
        by_employee[calc.job.employee_id].append(calc)
    for group in by_employee.values():
        cas_minimum(group, m.const)
    for calc in calcs:
        line = calc.line
        line.items.all().delete()
        line.save()
        for k, i in enumerate(sorted(calc.items, key=lambda x: (x["type"].sort, x["type"].code)), start=1):
            PayrollItem.objects.create(line=line, pay_type=i["type"], quantity=i["quantity"], base=i["base"], percent=i["percent"],
                                       amount=i["amount"], taxable_part=i.get("taxable_part", i["amount"] if i["type"].taxable else ZERO),
                                       manual=i["manual"], note=i["note"], sort=k * 10)
        seen.add(calc.job.pk)
    for line in existing.values():  # raporturi care nu mai sunt în lună
        line.delete()
    totals = defaultdict(Decimal)
    count = 0
    for line in payroll.lines.all():
        count += 1
        for f in TOTALS:
            totals[f] += getattr(line, f)
    payroll.totals = {k: float(v) for k, v in totals.items()} | {"lines": count}
    payroll.calculated_at = timezone.now()
    if payroll.status == "checked":
        payroll.status = "draft"
    payroll.save(update_fields=["totals", "calculated_at", "status"])
    return payroll.totals
