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
        return {"days": working, "hours": float(norm), "night": 0, "holiday": 0, "norm": float(norm), "overtime": 0,
                "missing": 0, "codes": {}, "assumed": True}

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
        self.worked_share = (min(self.hours, self.norm) / self.norm) if self.norm else (ZERO if self.job.kind == "contractor" else Decimal("1"))
        occ, sub = month.ctx.occupations.get(occ_id), month.ctx.subdivisions.get(sub_id)
        self.info = {"occupation": occ.name_ro if occ else "", "subdivision": sub.name_ro if sub else "", "kind": self.job.kind,
                     "kind_label": self.job.get_kind_display(), "rate": float(self.rate), "base_salary": float(self.job.base_salary),
                     "salary_full": float(self.salary_full), "hourly": float(self.hourly), "timesheet": self.ts,
                     "tab_number": self.job.employee.tab_number, "name": self.job.employee.full_name(), "is_main": is_main}

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
                self.add(t.code, self.salary_full * share, quantity=self.hours, base=self.salary_full,
                         note=f"{float(self.hours):g} ore din norma {float(self.norm):g}" if self.norm else "")
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
        hol = Decimal(str(self.ts.get("holiday") or 0))
        for t in m.by_auto["holiday"]:
            if hol and self.hourly:
                self.add(t.code, hol * self.hourly * c("holiday_pct") / 100, quantity=hol, base=self.hourly, percent=c("holiday_pct"))
        over = Decimal(str(self.ts.get("overtime") or 0))
        for t in m.by_auto["overtime"]:
            if over and self.hourly:
                self.add(t.code, over * self.hourly * (100 + c("overtime_pct")) / 100, quantity=over, base=self.hourly,
                         percent=100 + c("overtime_pct"))
        self._leave()
        if self.is_main:
            self._sick()
            self._incentives()

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
        m, c = self.m, self.m.const
        paid_days = int(c("sick_employer_days", "5"))
        total_days = ZERO
        for s in SickLeave.objects.filter(employee=self.job.employee, continuation_of__isnull=True, deletion_mark=False, date_from__lte=m.last,
                                          date_to__gte=m.first - timedelta(days=paid_days)).exclude(kind="pregnancy"):
            window_end = s.date_from + timedelta(days=paid_days - 1)
            start, end = max(s.date_from, m.first), min(window_end, m.last, s.date_to)
            if end >= start:
                total_days += (end - start).days + 1
        if not total_days:
            return
        monthly = self.salary_full * (Decimal(1) + (self.job.allowance_pct or ZERO) / 100)
        avg, how = average_daily(self.job, m.year, m.month, int(c("sick_avg_months", "12")), monthly)
        pct = c("sick_employer_pct", "75")
        for t in m.by_auto["sick"]:
            self.add(t.code, avg * total_days * pct / 100, quantity=total_days, base=avg, percent=pct,
                     note=f"{pct}% din media {avg} lei/zi ({how['months']} luni)")

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
                self.add(t.code, (r.amount or ZERO) * self.hours, quantity=self.hours, base=r.amount, note=r.document)
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
        cas_fixed = [it["amount"] for it in manual_items if it["type"].auto == "cas"]  # CAS scris de mână: suma lui
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
        ln.info = self.info


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
        line.items.all().delete()
        line.save()
        for k, i in enumerate(sorted(calc.items, key=lambda x: (x["type"].sort, x["type"].code)), start=1):
            PayrollItem.objects.create(line=line, pay_type=i["type"], quantity=i["quantity"], base=i["base"], percent=i["percent"],
                                       amount=i["amount"], taxable_part=i.get("taxable_part", i["amount"] if i["type"].taxable else ZERO),
                                       manual=i["manual"], note=i["note"], sort=k * 10)
        seen.add(jd.job.pk)
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
