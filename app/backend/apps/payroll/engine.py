"""Motorul de calcul al salariului pe lună.

Pentru fiecare raport de muncă din lună:
1. pontajul (tabela secției, sau norma întreagă dacă tabela lipsește): ore, noapte, sărbători, suplimentare, absențe;
2. acumulările automate: baza după modalitatea de remunerare a raportului (salariul de funcție pro-rata la ore; tariful orar ×
   orele; fără bază la „pe tipuri de ore”), orele pe tipuri (ore plătite × tarif, cu orele garantate — apps.worktime.hour_types;
   la „pe tipuri de ore” și „mixt”), sporurile fixe, plata pentru cumularea funcțiilor / suplinire (înregistrările de pe raport,
   CM art. 156), noaptea, sărbătorile, suplimentarele, concediul (media × zile), compensarea, boala (zilele angajatorului),
   premiile și ajutorul din ordine; lucrările în acord din rapoartele de producție aprobate (apps.production) și sporul
   acordului progresiv peste normă și garanția la neîndeplinirea normei (CM art. 161); staționarea și șomajul tehnic (zilele
   St / Șt din pontaj, cu cauza și procentul din ordin — CM art. 80, 80¹); sporul pentru condiții vătămătoare din
   subdiviziune / funcție; partea impozabilă a tichetelor de masă din borderoul aprobat (cu reținerea ei); din cursele
   aprobate (apps.transport) — plata pe km și diurna (în limita normelor neimpozabilă, peste ele — impozabilă);
3. rândurile scrise de mână (le înlocuiesc pe cele calculate de același tip) și completarea până la salariul minim;
4. celelalte tipuri, în ordinea dependențelor (apps.payroll.dependencies): rândurile personale ale angajatului (sumă fixă,
   % din salariu, tarif orar), treptele de vechime, „% din bază” și formulele (apps.payroll.formula) — fiecare după tipurile
   din baza / formula lui; tipurile „pentru toți angajații” se calculează și fără rândul angajatului;
5. plafoanele neimpozabile, bazele impozitului pe venit și CNAM, celelalte rețineri, CAS al angajatorului și CAS pe
   diferența până la baza minimă.
În lunile în regim IT Park (apps.payroll.it_park) salariul din CIM e impozitat final: bazele impozitului și CNAM sunt 0, fără
CAS și fără baza minimă CAS; completarea până la salariul minim rămâne. Contractele de prestări servicii — regimul general.
Impozitul pe venit, scutirea și CNAM nu se calculează aici: se rețin la plată, în îndreptarea spre plată
(apps.payroll.payments), din bazele puse pe rând. Rândurile scrise de mână (manual) rămân la recalculare; restul se refac.
Un rând de mână pe un tip care se calculează singur (salariul, un spor, CAS) îl înlocuiește pe cel calculat; pe un tip fără
calcul automat (premiu unic, reținere) se adaugă. Tipurile care depind de el (baza sindicatului, o formulă) se calculează
din suma corectată; bazele și CAS — la fel, afară de CAS scris de mână.
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.leave.models import IDLE_KINDS, Absence, LeaveAdjustment, SickLeave
from apps.org import calendar as holidays
from apps.orders.models import Incentive
from apps.staff import services as staff
from apps.staff.models import MAIN_KINDS, RATE_MODES, Employment, FunctionCombination
from apps.worktime import hour_types
from apps.worktime import services as worktime
from apps.worktime.models import HourType, JobHourRate, RosterLine, TimesheetLine
from apps.production import services as production
from apps.transport import services as transport

from . import dependencies, formula, it_park, meal_vouchers
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


def average_hourly(employment: Employment, year: int, month: int, months: int):
    """Câștigul mediu pe oră: acumulările care intră în medie din ultimele `months` luni aprobate / orele lucrate în ele (din
    pontajul păstrat pe rândul calculului). None — fără istoric cu ore."""
    first = add_months(date(year, month, 1), -months)
    end = date(year, month, 1) - timedelta(days=1)
    total, hours, used = ZERO, ZERO, set()
    lines = (PayrollLine.objects.filter(employment=employment, payroll__status="approved", payroll__year__gte=first.year)
             .select_related("payroll"))
    for ln in lines:
        p = ln.payroll
        if not first <= date(p.year, p.month, 1) <= end:
            continue
        h = Decimal(str(((ln.info or {}).get("timesheet") or {}).get("hours") or 0))
        if not h:
            continue
        hours += h
        used.add((p.year, p.month))
        total += sum((i.amount for i in ln.items.filter(pay_type__in_average=True, pay_type__category="accrual")), ZERO)
    if not hours:
        return None, {"months": 0}
    return q(total / hours), {"months": len(used), "sum": q(total), "hours": float(hours)}


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
    # lunile în regim IT Park: venitul asigurat e 68 % din salariul mediu al lunii, nu salariul (Legea 77/2016, art. 16)
    it_months = it_park.it_park_months(first, end) if employment.kind != "contractor" else set()
    for (y, m) in list(per_month):
        if (y, m) in it_months:
            per_month[(y, m)] = it_park.insured_income(Constants(month_bounds(y, m)[1]))
    n = len(per_month)
    if not n and employment.kind != "contractor" and it_park.is_it_park(year, month):
        fallback_monthly = it_park.insured_income(c)
    monthly = (sum(per_month.values(), ZERO) / n) if n else fallback_monthly
    cap = c("sick_avg_cap_salaries", "5") * c("avg_salary")
    capped = bool(cap) and monthly > cap
    if capped:
        monthly = cap
    f, l = month_bounds(year, month)
    days = (l - f).days + 1
    note = (f"{n} luni" if n else ("fără istoric: venitul asigurat IT Park" if it_park.is_it_park(year, month)
                                    and employment.kind != "contractor" else "fără istoric: salariul lunii")) \
        + f", {q(monthly)} lei / {days} zile" + (f", plafonul {num(cap)} lei" if capped else "") \
        + ("; lunile IT Park — venitul asigurat" if it_months & set(per_month) else "")
    return q(monthly / days), {"months": n, "monthly": q(monthly), "days": days, "note": note}


# --- baza minimă CAS (Legea 489/1999, art. 22 alin. (1)) ---------------------------------------------------------------
def cas_minimum(calcs: list, c) -> None:
    """Baza CAS a salariatului (toate raporturile lui de muncă din calcul, fără contractele de prestări servicii) nu poate fi
    mai mică decât salariul minim proporțional timpului lucrat; la timp parțial (norma totală sub 1) CAS nu poate fi mai mică
    de `cas_min_part_pct` % din CAS-ul pe salariul minim. Fără timp lucrat în lună (concediu neplătit, de îngrijire a
    copilului, boală plătită de CNAS toată luna) — fără bază minimă. Diferența: rândul „CAS pe diferența până la baza
    minimă” pe raportul de bază, cu baza reală și baza minimă în explicație."""
    jobs = [x for x in calcs if x.job.kind != "contractor"]
    if not jobs or any(x.it_park for x in jobs):  # IT Park: CAS e cuprinsă în impozitul unic (CF art. 372 alin. (1))
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
        self._index()
        # pontajul lunii pe raport de muncă: un raport în două tabele (transfer în lună) — totalurile adunate, zilele unite
        self.timesheets, self.ts_days = {}, defaultdict(dict)
        for ln in TimesheetLine.objects.filter(timesheet__year=self.year, timesheet__month=self.month, timesheet__deletion_mark=False):
            self.timesheets[ln.employment_id] = worktime.merge_totals(self.timesheets.get(ln.employment_id), ln.totals or {})
            for key, cell in (ln.days or {}).items():
                if Decimal(str(cell.get("h") or 0)) > 0 or key not in self.ts_days[ln.employment_id]:
                    self.ts_days[ln.employment_id][key] = cell
        self.rosters = {r.employment_id: r.days or {} for r in RosterLine.objects.filter(
            roster__year=self.year, roster__month=self.month, roster__deletion_mark=False)}
        self.meals = meal_vouchers.month_lines(self.first, self.last)
        # cursele aprobate cu întoarcerea în lună (S6b): plata pe km și diurna, pe raport de muncă
        self.trips = transport.month_summary(self.first, self.last)
        # orele pe tipuri, tarifele și cumulările (S4b) — pe raport
        self.hour_types = {t.code: t for t in HourType.objects.all()}
        self.guarantee_conf = hour_types.settings()
        self._typed = None
        self.rates = defaultdict(list)
        for r in JobHourRate.objects.filter(date_from__lte=self.last).exclude(date_to__lt=self.first).select_related("hour_type"):
            self.rates[r.employment_id].append(r)
        self.combinations = defaultdict(list)
        for c in (FunctionCombination.objects.filter(date_from__lte=self.last).exclude(date_to__lt=self.first)
                  .select_related("occupation", "hour_type").order_by("date_from", "id")):
            self.combinations[c.employment_id].append(c)
        # lucrările în acord (S5a): rapoartele de producție aprobate ale lunii, pe raport de muncă
        self.production = production.month_summary(self.first, self.last)
        self.avg_salary = self.const("avg_salary")
        self.it_park = it_park.is_it_park(self.year, self.month)  # regimul lunii calculului (CF art. 375)
        self.sick_covered = it_park.sick_covered(self.const)

    def _index(self):
        self.by_auto = defaultdict(list)
        for t in self.types.values():
            if t.formula == "auto" and t.auto != "none":
                self.by_auto[t.auto].append(t)
        self.order = dependencies.calc_order(self.types.values())  # dependența circulară oprește calculul
        self._parsed = {}

    def use_type(self, t: PayType, replaces: str | None = None):
        """Tipul dat (nesalvat, la „Încearcă”) în locul celui din bază — și în ordinea de calcul."""
        if replaces:
            self.types.pop(replaces, None)
        self.types[t.code] = t
        self._index()

    def parsed(self, t: PayType):
        if t.code not in self._parsed:
            self._parsed[t.code] = formula.parse(t.expression)
        return self._parsed[t.code]

    def jobs(self):
        """Raporturile de muncă din lună (toată întreprinderea sau subdiviziunea), cu zilele lor din worktime."""
        if self.payroll.subdivision_id:
            return self.ctx.jobs(self.payroll.subdivision)
        from apps.org.models import Subdivision

        out, seen = [], {}
        for sub in Subdivision.objects.filter(parent__isnull=True):
            for jd in self.ctx.jobs(sub):
                if jd.job.pk not in seen:
                    seen[jd.job.pk] = jd
                    out.append(jd)
                else:  # transferul între subdiviziuni de nivel întâi în lună: același raport, zilele din ambele
                    seen[jd.job.pk].days |= jd.days
        out.sort(key=lambda jd: (jd.job.employee.last_name, jd.job.employee.first_name, jd.job.kind != "main", jd.job.pk))
        return out

    def full_norm(self, jd) -> Decimal:
        """Norma de ore a lunii întregi pentru raport (toate zilele lucrătoare ale lunii, la norma raportului din istoric)."""
        if not hasattr(self, "_full_norms"):
            self._full_norms = {}
        if jd.job.pk not in self._full_norms:
            own = jd.days
            jd.days = set(self.ctx.days)
            try:
                self._full_norms[jd.job.pk] = self.ctx.norm(jd)
            finally:
                jd.days = own
        return self._full_norms[jd.job.pk]

    def typed(self, employment_id) -> dict:
        if self._typed is None:
            self._typed = worktime.typed_by_job(self.year, self.month, TimesheetLine.objects.filter(
                timesheet__year=self.year, timesheet__month=self.month).values_list("employment_id", flat=True))
        return self._typed.get(employment_id, {})

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
        self.norm = Decimal(str(self.ts.get("norm") or 0))  # norma zilelor raportului în lună (pentru suplimentare)
        self.hours = Decimal(str(self.ts.get("hours") or 0))
        # norma lunii întregi la norma raportului: salariul de funcție e pe lună — cine e angajat / eliberat în lună primește
        # partea zilelor lui (orele lucrate / norma lunii întregi), iar salariul pe oră e salariul / norma lunii întregi
        self.month_norm = month.full_norm(jd) or self.norm
        sub_id, occ_id, rate = jd.values_on(max(jd.days))
        self.rate = Decimal(rate)
        rec = next((h for h in reversed(jd.history) if h.date <= max(jd.days)), None)
        # modalitatea de remunerare și tariful orar ale lunii (din istoric, la ultima zi a raportului în lună)
        self.pay_mode = rec.pay_mode if rec else self.job.pay_mode
        self.hourly_rate = Decimal(rec.hourly_rate if rec else self.job.hourly_rate or 0)
        if self.pay_mode in ("hourly", "piece"):  # salariul lunar echivalent: tariful × norma lunii (pentru % din salariu, media)
            # în acord tariful e cel al categoriei muncitorului: din el — suplimentarele și noaptea (CM art. 157, 159)
            self.salary_full = q(self.hourly_rate * self.norm)
            self.hourly = self.hourly_rate
        else:
            self.salary_full = q(self.job.base_salary * self.rate)  # salariul pentru norma raportului
            self.hourly = q(self.salary_full / self.month_norm) if self.month_norm and self.pay_mode != "hour_types" else ZERO
        # orele pe tipuri (instruire, examinare, zbor…) cu orele garantate și plata lor (apps.worktime.hour_types)
        self.hour_summary = hour_types.summarize(month.ctx, jd, month.typed(self.job.pk), month.rates.get(self.job.pk, []),
                                                 month.hour_types, month.guarantee_conf)
        added = hour_types.added_hours(self.hour_summary)  # tipurile „se adaugă la orele lucrate”
        self.hours += added
        # orele plătite din salariul lunar: cele obișnuite + cele de sărbătoare / repaus în limita normei; suplimentarele și
        # orele de sărbătoare peste normă se plătesc separat (SUPL, SARB), întregi
        ts = self.ts
        self.salary_hours = ((self._d("regular") + self._d("holiday_in_norm")) if "regular" in ts else self.hours - added) + added
        if self.norm:
            self.worked_share = min(self.salary_hours, self.norm) / self.month_norm
        else:
            self.worked_share = ZERO if self.job.kind == "contractor" else Decimal("1")
        # evidența globală (CM art. 99): în lunile perioadei salariul se plătește pentru norma lunii fără zilele de absență
        # (orele graficului peste / sub normă se socotesc la sfârșitul perioadei — suplimentarele din pontaj)
        self.summarized = ts.get("summarized")
        if self.summarized and self.norm:
            present = max(self.norm - self._d("norm_absent"), ZERO)
            self.worked_share = present / self.month_norm
        # lucrările în acord ale lunii și îndeplinirea normei (din orele rapoartelor sau din pontaj)
        self.piece = month.production.get(self.job.pk)
        self.piece_pct = self.piece_basis = None
        self.piece_source = ""
        if self.piece is not None:
            self.piece_pct, self.piece_basis, self.piece_source = production.fulfillment(self.piece, self.salary_hours)
        occ, sub = month.ctx.occupations.get(occ_id), month.ctx.subdivisions.get(sub_id)
        self.info = {"occupation": occ.name_ro if occ else "", "subdivision": sub.name_ro if sub else "", "kind": self.job.kind,
                     "kind_label": self.job.get_kind_display(), "rate": float(self.rate), "base_salary": float(self.job.base_salary),
                     "salary_full": float(self.salary_full), "hourly": float(self.hourly), "timesheet": self.ts,
                     "tab_number": self.job.employee.tab_number, "name": self.job.employee.full_name(), "is_main": is_main,
                     "pay_mode": self.pay_mode, "hourly_rate": float(self.hourly_rate),
                     "hour_types": self.hour_summary, "month_norm": float(self.month_norm)}
        if self.summarized:
            self.info["summarized"] = self.summarized
        if self.piece is not None:
            self.info["production"] = {"amount": float(self.piece.amount), "progressive": float(self.piece.progressive),
                                       "normed_hours": float(self.piece.normed_hours), "hours": float(self.piece_basis or 0),
                                       "hours_source": self.piece_source,
                                       "fulfillment": float(q(self.piece_pct)) if self.piece_pct is not None else None}
        self.traces: list = []  # formulele calculate: variabilele, rezultatul (pentru „Încearcă”)
        self.try_mode = False  # la „Încearcă” erorile formulei se arată, nu opresc calculul
        self.forced_rows: dict = {}  # {codul tipului: [rânduri]} — la „Încearcă”, în locul rândurilor angajatului
        self._seniority = None
        # IT Park: salariul din CIM e impozitat final; contractul de prestări servicii rămâne în regimul general
        self.it_park = month.it_park and self.job.kind != "contractor"
        if self.it_park:
            self.info["it_park"] = True
            self.info["regime_note"] = it_park.FINAL_NOTE

    def _d(self, key) -> Decimal:
        return Decimal(str(self.ts.get(key) or 0))

    def add(self, code: str, amount, quantity=None, base=None, percent=None, note="", manual=False, keep_zero=False):
        t = self.m.types.get(code)
        if t is None or (q(amount) == ZERO and not keep_zero):
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
        hourly_paid = self.pay_mode == "hourly"
        # tariful orar și acordul plătesc deja ora lucrată: la suplimentare / sărbători se adaugă doar sporul
        increment_only = self.pay_mode in ("hourly", "piece")
        for t in m.by_auto["salary"]:
            if self.job.kind == "contractor" or self.pay_mode in ("hour_types", "piece"):
                continue
            if hourly_paid:  # tariful orar × toate orele lucrate; sporurile pentru suplimentare / sărbători — peste ora simplă
                self.add(t.code, self.hourly_rate * self.hours, quantity=self.hours, base=self.hourly_rate,
                         note=f"tariful orar {num(self.hourly_rate)} lei × {float(self.hours):g} ore")
            else:
                self.add(t.code, self.salary_full * share, quantity=self.salary_hours, base=self.salary_full,
                         note=f"{float(self.salary_hours):g} ore din norma {float(self.norm):g}" if self.norm else "")
        self._piece()
        self._hour_types()
        for t in m.by_auto["allowance"]:
            if self.job.allowance_pct:
                self.add(t.code, self.salary_full * share * self.job.allowance_pct / 100, base=self.salary_full * share,
                         percent=self.job.allowance_pct)
        self._combinations()
        night = Decimal(str(self.ts.get("night") or 0))
        for t in m.by_auto["night"]:
            if night and self.hourly:
                self.add(t.code, night * self.hourly * c("night_pct") / 100, quantity=night, base=self.hourly, percent=c("night_pct"))
        for t in m.by_auto["holiday"]:
            if self.pay_mode == "piece":
                self._piece_holiday(t.code)
            elif self.hourly:
                self._holiday(t.code, self.hourly, hourly_paid=hourly_paid)
        for t in m.by_auto["overtime"]:
            if self.hourly:
                self._overtime(t.code, self.hourly, full=not increment_only)
        self._leave()
        self._idle()
        self._harmful()
        self._guarantee()
        self._meal_vouchers()
        self._trips()
        if self.is_main:
            self._sick()
            self._incentives()

    def _piece(self):
        """Lucrările în acord din rapoartele de producție aprobate ale lunii (individuale și partea din brigadă): suma lor pe
        raportul de muncă, cu orele normate ca și cantitate; apoi sporul acordului progresiv (ACORDP) pe partea lucrărilor
        marcate „progresiv”, după treptele de îndeplinire a normei ale tipului."""
        s, m = self.piece, self.m
        if s is None or self.job.kind == "contractor":
            return
        pct_text = (f"; îndeplinirea normei {production.fmt(self.piece_pct, 2)} % ({production.fmt(s.normed_hours)} ore normate / "
                    f"{production.fmt(self.piece_basis)} {self.piece_source})" if self.piece_pct is not None else "")
        for t in m.by_auto["piece"][:1]:
            self.add(t.code, s.amount, quantity=s.normed_hours, note=s.note() + pct_text)
        for t in m.by_auto["piece_prog"][:1]:
            if not s.progressive or self.piece_pct is None:
                continue
            extra, how = production.progressive_increment(s.progressive, self.piece_pct, t.scale or [])
            if extra:
                self.add(t.code, extra, base=s.progressive,
                         note=f"lucrările în acord progresiv {production.fmt(s.progressive, 2)} lei, îndeplinirea normei "
                              f"{production.fmt(self.piece_pct, 2)} %: {how}")

    def _guarantee(self):
        """Garanția la neîndeplinirea normei în acord (CM art. 161), pe fiecare raport de producție aprobat cu cauza scrisă:
        din vina angajatorului — cel puțin câștigul mediu pe oră × orele lucrate la raport; fără vina părților — cel puțin
        C.shortfall_nofault_pct % (2/3) din tariful categoriei × orele. Se plătește diferența dintre garanție și câștigul în acord
        al raportului."""
        s, m = self.piece, self.m
        types = m.by_auto["piece_guarantee"]
        if s is None or not s.shortfalls or not types or self.job.kind == "contractor":
            return
        c = m.const
        avg = None
        for x in s.shortfalls:
            hours, earned = x["hours"], x["amount"]
            if not hours or not x["complete"]:
                continue
            if x["cause"] == "employer":
                if avg is None:
                    avg, how = average_hourly(self.job, m.year, m.month, int(c("leave_avg_months", "3")))
                    avg_note = (f"câștigul mediu pe oră {production.fmt(avg, 2)} lei ({how['months']} luni)" if avg is not None
                                else "")
                    if avg is None:
                        avg, avg_note = self.hourly, f"fără istoric: tariful orar {production.fmt(self.hourly, 2)} lei"
                rate, why = avg, f"din vina angajatorului — {avg_note}"
            else:
                pct = c("shortfall_nofault_pct", "66.6667")
                rate = self.hourly * pct / 100
                why = f"fără vina părților — {production.fmt(pct, 2)} % din tariful categoriei {production.fmt(self.hourly, 2)} lei"
            guaranteed = q(rate * hours)
            if guaranteed > earned:
                self.add(types[0].code, guaranteed - earned, quantity=hours, base=rate,
                         note=f"{x['ref']}: {production.fmt(hours)} ore × {production.fmt(rate, 2)} lei = {production.fmt(guaranteed, 2)} lei "
                              f"({why}, CM art. 161), câștigul în acord {production.fmt(earned, 2)} lei")

    def _idle_days(self):
        """Zilele de staționare / șomaj tehnic ale raportului în lună: (ziua, felul, orele planificate, absența). Din celulele
        pontajului (St / Șt, cu orele planificate „ph”), fără pontaj — din ordine (absențele lunii) și graficul de lucru."""
        m, jd = self.m, self.jd
        cells = m.ts_days.get(self.job.pk)
        out = []
        roster = m.rosters.get(self.job.pk)
        for day in sorted(jd.days):
            a = jd.absence(day)
            if a is not None and (a.kind not in IDLE_KINDS or (a.employment_id and a.employment_id != self.job.pk)):
                a = None
            if cells is not None:
                cell = cells.get(str(day.day)) or {}
                code = cell.get("c")
                if code not in worktime.IDLE_CODES:
                    continue
                kind = "idle" if code == "St" else "tech_unemployment"
                hours = (Decimal(str(cell["ph"])) if "ph" in cell
                         else worktime.planned_hours(m.ctx, jd, day, roster))
            elif a is not None:
                kind = a.kind
                hours = worktime.planned_hours(m.ctx, jd, day, roster)
            else:
                continue
            if a is not None and a.kind != kind:
                a = None
            if hours > 0:
                out.append((day, kind, hours, a))
        return out

    def _idle(self):
        """Staționarea (CM art. 80¹) și șomajul tehnic (CM art. 80): orele planificate ale zilelor St / Șt × salariul de bază pe
        oră × procentul — cel din ordin, altfel cel din Constante după cauză (din vina angajatorului 100 %, fără vina părților
        2/3, dar nu sub salariul minim pe oră, din vina salariatului 0; șomajul tehnic 50 %). Zilele fără ordin (codul pus de
        mână în pontaj) — staționarea „fără vina părților”."""
        m, c = self.m, self.m.const
        if self.job.kind == "contractor" or not self.hourly:
            return
        groups = defaultdict(lambda: [ZERO, 0, []])
        for day, kind, hours, a in self._idle_days():
            cause = (a.cause if a is not None and a.cause else "nobody") if kind == "idle" else ""
            pct = a.pay_pct if a is not None and a.pay_pct is not None else None
            ref = (f"ordinul {a.order_item.order.reference()}" if a is not None and a.order_item_id and a.order_item.order.number
                   else ("fără ordin (pontajul)" if a is None else ""))
            g = groups[(kind, cause, pct, ref)]
            g[0] += hours
            g[1] += 1
        if not groups:
            return
        min_hourly = c("min_salary") / c("min_salary_hours", "169") if c("min_salary_hours", "169") else ZERO
        for (kind, cause, pct, ref), (hours, days, _x) in groups.items():
            types = m.by_auto[kind]
            if not types:
                continue
            if pct is None:
                pct = (c("tech_unemployment_pct", "50") if kind == "tech_unemployment"
                       else c({"employer": "idle_employer_pct", "nobody": "idle_nofault_pct", "worker": "idle_worker_pct"}[cause],
                              {"employer": "100", "nobody": "66.6667", "worker": "0"}[cause]))
            rate = self.hourly * pct / 100
            floor = ""
            if kind == "idle" and cause == "nobody" and rate < min_hourly * self.rate:
                rate, floor = min_hourly * self.rate, f", ridicat la salariul minim pe oră {production.fmt(min_hourly, 2)} lei × norma {num(self.rate)}"
            if not rate:
                continue
            label = ("șomaj tehnic (CM art. 80)" if kind == "tech_unemployment" else
                     {"employer": "staționare din vina angajatorului", "nobody": "staționare fără vina părților",
                      "worker": "staționare din vina salariatului"}[cause] + " (CM art. 80¹)")
            self.add(types[0].code, rate * hours, quantity=hours, base=self.hourly, percent=pct,
                     note=f"{label}: {days} zile, {production.fmt(hours)} ore × {production.fmt(self.hourly, 2)} lei × "
                          f"{production.fmt(pct, 2)} %{floor}" + (f"; {ref}" if ref else ""))

    def _harmful_hours(self) -> dict:
        """Orele lucrate în condiții vătămătoare pe procent: ziua în subdiviziunea / funcția cu sporul (procentul mai mare
        dintre ele), din pontaj; fără pontaj — orele planificate ale zilelor fără absență."""
        m, jd = self.m, self.jd
        cells = m.ts_days.get(self.job.pk)
        roster = m.rosters.get(self.job.pk)
        out = defaultdict(lambda: ZERO)
        for day in sorted(jd.days):
            sub_id, occ_id, _rate = jd.values_on(day)
            sub, occ = m.ctx.subdivisions.get(sub_id), m.ctx.occupations.get(occ_id)
            pct = max((x.harmful_pct for x in (sub, occ) if x is not None and x.harmful and x.harmful_pct), default=ZERO)
            if not pct:
                continue
            if cells is not None:
                hours = Decimal(str((cells.get(str(day.day)) or {}).get("h") or 0))
            elif jd.absence(day) is None and not jd.is_suspended(day):
                hours = worktime.planned_hours(m.ctx, jd, day, roster)
            else:
                hours = ZERO
            if hours > 0:
                out[pct] += hours
        return out

    def _harmful(self):
        """Sporul pentru condiții vătămătoare (CM art. 139; mărimea — din contractul colectiv, scrisă la subdiviziune / funcție):
        salariul de bază pe oră × orele lucrate în aceste condiții × procentul. Rândul personal NOCIV (spor stabilit
        individual) îl înlocuiește."""
        m = self.m
        types = m.by_auto["harmful"]
        if not types or self.job.kind == "contractor" or not self.hourly:
            return
        if self.rows().get("NOCIV"):
            return
        for pct, hours in sorted(self._harmful_hours().items()):
            self.add(types[0].code, self.hourly * hours * pct / 100, quantity=hours, base=self.hourly, percent=pct,
                     note=f"{production.fmt(hours)} ore în condiții vătămătoare × {production.fmt(self.hourly, 2)} lei × "
                          f"{production.fmt(pct, 2)} % (subdiviziunea / funcția)")

    def _trips(self):
        """Cursele aprobate ale lunii (întoarcerea în lună): plata pe km (km × tariful fixat la aprobare, fiecărui șofer al
        cursei), diurna în limita normelor (neimpozabilă, fără CAS / CNAM) și partea peste norme (impozabilă)."""
        s = self.m.trips.get(self.job.pk)
        if s is None or self.job.kind == "contractor":
            return
        for t in self.m.by_auto["trip_km"][:1]:
            self.add(t.code, s.km_amount, quantity=s.km, note=s.km_note())
        for t in self.m.by_auto["per_diem"][:1]:
            self.add(t.code, s.per_diem, quantity=s.days, note=f"diurna din {len(s.refs)} curse, în limita normelor (HG 10/2012)")
        for t in self.m.by_auto["per_diem_excess"][:1]:
            self.add(t.code, s.per_diem_taxable, note="diurna peste normele HG 10/2012 — venit impozabil (CF art. 20)")

    def _meal_vouchers(self):
        """Tichetele de masă din borderourile aprobate cu data în lună: partea peste valoarea neimpozabilă (facilitate
        impozabilă, CF art. 19 lit. a¹)) — acumularea, și reținerea ei (tichetele sunt deja pe card)."""
        m = self.m
        for ln in m.meals.get(self.job.pk, []):
            if not ln.taxable:
                continue
            doc = ln.voucher_list
            note = (f"borderoul {doc.reference()}, luna {doc.month:02d}.{doc.year}: {ln.count} tichete × "
                    f"({production.fmt(doc.value, 2)} − {production.fmt(doc.cap, 2)}) lei peste valoarea neimpozabilă")
            for t in m.by_auto["meal_voucher"][:1]:
                self.add(t.code, ln.taxable, quantity=ln.count, base=doc.value - doc.cap, note=note)
            for t in m.by_auto["meal_voucher_offset"][:1]:
                self.add(t.code, ln.taxable, quantity=ln.count,
                         note=f"partea impozabilă a tichetelor de masă, acordată în natură (borderoul {doc.reference()})")

    def _piece_holiday(self, code):
        """În acord, munca în zilele de sărbătoare / repaus se plătește cel puțin cu dublul tarifelor în acord (CM art. 158):
        acordul a plătit-o o dată, se adaugă sporul (C.holiday_hourly_pct − 100) % pe câștigul în acord pe oră al lunii (suma
        acordului / orele lui); fără câștig în acord — pe tariful orar al categoriei."""
        c = self.m.const
        hours = self._d("holiday") + self._d("rest_work")
        pct = c("holiday_hourly_pct", "200") - 100
        if not hours or pct <= 0:
            return
        s = self.piece
        if s is not None and s.amount and self.piece_basis:
            hourly = s.amount / self.piece_basis
            how = f"câștigul în acord pe oră {production.fmt(hourly, 2)} lei ({production.fmt(s.amount, 2)} lei / {production.fmt(self.piece_basis)} ore)"
        elif self.hourly:
            hourly, how = self.hourly, f"tariful orar al categoriei {production.fmt(self.hourly, 2)} lei"
        else:
            return
        self.add(code, hourly * hours * pct / 100, quantity=hours, base=hourly, percent=pct,
                 note=f"{float(hours):g} ore × {how} × {num(pct)} % (dublul tarifelor în acord, CM art. 158)")

    def _hour_types(self):
        """Orele pe tipuri cu tarif (la modalitățile „pe tipuri de ore” și „mixt”): ore plătite × tariful, unde ore plătite =
        max(efective, garantate reduse după zilele disponibile); un rând pe tip de ore (cu tariful schimbat în lună — suma
        rândurilor de tarif, explicate în observații), cu tipul de calcul legat în clasificatorul tipurilor de ore sau „Ore pe
        tipuri”. Orele acestea nu intră în tariful orar pentru noapte / sărbători / suplimentare (acelea se socotesc din orele
        standard ale pontajului)."""
        if self.pay_mode not in RATE_MODES or self.job.kind == "contractor":
            return
        default = self.m.by_auto["hour_types"]
        by_pk = {t.pk: t for t in self.m.types.values()}
        for code, s in self.hour_summary.items():
            linked = by_pk.get(s["pay_type"]) if s["pay_type"] else None
            pay = linked if linked is not None and linked.auto == "hour_types" else (default[0] if default else None)
            if pay is None:
                continue
            if not s["amount"]:
                continue
            paid = sum((Decimal(str(row["paid"])) for row in s["rows"]), ZERO)
            single = len(s["rows"]) == 1
            self.add(pay.code, Decimal(str(s["amount"])), quantity=paid, base=Decimal(str(s["rate"])) if single else None,
                     note=f"{code}: {s['note']}")

    def _combinations(self):
        """Cumularea funcțiilor, suplinirea, interimatul pe același contract (CM art. 156) — înregistrările de pe raport:
        % din salariul propriu × partea lucrată × zilele în vigoare; % din salariul funcției cumulate / suplinite (la fel);
        suma fixă × zilele în vigoare; pe ore — orele tipului ales × tariful. Zilele în vigoare: zilele lucrătoare ale
        cumulării din zilele lucrătoare ale raportului în lună."""
        m = self.m
        types = m.by_auto["combination"]
        recs = m.combinations.get(self.job.pk, [])
        if not types or not recs:
            return
        cal = m.ctx.cal
        job_days = [d for d in m.ctx.days if cal.is_working(d) and self.jd.active(d)]
        for rec in recs:
            mine = [d for d in job_days if rec.date_from <= d and (rec.date_to is None or d <= rec.date_to)]
            label = f"{rec.get_kind_display()}: {rec.occupation.name_ro}"
            period = (Decimal(len(mine)) / len(job_days)) if job_days else ZERO
            days_text = f"zilele {len(mine)} / {len(job_days)}"
            if rec.pay_mode == "hourly":
                code = rec.hour_type.code if rec.hour_type_id else ""
                hours = Decimal(str((self.hour_summary.get(code) or {}).get("hours") or 0))
                if hours:
                    self.add(types[0].code, hours * rec.value, quantity=hours, base=rec.value,
                             note=f"{label} — {code} {hour_types.fmt(hours)} ore × {hour_types.fmt(rec.value, True)} lei")
                continue
            if not mine:
                continue
            if rec.pay_mode == "fixed":
                self.add(types[0].code, rec.value * period, base=rec.value,
                         note=f"{label} — {hour_types.fmt(rec.value, True)} lei × {days_text}")
                continue
            own = rec.pay_mode == "pct_own"
            salary = self.salary_full if own else Decimal(rec.other_salary or 0)
            base = salary * self.worked_share * period
            self.add(types[0].code, base * rec.value / 100, base=base, percent=rec.value,
                     note=f"{label} — {num(rec.value)} % din salariul {'propriu' if own else 'funcției'} {hour_types.fmt(salary, True)} × "
                          f"partea lucrată {float(self.worked_share) * 100:.4g} % × {days_text}")

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
        monthly = self.fallback_monthly()
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
            avg, how = sick_average_daily(self.job, m.year, m.month, c, self.fallback_monthly())
            for t in m.by_auto[auto]:
                self.add(t.code, avg * days_left * pct / 100, quantity=days_left, base=avg, percent=pct,
                         note=f"{num(pct)}% din media {avg} lei/zi ({how['note']}); {codes}")

    def fallback_monthly(self) -> Decimal:
        """Câștigul lunar fără istoric (pentru media concediului / bolii): salariul cu sporurile fixe; la „pe tipuri de ore” și
        „mixt” — plus garanția lunii × tariful fiecărui tip."""
        monthly = self.salary_full * (Decimal(1) + (self.job.allowance_pct or ZERO) / 100)
        if self.pay_mode in RATE_MODES:
            for r in self.m.rates.get(self.job.pk, []):
                if r.guaranteed_hours and r.in_force(self.m.last, self.m.last):
                    monthly += r.guaranteed_hours * r.rate
        return monthly

    def _incentives(self):
        m = self.m
        for inc in Incentive.objects.filter(employee=self.job.employee, date__gte=m.first, date__lte=m.last).select_related("kind"):
            kind = inc.kind.code if inc.kind_id else "bonus"
            amount = inc.amount if inc.amount is not None else (self.salary_full * (inc.percent or 0) / 100)
            note = inc.note or (f"ordinul {inc.order_item.order.reference()}" if inc.order_item_id else "")
            for t in m.by_auto["aid" if kind == "aid" else "bonus"]:
                self.add(t.code, amount, base=self.salary_full if inc.amount is None else None, percent=inc.percent, note=note)

    # -- rândurile de mână, apoi tipurile dependente --
    def run(self, manual_items):
        self.auto()
        overridden = self.apply_manual(manual_items)
        self.minimum_completion(overridden)
        self.dependents(overridden)
        self.bases(manual_items)

    def apply_manual(self, manual_items) -> set:
        """Rândul de mână înlocuiește rândul calculat de același tip; intră în calcul înaintea tipurilor care depind de el."""
        overridden = {it["type"].pk for it in manual_items}
        self.items = [i for i in self.items if i["type"].pk not in overridden] + list(manual_items)
        return overridden

    def rows(self) -> dict:
        """Rândurile personale valabile în lună pe acest raport (cele fără raport — pe cel de bază), pe codul tipului."""
        m, out = self.m, defaultdict(list)
        qs = (EmployeePayItem.objects.filter(employee=self.job.employee, date_from__lte=m.last)
              .filter(Q(date_to__isnull=True) | Q(date_to__gte=m.first)).select_related("pay_type").order_by("date_from", "id"))
        for r in qs:
            if r.employment_id and r.employment_id != self.job.pk:
                continue
            if not r.employment_id and not self.is_main:
                continue
            out[r.pay_type.code].append(r)
        return out

    def dependents(self, overridden):
        """Tipurile care nu sunt automate, în ordinea dependențelor: pe fiecare rând al angajatului; tipurile „pentru toți
        angajații” (formula, treptele, procentele tipului) — și fără rând, o dată pe raport (nu la contractul de prestări
        servicii)."""
        rows = self.rows()
        for code, forced in self.forced_rows.items():
            rows[code] = forced
        for t in self.m.order:
            if t.pk is not None and t.pk in overridden:
                continue
            own = rows.get(t.code) or []
            if not own and t.applies_to == "all" and t.formula in PayType.GENERAL_FORMULAS and self.job.kind != "contractor":
                own = [None]
            for r in own:
                self.compute(t, r)

    def seniority_years(self, which: str) -> Decimal:
        if self._seniority is None:
            self._seniority = staff.seniority(self.job.employee, self.m.last)
        return Decimal(self._seniority[which]["years"])

    def compute(self, t: PayType, r):
        m = self.m
        pct = r.percent if r is not None and r.percent is not None else t.percent
        doc = r.document if r is not None else ""
        if t.formula == "pct_salary":
            base = self.salary_full * self.worked_share
            self.add(t.code, base * pct / 100, base=base, percent=pct, note=doc)
        elif t.formula == "pct_base":
            base = self.sum_codes(t.base_codes)
            self.add(t.code, base * pct / 100, base=base, percent=pct, note=doc)
        elif t.formula == "hourly":
            if r is None:
                return
            rate = r.amount or ZERO
            self.add(t.code, rate * self.hours, quantity=self.hours, base=r.amount, note=doc)
            if rate:  # tariful pe oră: sporul pentru suplimentare și dublul în zilele de sărbătoare / repaus
                for x in m.by_auto["overtime"]:
                    self._overtime(x.code, rate, full=False)
                for x in m.by_auto["holiday"]:
                    self._holiday(x.code, rate, hourly_paid=True)
        elif t.formula == "scale":
            self._scale(t, doc)
        elif t.formula == "expr":
            self._expr(t, r, pct)
        elif r is not None:  # suma fixă
            self.add(t.code, r.amount or ZERO, note=doc)

    def _scale(self, t: PayType, doc=""):
        """Treptele de vechime: procentul treptei atinse de vechimea totală în muncă la sfârșitul lunii
        (trepte {"from": ani, "pct": %}, din contractul colectiv / regulamentul de salarizare al întreprinderii)."""
        if t.category != "accrual" or not t.scale:
            return
        years = self.seniority_years("total")
        pct = None
        for threshold, p in sorted((Decimal(str(s["from"])), Decimal(str(s["pct"]))) for s in t.scale if "from" in s):
            if years >= threshold:
                pct = p
        if pct:
            base = self.sum_codes(t.base_codes or ["SAL"])
            self.add(t.code, base * pct / 100, base=base, percent=pct, note=doc)

    def variable(self, name: str, t: PayType, r, pct) -> Decimal:
        """Valoarea unei variabile a formulei (apps.payroll.formula.VARIABLES) pentru acest raport de muncă."""
        d, ts = self._d, self.ts
        simple = {
            "SalariuFunctie": lambda: self.salary_full, "Norma": lambda: self.norm, "OreLucrate": lambda: self.hours,
            "ZileLucrate": lambda: d("days"), "TarifOrar": lambda: self.hourly, "ParteLucrata": lambda: self.worked_share,
            "ZileNorma": lambda: Decimal(sum(1 for day in self.jd.days if self.m.ctx.cal.is_working(day))),
            "OreNoapte": lambda: d("night"), "OreSarbatoare": lambda: d("holiday") + d("rest_work"),
            "OreOdihna": lambda: d("rest_work"),
            "OreSarbatoareInNorma": lambda: d("holiday_in_norm") if "holiday_in_norm" in ts else d("holiday") + d("rest_work"),
            "OreSarbatoarePesteNorma": lambda: d("holiday_over_norm"),
            "OreSuplim2": lambda: d("overtime_2") if "overtime_2" in ts else d("overtime"),
            "OreSuplimPeste": lambda: d("overtime_over"),
            "Suma": lambda: (r.amount if r is not None and r.amount is not None else ZERO),
            "Procent": lambda: Decimal(pct or 0),
            "Cantitate": lambda: (r.quantity if r is not None and r.quantity is not None else ZERO),
            "Baza": lambda: self.sum_codes(t.base_codes or []),
            "SalariuMinim": lambda: self.m.const("min_salary"), "SalariuMediu": lambda: self.m.const("avg_salary"),
            "NormaRaport": lambda: self.rate,
            "VechimeAni": lambda: self.seniority_years("total"),
            "VechimeIntreprindereAni": lambda: self.seniority_years("institution"),
            "OreNormate": lambda: self.piece.normed_hours if self.piece is not None else ZERO,
            "OreAcord": lambda: self.piece_basis or ZERO,
            "IndeplinireNorma": lambda: q(self.piece_pct) if self.piece_pct is not None else ZERO,
        }
        if name not in simple:
            raise formula.FormulaError(f"Variabila „{name}” nu există")
        return Decimal(simple[name]())

    def hour_value(self, kind: str, code: str) -> Decimal:
        """`Ore.COD` (efective), `OrePlatite.COD`, `Garantat.COD` (garanția redusă a lunii), `Tarif.COD` (tariful în vigoare la
        sfârșitul lunii) — 0 dacă raportul n-are ore / tarif de acest tip."""
        if code not in self.m.hour_types:
            raise formula.FormulaError(f"Tipul de ore „{code}” nu există")
        s = self.hour_summary.get(code)
        if s is None:
            return ZERO
        value = {"ore": s["hours"], "ore_platite": s["paid"], "garantat": s["guaranteed"] or 0, "tarif": s["rate"] or 0}[kind]
        return Decimal(str(value))

    def _expr(self, t: PayType, r, pct):
        """Formula tipului: rezultatul pe rând, cu explicația (formula și valorile variabilelor folosite). Un rezultat negativ
        se oprește la 0, cu avertisment (o acumulare / reținere nu poate fi negativă)."""
        m = self.m

        def resolve(kind, name):
            if kind == "var":
                return self.variable(name, t, r, pct)
            if kind in formula.HOUR_KINDS:
                return self.hour_value(kind, name)
            if kind == "const":
                if name not in m.const.values:
                    raise formula.FormulaError(f"Constanta C.{name} nu are valoare la {m.last:%d.%m.%Y}")
                return m.const.values[name]
            return self.sum_codes([name])

        trace = {"code": t.code, "name": t.name_ro, "row": getattr(r, "pk", None), "expression": t.expression}
        try:
            res = formula.evaluate(m.parsed(t), resolve)
        except formula.FormulaError as exc:
            if self.try_mode:
                self.traces.append({**trace, "error": exc.text(), "variables": {}, "result": None, "note": ""})
                return
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": f"Tipul {t.code} ({t.name_ro}), {self.job.employee.full_name()}: {exc.text()}"}) from None
        value = q(res.value)
        note = res.explanation
        negative = value < 0
        if negative:
            note = f"formula a dat {formula.fmt(value)} — se ia 0; {note}"
            value = ZERO
        if r is not None and r.document:
            note = f"{note}; {r.document}"
        used = res.used
        self.add(t.code, value, quantity=used.get("Cantitate"), base=used.get("Baza"), percent=used.get("Procent"), note=note,
                 keep_zero=negative)
        self.traces.append({**trace, "error": "", "variables": used, "result": value, "note": note[:300], "negative": negative})

    # -- bazele, reținerile, CAS --
    def bases(self, manual_items):
        m, c = self.m, self.m.const
        cas_fixed = [it["amount"] for it in manual_items if it["type"].auto == "cas"]  # CAS scris de mână: suma lui
        self.cas_manual = bool(cas_fixed)
        gross = tax_base = cnam_base = cas_base = ZERO
        for i in self.items:
            t, amount = i["type"], i["amount"]
            if t.category != "accrual":
                continue
            gross += amount
            if self.it_park and not (t.auto in ("sick", "sick_accident") and not m.sick_covered):
                i["taxable_part"] = ZERO  # impozitat final: fără impozit, CNAM și CAS (CF art. 372 alin. (1), art. 377)
                continue
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
        if self.it_park:
            cas_base = ZERO  # CAS e cuprinsă în impozitul unic; venitul asigurat e cel din Legea 77/2016 (IPC21)
        cas = sum(cas_fixed, ZERO) if cas_fixed else q(cas_base * c("cas_employer_pct") / 100)
        for t in m.by_auto["cas"]:
            if not cas_fixed:
                self.add(t.code, cas, base=cas_base, percent=c("cas_employer_pct"))
        ln = self.line
        ln.gross, ln.taxable, ln.cnam_base, ln.cas, ln.deductions = q(gross), q(tax_base), q(cnam_base), cas, q(deductions)
        ln.it_park = self.it_park
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
        # salariul tarifar al timpului lucrat: salariul de funcție / tariful orar, plata orelor pe tipuri, lucrările în acord și
        # garanția lor (nu sporurile, nici sporul acordului progresiv)
        paid = sum((i["amount"] for i in self.items if i["type"].auto in ("salary", "hour_types", "piece", "piece_guarantee",
                                                                          "trip_km")), ZERO)
        if target > paid:
            self.add(types[0].code, target - paid, base=target,
                     note=f"salariul minim {num(minimum)} × norma {num(self.rate)} × {float(self.worked_share) * 100:.4g} % lucrat = {target}; "
                          f"salariul de funcție {q(paid)}")


TOTALS = ("gross", "taxable", "cnam_base", "cas", "deductions", "net")


def main_jobs(jobs) -> dict:
    """Raportul „principal” al fiecărei persoane în lună (boala, premiile, rândurile fără raport merg acolo): cel de bază,
    altfel primul (de ex. singurul raport e un cumul extern)."""
    main_of = {}
    for jd in jobs:
        emp_id = jd.job.employee_id
        if emp_id not in main_of or (jd.job.kind in MAIN_KINDS and main_of[emp_id].kind not in MAIN_KINDS):
            main_of[emp_id] = jd.job
    return main_of


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
    jobs = m.jobs()
    if employee_id is not None:
        jobs = [jd for jd in jobs if jd.job.employee_id == employee_id]
    order = {jd.job.pk: n for n, jd in enumerate(m.jobs(), start=1)} if employee_id is not None else None
    main_of = main_jobs(jobs)
    calcs = []
    for n, jd in enumerate(jobs, start=1):
        line = existing.pop(jd.job.pk, None) or PayrollLine(payroll=payroll, employee=jd.job.employee, employment=jd.job)
        line.sort = (order[jd.job.pk] if order else n) * 10
        if line.pk is None:
            line.save()
        manual = [{"type": i.pay_type, "amount": i.amount, "quantity": i.quantity, "base": i.base, "percent": i.percent,
                   "note": i.note, "manual": True} for i in line.items.filter(manual=True).exclude(pay_type__auto__in=AT_PAYMENT).select_related("pay_type")]
        calc = LineCalc(m, jd, line, is_main=main_of[jd.job.employee_id].pk == jd.job.pk)
        calc.run(manual)
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


def try_type(pay_type: PayType, *, employee, year: int, month: int, employment=None, row_values=None, replaces=None) -> dict:
    """„Încearcă pe un angajat”: calculul lunii pentru angajat cu tipul dat (salvat sau doar scris în editor), în memorie —
    nimic nu se salvează (și, pentru siguranță, tranzacția se anulează la sfârșit). Întoarce, pe fiecare raport de muncă,
    variabilele formulei cu valorile lor, rezultatul, explicația și erorile. `row_values` = {amount, percent, quantity} —
    rândul angajatului închipuit (fără el: rândurile lui; dacă n-are, un rând gol, ca formula să se poată încerca)."""
    from rest_framework.exceptions import ValidationError

    with transaction.atomic():
        payroll = Payroll(year=year, month=month)
        m = Month(payroll)
        m.use_type(pay_type, replaces=replaces)
        all_jobs = [jd for jd in m.jobs() if jd.job.employee_id == employee.pk]
        jobs = [jd for jd in all_jobs if employment is None or jd.job.pk == employment.pk]
        if not jobs:
            raise ValidationError({"employee": f"{employee.full_name()} nu are raport de muncă în luna {month:02d}.{year}."})
        main_of = main_jobs(all_jobs)
        out = []
        for jd in jobs:
            line = PayrollLine(payroll=payroll, employee=employee, employment=jd.job)
            calc = LineCalc(m, jd, line, is_main=main_of[employee.pk].pk == jd.job.pk)
            calc.try_mode = True

            def synth(values):
                return EmployeePayItem(employee=employee, employment=jd.job, pay_type=pay_type, date_from=m.first,
                                       amount=values.get("amount"), percent=values.get("percent"), quantity=values.get("quantity"))

            if row_values is not None:
                calc.forced_rows = {pay_type.code: [synth(row_values)]}
            else:
                own = calc.rows().get(replaces or pay_type.code, [])
                if own or pay_type.applies_to != "all" or pay_type.formula not in PayType.GENERAL_FORMULAS:
                    calc.forced_rows = {pay_type.code: own or [synth({})]}
                else:
                    calc.forced_rows = {pay_type.code: []}
            error = ""
            try:
                calc.run([])
            except ValidationError as exc:
                error = str(exc.detail.get("detail", exc.detail) if isinstance(exc.detail, dict) else exc.detail)
            mine = [i for i in calc.items if i["type"].code == pay_type.code]
            traces = [tr for tr in calc.traces if tr["code"] == pay_type.code]
            out.append({
                "employment": jd.job.pk, "employment_label": f"{jd.job.get_kind_display()}: {jd.job.occupation.name_ro}",
                "result": sum((i["amount"] for i in mine), ZERO), "notes": [i["note"] for i in mine if i["note"]],
                "traces": traces, "error": error or "; ".join(tr["error"] for tr in traces if tr.get("error")),
                "items": [{"code": i["type"].code, "name": i["type"].name_ro, "category": i["type"].category, "amount": i["amount"],
                           "note": i["note"]} for i in calc.items],
                "gross": calc.line.gross, "deductions": calc.line.deductions,
            })
        transaction.set_rollback(True)
    return {"employee": employee.pk, "employee_name": employee.full_name(), "year": year, "month": month, "lines": out}
