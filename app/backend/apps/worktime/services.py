"""Timpul de muncă: calendarul de producție și norma lunară, tura planificată pe zi, graficul lunar și tabela de pontaj.

Ziua unui raport de muncă se socotește așa (de la cel mai „tare” la cel mai „slab”):
1. celula scrisă de mână în pontaj (rămâne la recalculare);
2. absența angajatului (concediu, boală, delegare — din ordine și foi de boală) → codul ei (C, Cm, D...);
3. contractul suspendat → „Sp”;
4. tura din graficul de ture al subdiviziunii (graficul lunar), dacă există;
5. tura din graficul de lucru al raportului (săptămânal sau ciclic); fără grafic — 5 zile × (orele săptămânale / 5);
6. ziua fără tură → „R” (repaus) sau „Sn” (sărbătoare nelucrătoare).

Notațiile din pontaj sunt cele din modelul tabelului de evidență a timpului de muncă aprobat prin Convenția colectivă
(nivel național) nr. 17 din 28.02.2020 (MO nr. 70-74/2020, art. 241), pentru CM art. 106.

Graficul săptămânal se micșorează după normă (0,5 normă din „5 × 8” = 4 ore pe zi); graficul pe ture nu — la cumul se pun
mai puține ture în graficul lunar.
"""
import calendar as pycal
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.core.models import SystemSetting
from apps.leave.models import IDLE_KINDS, WITHOUT_HOLIDAYS, Absence
from apps.org import calendar as holidays
from apps.org.models import Subdivision
from apps.staff.models import Employment

from .models import CalendarDay, JobSchedule, Roster, RosterLine, ShiftType, Timesheet, TimesheetLine

# codurile absențelor în pontaj (după tipul absenței din dosar) — notațiile Convenției colective nr. 17/2020
ABSENCE_CODES = {
    "annual": "C", "extra": "C", "unpaid": "Cn", "maternity": "Cc", "paternity": "Cc", "childcare": "Cc",
    "childcare_unpaid": "Cc", "study": "Cs", "days_off": "Ls", "travel": "D", "training": "F", "sick": "Cm",
    "idle": "St", "tech_unemployment": "Șt",
}
SUSPENDED, REST, HOLIDAY = "Sp", "R", "Sn"
CODE_LABELS = {
    "R": "Zile de repaus (odihnă)", "Sn": "Zile de sărbătoare nelucrătoare", "Ls": "Zile libere cu menținerea salariului",
    "C": "Concediu plătit", "Cn": "Concediu neplătit", "Cs": "Concediu de studii", "Cm": "Concediu medical",
    "Cc": "Concediu de maternitate, pentru îngrijirea copilului, paternal", "D": "Deplasare",
    "Sp": "Suspendarea contractului individual de muncă", "Șt": "Șomaj tehnic", "St": "Staționare", "Dt": "Detașare",
    "A": "Absențe",
    # nu e în modelul Convenției nr. 17/2020 (acolo formarea cu menținerea salariului nu are notație proprie)
    "F": "Formare profesională (notație proprie)",
}
# codurile care se pun de mână (celelalte vin din ordine, foi de boală și grafic)
MANUAL_CODES = ["A", "Șt", "St", "Dt", "R", "Sn"]
SETTINGS_KEY = "worktime_settings"
# min_rest_hours — odihna minimă între ture; oricum cel puțin dublul turei anterioare (CM art. 101 alin. (6));
# max_night_shifts — câte ture de noapte pe lună (0 = fără limită)
DEFAULTS = {"min_rest_hours": 12, "max_night_shifts": 0}
ONE = Decimal("1")


def get_settings() -> dict:
    return {**DEFAULTS, **(SystemSetting.read(SETTINGS_KEY, {}) or {})}


def _q(value) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def month_days(year: int, month: int) -> list:
    if not (1 <= month <= 12):
        raise ValidationError({"month": "Luna este între 1 și 12."})
    return [date(year, month, d) for d in range(1, pycal.monthrange(year, month)[1] + 1)]


def fmt_hours(value) -> str:
    return format(Decimal(str(value)).normalize(), "f").replace(".", ",")


# --- calendarul de producție -------------------------------------------------------------------------------------
class Calendar:
    """Sărbătorile și abaterile (zile transferate, scurtate) pe o perioadă."""

    def __init__(self, start: date, end: date):
        self.holidays = holidays.holidays_between(start, end)
        self.overrides = {c.date: c for c in CalendarDay.objects.filter(date__gte=start, date__lte=end)}

    def is_working(self, day: date) -> bool:
        if day in self.overrides:
            return self.overrides[day].working
        return day.weekday() < 5 and day not in self.holidays

    def hours_less(self, day: date) -> Decimal:
        o = self.overrides.get(day)
        return o.hours_less if o else Decimal("0")

    def is_holiday(self, day: date) -> bool:
        return day in self.holidays


def month_norms(year: int) -> list:
    """Calendarul pe an: zilele lucrătoare și norma de ore pe lună pentru 40, 35 și 30 de ore pe săptămână."""
    cal = Calendar(date(year, 1, 1), date(year, 12, 31))
    out = []
    for m in range(1, 13):
        days = [d for d in month_days(year, m) if cal.is_working(d)]
        less = sum((cal.hours_less(d) for d in days), Decimal("0"))
        out.append({"month": m, "working_days": len(days), "calendar_days": len(month_days(year, m)),
                    "holidays": sorted(d for d in cal.holidays if d.month == m and d.year == year),
                    **{f"norm_{h}": _q(Decimal(h) / 5 * len(days) - less) for h in (40, 35, 30)}})
    return out


# --- raportul de muncă pe zile -----------------------------------------------------------------------------------
class JobDays:
    """Ce știm despre un raport de muncă în lună: activ, subdiviziunea și norma pe zile, graficul, absențele."""

    def __init__(self, job: Employment, days: list, absences: list):
        self.job = job
        self.history = sorted(job.history.all(), key=lambda h: (h.date, h.pk))
        self.schedules = sorted(job.work_schedules.all(), key=lambda s: (s.date_from, s.pk))
        self.absences = absences
        self.suspended = self._suspensions(days[-1])

    def values_on(self, day):
        recs = [h for h in self.history if h.date <= day]
        rec = recs[-1] if recs else None
        if rec is None:
            return self.job.subdivision_id, self.job.occupation_id, self.job.rate
        return rec.subdivision_id, rec.occupation_id, rec.rate

    def active(self, day) -> bool:
        return self.job.date_from <= day and (self.job.end_date is None or day <= self.job.end_date)

    def _suspensions(self, until):
        periods, start = [], None
        for h in self.history:
            if h.event == "suspend":
                start = h.date
            elif h.event == "resume" and start:
                periods.append((start, h.date - timedelta(days=1)))
                start = None
        if start:
            periods.append((start, until))
        return periods

    def is_suspended(self, day) -> bool:
        return any(a <= day <= b for a, b in self.suspended)

    def absence(self, day):
        return next((a for a in self.absences if a.date_from <= day <= a.date_to), None)

    def schedule(self, day):
        recs = [s for s in self.schedules if s.date_from <= day]
        return recs[-1] if recs else None

    def weekly_hours(self, day, subdivisions, occupations) -> Decimal:
        js = self.schedule(day)
        if js:
            return js.schedule.weekly_hours
        sub_id, occ_id, _ = self.values_on(day)
        sub = subdivisions.get(sub_id)
        if sub is not None and sub.reduced_hours:
            return sub.reduced_hours
        occ = occupations.get(occ_id)
        return occ.weekly_hours if occ else Decimal("40")


class Context:
    """Datele comune ale unei luni (turele, calendarul, funcțiile, subdiviziunile, absențele)."""

    def __init__(self, year: int, month: int):
        from apps.org.models import Occupation

        self.year, self.month = year, month
        self.days = month_days(year, month)
        self.cal = Calendar(self.days[0], self.days[-1])
        self.shifts = {s.code: s for s in ShiftType.objects.all()}
        self.subdivisions = {s.pk: s for s in Subdivision.objects.all()}
        self.occupations = {o.pk: o for o in Occupation.objects.all()}
        self.min_rest = Decimal(str(get_settings().get("min_rest_hours") or 0))

    def jobs(self, subdivision: Subdivision):
        """Raporturile de muncă care au măcar o zi în subdiviziune (cu sub-subdiviziunile) în luna dată."""
        ids = subdivision.descendant_ids()
        first, last = self.days[0], self.days[-1]
        qs = (Employment.objects.filter(date_from__lte=last).filter(Q(end_date__isnull=True) | Q(end_date__gte=first))
              .filter(Q(subdivision_id__in=ids) | Q(history__subdivision_id__in=ids)).distinct()
              .select_related("employee", "occupation", "subdivision")
              .prefetch_related("history", "work_schedules__schedule"))
        jobs = list(qs)
        emp_ids = {j.employee_id for j in jobs}
        absences = defaultdict(list)
        for a in Absence.objects.filter(employee_id__in=emp_ids, date_from__lte=last, date_to__gte=first):
            absences[a.employee_id].append(a)
        out = []
        for job in jobs:
            jd = JobDays(job, self.days, absences.get(job.employee_id, []))
            mine = [d for d in self.days if jd.active(d) and jd.values_on(d)[0] in ids]
            if mine:
                jd.days = set(mine)
                out.append(jd)
        out.sort(key=lambda jd: (jd.job.employee.last_name, jd.job.employee.first_name, jd.job.kind != "main", jd.job.pk))
        return out

    def shift(self, code):
        """(ore, ore de noapte, începutul) pentru codul turei; codurile numerice („8”, „4”) — ore de zi."""
        if not code:
            return None
        s = self.shifts.get(code)
        if s is not None:
            return s.hours, s.night_hours, s.start or time(8)
        try:
            hours = Decimal(str(code).replace(",", "."))
        except Exception:  # noqa: BLE001
            return None
        return hours, Decimal("0"), time(8)

    def planned(self, jd: JobDays, day: date) -> str:
        """Codul turei din graficul de lucru al raportului (fără graficul lunar)."""
        _sub, _occ, rate = jd.values_on(day)
        js = jd.schedule(day)
        if js is None or js.schedule.kind == "week":
            if js is not None:
                week = js.schedule.week or []
                code = week[day.weekday()] if len(week) == 7 else ""
                if day in self.cal.overrides and self.cal.overrides[day].working and not code:
                    code = next((c for c in week if c), "")  # sâmbăta lucrătoare transferată: ca în zilele obișnuite
                if not self.cal.is_working(day) and js.schedule.holidays_off:
                    return ""
                info = self.shift(code)
                if info is None:
                    return ""
                hours = info[0] * rate - self.cal.hours_less(day)
                return code if rate == ONE and not self.cal.hours_less(day) else fmt_hours(hours)
            if not self.cal.is_working(day):
                return ""
            weekly = jd.weekly_hours(day, self.subdivisions, self.occupations)
            return fmt_hours(weekly / 5 * rate - self.cal.hours_less(day))
        cycle = js.schedule.cycle or []
        if not cycle:
            return ""
        start = js.schedule.cycle_start or js.date_from
        code = cycle[((day - start).days + js.cycle_offset) % len(cycle)]
        if js.schedule.holidays_off and self.cal.is_holiday(day):
            return ""
        return code or ""

    def norm(self, jd: JobDays) -> Decimal:
        """Norma de ore a lunii pentru raport: zilele lucrătoare în care e în subdiviziune × orele pe zi × norma."""
        total = Decimal("0")
        for day in sorted(jd.days):
            if self.cal.is_working(day):
                _s, _o, rate = jd.values_on(day)
                total += (jd.weekly_hours(day, self.subdivisions, self.occupations) / 5 - self.cal.hours_less(day)) * rate
        return total


# --- graficul de ture (lunar) ------------------------------------------------------------------------------------------
def _label(jd: JobDays, ctx: Context) -> dict:
    job = jd.job
    sub_id, occ_id, rate = jd.values_on(max(jd.days))
    occ, sub = ctx.occupations.get(occ_id), ctx.subdivisions.get(sub_id)
    return {"employment": job.pk, "employee": job.employee_id, "name": job.employee.full_name(),
            "short_name": job.employee.short_name(), "tab_number": job.employee.tab_number, "kind": job.kind,
            "kind_label": job.get_kind_display(), "occupation": occ.name_ro if occ else "",
            "subdivision": sub.name_ro if sub else "", "rate": float(rate)}


@transaction.atomic
def fill_roster(roster: Roster, overwrite=False) -> int:
    """Adaugă raporturile lipsă și le completează turele din graficul de lucru (cele existente rămân, dacă nu se cere)."""
    ctx = Context(roster.year, roster.month)
    lines = {ln.employment_id: ln for ln in roster.lines.all()}
    added = 0
    for i, jd in enumerate(ctx.jobs(roster.subdivision), start=1):
        ln = lines.get(jd.job.pk)
        if ln is None:
            ln = RosterLine(roster=roster, employment=jd.job, sort=i * 10)
            added += 1
        elif ln.days and not overwrite:
            continue
        ln.days = {str(d.day): code for d in sorted(jd.days) if (code := ctx.planned(jd, d))}
        ln.save()
    return added


def roster_report(roster: Roster) -> dict:
    """Rândurile cu totalurile (ore, noapte, ture de noapte, norma) și avertismentele (CM art. 101): două ture la rând,
    odihna dintre ture mai scurtă decât dublul turei anterioare (sau decât minimul din setări), prea multe ture de noapte,
    norma depășită, tură într-o zi de absență."""
    ctx = Context(roster.year, roster.month)
    jobs = {jd.job.pk: jd for jd in ctx.jobs(roster.subdivision)}
    rows, warnings = [], []
    for ln in roster.lines.select_related("employment__employee").order_by("sort", "id"):
        jd = jobs.get(ln.employment_id)
        if jd is None:  # raportul nu mai e în secție în luna aceasta
            jd = JobDays(ln.employment, ctx.days, list(ln.employment.employee.absences.all()))
            jd.days = {d for d in ctx.days if jd.active(d)}
        hours = night = Decimal("0")
        nights = 0
        absences = {}
        prev_end, prev_hours, prev_shift = None, 0.0, False
        for day in ctx.days:
            code = (ln.days or {}).get(str(day.day), "")
            a = jd.absence(day)
            if a is not None:
                absences[str(day.day)] = ABSENCE_CODES.get(a.kind, "")
            info = ctx.shift(code)
            if info is None:
                continue
            h, n, start = info
            hours, night, nights = hours + h, night + n, nights + (1 if n > 0 else 0)
            begin = datetime.combine(day, start)
            if prev_end is not None and h > 0:
                rest = (begin - prev_end).total_seconds() / 3600
                # CM art. 101 alin. (6): între ture — cel puțin dublul turei anterioare; orele scrise ca cifră nu sunt tură
                need = max(float(ctx.min_rest), 2 * prev_hours if prev_shift else 0)
                who = {"employment": ln.employment_id, "name": ln.employment.employee.short_name(), "day": day.day}
                if rest <= 0:  # CM art. 101 alin. (4): două ture la rând sunt interzise
                    warnings.append({"kind": "consecutive", **who})
                elif rest < need:
                    warnings.append({"kind": "rest", **who, "rest": round(rest, 1), "need": round(need, 1)})
            if h > 0:
                prev_end, prev_hours, prev_shift = begin + timedelta(hours=float(h)), float(h), code in ctx.shifts
            if a is not None:
                warnings.append({"kind": "absence", "employment": ln.employment_id, "name": ln.employment.employee.short_name(),
                                 "day": day.day, "code": ABSENCE_CODES.get(a.kind, "")})
        norm = ctx.norm(jd) if jd.days else Decimal("0")
        if hours > norm and norm:
            warnings.append({"kind": "norm", "employment": ln.employment_id, "name": ln.employment.employee.short_name(),
                             "hours": _q(hours), "norm": _q(norm)})
        max_nights = int(get_settings().get("max_night_shifts") or 0)
        if max_nights and nights > max_nights:
            warnings.append({"kind": "nights", "employment": ln.employment_id, "name": ln.employment.employee.short_name(),
                             "nights": nights, "max": max_nights})
        rows.append({"id": ln.id, **_label(jd, ctx), "days": ln.days or {}, "absences": absences, "note": ln.note,
                     "hours": _q(hours), "night": _q(night), "nights": nights, "norm": _q(norm), "diff": _q(hours - norm)})
    return {"days": _days_header(ctx), "rows": rows, "warnings": warnings}


def _days_header(ctx: Context) -> list:
    return [{"day": d.day, "weekday": d.weekday(), "holiday": ctx.cal.is_holiday(d), "working": ctx.cal.is_working(d)}
            for d in ctx.days]


# --- tabela de pontaj ----------------------------------------------------------------------------------------------
IDLE_CODES = ("St", "Șt")  # staționarea, șomajul tehnic — zilele lor au orele planificate („ph”), care se plătesc după cauză


def _cell(ctx: Context, jd: JobDays, day: date, roster_days) -> dict | None:
    a = jd.absence(day)
    if a is not None:
        if a.kind in WITHOUT_HOLIDAYS and ctx.cal.is_holiday(day):
            return {"c": HOLIDAY}
        if a.kind in IDLE_KINDS:
            # staționarea / șomajul tehnic acoperă doar zilele cu tură planificată; repausul și sărbătoarea rămân ale lor
            planned = planned_hours(ctx, jd, day, roster_days)
            if planned <= 0:
                return {"c": HOLIDAY if ctx.cal.is_holiday(day) else REST}
            return {"c": ABSENCE_CODES[a.kind], "ph": float(planned)}
        return {"c": ABSENCE_CODES.get(a.kind, "?")}
    if jd.is_suspended(day):
        return {"c": SUSPENDED}
    code = roster_days.get(str(day.day), "") if roster_days is not None else ctx.planned(jd, day)
    info = ctx.shift(code)
    if info is None:
        return {"c": HOLIDAY if ctx.cal.is_holiday(day) else REST}
    hours, night, _start = info
    cell = {"c": code, "h": float(hours), "n": float(night)}
    if ctx.cal.is_holiday(day):
        cell["hol"] = 1
    return cell


def planned_hours(ctx: Context, jd: JobDays, day: date, roster_days=None) -> Decimal:
    """Orele planificate ale zilei (norma zilei): tura din graficul lunar al subdiviziunii, dacă există, altfel din graficul
    de lucru al raportului. 0 — zi de repaus după grafic."""
    code = roster_days.get(str(day.day), "") if roster_days is not None else ctx.planned(jd, day)
    info = ctx.shift(code)
    return info[0] if info else Decimal("0")


def overtime_first_hours(on_day: date) -> Decimal:
    """Câte ore suplimentare pe zi se plătesc cu tariful întâi (CM art. 157: primele două ore) — constanta salariului."""
    from apps.payroll.models import PayConstant

    c = PayConstant.objects.filter(code="overtime_first_hours", date_from__lte=on_day).order_by("-date_from").first()
    return c.value if c else Decimal("2")


def split_overtime(hours: Decimal, first: Decimal) -> tuple:
    """Orele suplimentare ale unei perioade (o zi; la evidența globală — perioada de calcul) → (primele `first` ore, restul)."""
    hours = max(hours, Decimal("0"))
    head = min(hours, first)
    return head, hours - head


def accounting_period(schedule, year: int, month: int):
    """Perioada de calcul a evidenței globale (CM art. 99) care cuprinde luna: (prima lună, ultima lună) ca date (ziua 1);
    None — evidența e lunară (perioada de o lună, sau luna e înaintea primei perioade)."""
    n = int(getattr(schedule, "accounting_months", 1) or 1)
    if schedule is None or n <= 1:
        return None
    start = schedule.accounting_start or date(year, 1, 1)
    k = (year * 12 + month - 1) - (start.year * 12 + start.month - 1)
    if k < 0:
        return None
    first_index = start.year * 12 + start.month - 1 + (k // n) * n
    last_index = first_index + n - 1
    return date(first_index // 12, first_index % 12 + 1, 1), date(last_index // 12, last_index % 12 + 1, 1)


def _day_norm(ctx: Context, jd: JobDays, day: date) -> Decimal:
    """Norma zilei lucrătoare din calendar pentru raport (orele săptămânale / 5 − ziua scurtată, × norma)."""
    if not ctx.cal.is_working(day):
        return Decimal("0")
    _s, _o, rate = jd.values_on(day)
    return (jd.weekly_hours(day, ctx.subdivisions, ctx.occupations) / 5 - ctx.cal.hours_less(day)) * rate


def _period_before(jd: JobDays, first_month: date, year: int, month: int) -> dict:
    """Orele lunilor de dinainte din perioada de calcul (din tabelele de pontaj ale raportului): obișnuite, norma, norma
    zilelor de absență și lunile fără pontaj."""
    out = {"regular": Decimal("0"), "norm": Decimal("0"), "norm_absent": Decimal("0"), "months": [], "missing": []}
    cur = first_month
    while (cur.year, cur.month) < (year, month):
        lines = list(TimesheetLine.objects.filter(employment=jd.job, timesheet__year=cur.year, timesheet__month=cur.month,
                                                  timesheet__deletion_mark=False).values_list("totals", flat=True))
        if lines:
            for t in lines:
                t = t or {}
                for k in ("regular", "norm", "norm_absent"):
                    out[k] += Decimal(str(t.get(k) or 0))
            out["months"].append(f"{cur:%m.%Y}")
        else:
            out["missing"].append(f"{cur:%m.%Y}")
        cur = (cur + timedelta(days=32)).replace(day=1)
    return out


def line_totals(ctx: Context, jd: JobDays, days: dict, roster_days=None) -> dict:
    """Totalurile rândului din pontaj. Pe fiecare zi (CM art. 157, 158):
    - sărbătoarea nelucrătoare și ziua de repaus după grafic (fără tură planificată) — orele merg la „holiday” / „rest_work”;
    - ziua lucrătoare — orele peste tura planificată sunt suplimentare, împărțite în primele 2 ore și restul
      (`overtime_days` = {zi: [primele, restul]}), celelalte sunt ore obișnuite („regular”).
    Orele obișnuite peste norma lunii (graficul pe ture planificat peste normă) sunt suplimentare pe perioadă
    (`overtime_period`, împărțite la fel); evidența globală pe o perioadă mai lungă (CM art. 99) se adaugă aici.
    Orele de sărbătoare / repaus se împart în „în limita normei lunare” și „peste normă” (pentru salariul lunar):
    în limită — cât mai lipsește orelor obișnuite până la normă."""
    worked = hours = night = holiday = rest_work = regular = Decimal("0")
    codes = defaultdict(int)
    first = overtime_first_hours(ctx.days[-1])
    ot_days, ot_first, ot_next = {}, Decimal("0"), Decimal("0")
    for key, cell in days.items():
        h = Decimal(str(cell.get("h") or 0))
        if h > 0:
            worked += 1
            hours += h
            night += Decimal(str(cell.get("n") or 0))
            day = ctx.days[int(key) - 1] if key.isdigit() and 1 <= int(key) <= len(ctx.days) else None
            if cell.get("hol") or (day is not None and ctx.cal.is_holiday(day)):
                holiday += h
                continue
            plan = planned_hours(ctx, jd, day, roster_days) if day is not None else h
            if plan <= 0:
                rest_work += h
                continue
            over = max(h - plan, Decimal("0"))
            regular += h - over
            if over:
                a, b = split_overtime(over, first)
                ot_days[key] = [_q(a), _q(b)]
                ot_first, ot_next = ot_first + a, ot_next + b
        elif cell.get("c"):
            codes[cell["c"]] += 1
    norm = ctx.norm(jd) if jd.days else Decimal("0")
    # norma zilelor lucrătoare din calendar în care raportul n-a lucrat din cauza unei absențe (concediu, boală, staționare…)
    norm_absent = Decimal("0")
    idle = defaultdict(lambda: Decimal("0"))
    for key, cell in days.items():
        code = cell.get("c") or ""
        if Decimal(str(cell.get("h") or 0)) > 0 or not code or code in (REST, HOLIDAY) or not key.isdigit():
            continue
        day = ctx.days[int(key) - 1] if 1 <= int(key) <= len(ctx.days) else None
        if day is not None and day in jd.days:
            norm_absent += _day_norm(ctx, jd, day)
        if code in IDLE_CODES:
            idle[code] += Decimal(str(cell.get("ph") or 0))
    out_extra = {"norm_absent": _q(norm_absent)}
    if idle:
        out_extra["idle"] = {k: _q(v) for k, v in sorted(idle.items())}
    js = jd.schedule(max(jd.days)) if jd.days else None
    acc = accounting_period(js.schedule, ctx.year, ctx.month) if js is not None else None
    if acc is None:
        period = max(regular - norm, Decimal("0"))  # evidența lunară: orele peste norma lunii
    else:
        # evidența globală (CM art. 99): în lunile perioadei nu sunt suplimentare pe lună; în ultima — orele obișnuite ale
        # perioadei peste norma ei (fără zilele de absență)
        first_m, last_m = acc
        last = (ctx.year, ctx.month) == (last_m.year, last_m.month)
        info = {"months": js.schedule.accounting_months, "from": f"{first_m:%m.%Y}", "to": f"{last_m:%m.%Y}", "last": last}
        period = Decimal("0")
        if last:
            before = _period_before(jd, first_m, ctx.year, ctx.month)
            p_regular = before["regular"] + regular
            p_norm = before["norm"] - before["norm_absent"] + norm - norm_absent
            period = max(p_regular - p_norm, Decimal("0"))
            info.update({"regular": _q(p_regular), "norm": _q(p_norm), "missing_months": before["missing"]})
        out_extra["summarized"] = info
    if period:
        a, b = split_overtime(period, first)
        # orele trec din cele obișnuite în suplimentare (la evidența globală — cel mult cele ale lunii; restul au fost lucrate
        # în lunile de dinainte ale perioadei)
        ot_first, ot_next, regular = ot_first + a, ot_next + b, regular - min(period, regular)
    special = holiday + rest_work
    in_norm = min(special, max(norm - regular, Decimal("0")))
    return {"days": int(worked), "hours": _q(hours), "night": _q(night), "holiday": _q(holiday), "rest_work": _q(rest_work),
            "regular": _q(regular), "norm": _q(norm), "overtime": _q(ot_first + ot_next), "overtime_2": _q(ot_first),
            "overtime_over": _q(ot_next), "overtime_period": _q(period), "overtime_days": dict(sorted(ot_days.items(), key=lambda kv: int(kv[0]))),
            "holiday_in_norm": _q(in_norm), "holiday_over_norm": _q(special - in_norm),
            "missing": _q(max(norm - regular - in_norm, Decimal("0"))), "codes": dict(sorted(codes.items())), **out_extra}


def merge_totals(a: dict | None, b: dict) -> dict:
    """Totalurile a două linii de pontaj ale aceluiași raport de muncă (transfer în lună): numerele adunate, codurile și
    orele pe zile unite; evidența globală — a ultimei linii."""
    if not a:
        return dict(b)
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, bool) or k == "summarized":
            out[k] = v
        elif isinstance(v, (int, float)):
            out[k] = _q(Decimal(str(out.get(k) or 0)) + Decimal(str(v)))
        elif isinstance(v, dict):
            merged = dict(out.get(k) or {})
            for kk, vv in v.items():
                if isinstance(vv, (int, float)) and not isinstance(vv, bool):
                    merged[kk] = _q(Decimal(str(merged.get(kk) or 0)) + Decimal(str(vv)))
                else:
                    merged[kk] = vv
            out[k] = merged
        else:
            out[k] = v
    return out


@transaction.atomic
def fill_timesheet(ts: Timesheet, keep_manual=True) -> int:
    """Completează tabela: raporturile lipsă se adaugă; zilele se recalculează, cele scrise de mână rămân."""
    if ts.status == "closed":
        raise ValidationError({"detail": "Tabela este închisă."})
    ctx = Context(ts.year, ts.month)
    rosters = {ln.employment_id: ln.days or {} for ln in RosterLine.objects.filter(
        roster__subdivision=ts.subdivision, roster__year=ts.year, roster__month=ts.month)}
    lines = {ln.employment_id: ln for ln in ts.lines.all()}
    added = 0
    for i, jd in enumerate(ctx.jobs(ts.subdivision), start=1):
        ln = lines.pop(jd.job.pk, None)
        if ln is None:
            ln = TimesheetLine(timesheet=ts, employment=jd.job, sort=i * 10)
            added += 1
        old = ln.days or {}
        days = {}
        for day in sorted(jd.days):
            key = str(day.day)
            if keep_manual and old.get(key, {}).get("m"):
                days[key] = old[key]
                continue
            cell = _cell(ctx, jd, day, rosters.get(jd.job.pk))
            if cell:
                days[key] = cell
        ln.days, ln.totals = days, line_totals(ctx, jd, days, rosters.get(jd.job.pk))
        ln.save()
    for ln in lines.values():  # raporturi care nu mai sunt în secție în luna aceasta (de ex. transfer anulat)
        if not any(c.get("m") for c in (ln.days or {}).values()) and not ln.typed_hours:
            ln.delete()
    return added


def set_cell(line: TimesheetLine, day: int, code: str, hours=None, night=None) -> TimesheetLine:
    """Corectarea de mână a unei zile: cod de absență (fără ore) sau tura / orele lucrate."""
    ts = line.timesheet
    if ts.status == "closed":
        raise ValidationError({"detail": "Tabela este închisă."})
    ctx = Context(ts.year, ts.month)
    if not 1 <= day <= len(ctx.days):
        raise ValidationError({"day": "Ziua nu este în lună."})
    d = ctx.days[day - 1]
    days = dict(line.days or {})
    code = (code or "").strip()
    if not code and hours in (None, "", 0, "0"):
        days[str(day)] = {"c": "", "m": 1}
    elif code in IDLE_CODES:
        jd0 = _line_job_days(line, ctx)
        roster0 = _roster_days(line)
        days[str(day)] = {"c": code, "m": 1, "ph": float(planned_hours(ctx, jd0, d, roster0))}
    elif code in CODE_LABELS:
        days[str(day)] = {"c": code, "m": 1}
    else:
        info = ctx.shift(code) if code else None
        h = Decimal(str(hours).replace(",", ".")) if hours not in (None, "") else (info[0] if info else None)
        if h is None or h < 0 or h > 24:
            raise ValidationError({"hours": "Orele lucrate sunt între 0 și 24 (sau un cod de tură / absență)."})
        n = Decimal(str(night).replace(",", ".")) if night not in (None, "") else (info[1] if info else Decimal("0"))
        if n > h:
            raise ValidationError({"night": "Orele de noapte nu pot fi mai multe decât cele lucrate."})
        cell = {"c": code or fmt_hours(h), "h": float(h), "n": float(n), "m": 1}
        if ctx.cal.is_holiday(d):
            cell["hol"] = 1
        days[str(day)] = cell
    line.days = days
    line.totals = line_totals(ctx, _line_job_days(line, ctx), days, _roster_days(line))
    line.save(update_fields=["days", "totals"])
    return line


def _line_job_days(line: TimesheetLine, ctx: Context) -> JobDays:
    """Zilele raportului de muncă al liniei în subdiviziunea tabelei (cu absențele lunii)."""
    ts = line.timesheet
    jd = JobDays(line.employment, ctx.days, list(line.employment.employee.absences.filter(
        date_from__lte=ctx.days[-1], date_to__gte=ctx.days[0])))
    ids = ts.subdivision.descendant_ids()
    jd.days = {x for x in ctx.days if jd.active(x) and jd.values_on(x)[0] in ids}
    return jd


def _roster_days(line: TimesheetLine):
    ts = line.timesheet
    roster = RosterLine.objects.filter(roster__subdivision=ts.subdivision, roster__year=ts.year, roster__month=ts.month,
                                       employment=line.employment).first()
    return (roster.days or {}) if roster else None


def typed_by_job(year: int, month: int, employment_ids) -> dict:
    """Orele pe tipuri ale raporturilor în lună, din toate tabelele lunii (un raport cu două linii — adunate)."""
    from . import hour_types

    parts = defaultdict(list)
    for ln in TimesheetLine.objects.filter(timesheet__year=year, timesheet__month=month, timesheet__deletion_mark=False,
                                           employment_id__in=list(employment_ids)).only("employment_id", "typed_hours"):
        if ln.typed_hours:
            parts[ln.employment_id].append(ln.typed_hours)
    return {k: hour_types.merge(v) for k, v in parts.items()}


def timesheet_report(ts: Timesheet, only_line=None) -> dict:
    """Rândurile tabelei cu zilele, totalurile și orele pe tipuri (efective, garantate, de plată — apps.worktime.hour_types),
    plus coloanele tipurilor de ore: cele cu tarif pe raporturile din tabelă, cele scrise și cele „pentru toți”."""
    from apps.staff.models import FunctionCombination

    from . import hour_types
    from .models import HourType, JobHourRate

    ctx = Context(ts.year, ts.month)
    first, last = ctx.days[0], ctx.days[-1]
    lines = list(ts.lines.select_related("employment__employee", "employment__occupation").prefetch_related(
        "employment__history").order_by("sort", "id"))
    if only_line is not None:
        lines = [ln for ln in lines if ln.pk == only_line]
    job_ids = {ln.employment_id for ln in lines}
    types = {t.code: t for t in HourType.objects.all()}
    rates = defaultdict(list)
    for r in JobHourRate.objects.filter(employment_id__in=job_ids).select_related("hour_type"):
        rates[r.employment_id].append(r)
    combos = defaultdict(list)
    for c in (FunctionCombination.objects.filter(employment_id__in=job_ids, date_from__lte=last)
              .filter(Q(date_to__isnull=True) | Q(date_to__gte=first)).select_related("occupation", "hour_type")):
        combos[c.employment_id].append(c)
    absences = defaultdict(list)
    for a in Absence.objects.filter(employee_id__in={ln.employment.employee_id for ln in lines}, date_from__lte=last,
                                    date_to__gte=first):
        absences[a.employee_id].append(a)
    typed = typed_by_job(ts.year, ts.month, job_ids)
    conf = hour_types.settings()
    rows, used = [], set()
    for ln in lines:
        jd = JobDays(ln.employment, ctx.days, absences.get(ln.employment.employee_id, []))
        jd.days = set(ctx.days)
        summary = hour_types.summarize(ctx, jd, typed.get(ln.employment_id, {}), rates.get(ln.employment_id, []), types, conf)
        used |= set(summary)
        for c in combos.get(ln.employment_id, []):
            if c.pay_mode == "hourly" and c.hour_type_id:
                used.add(c.hour_type.code)
        rec = ln.employment.history.filter(date__lte=last).order_by("-date", "-id").first()
        mode = rec.pay_mode if rec else ln.employment.pay_mode
        rows.append({"id": ln.id, **_label(jd, ctx), "days": ln.days or {}, "totals": ln.totals or {}, "note": ln.note,
                     "typed": (ln.typed_hours or {}), "hour_types": summary,
                     "hour_warnings": hour_types.warnings(summary, ln.totals or {}),
                     "pay_mode": mode, "rate_codes": sorted({r.hour_type.code for r in rates.get(ln.employment_id, [])
                                                             if r.in_force(first, last)}),
                     "combinations": [{"kind": c.kind, "occupation": c.occupation.name_ro, "pay_mode": c.pay_mode,
                                       "value": float(c.value), "text": str(c)} for c in combos.get(ln.employment_id, [])]})
    used |= {t.code for t in types.values() if t.in_all_timesheets and t.is_active and not t.deletion_mark}
    columns = [{"code": t.code, "name_ro": t.name_ro, "name_ru": t.name_ru, "name_en": t.name_en, "entry": t.entry,
                "work_time": t.work_time, "is_active": t.is_active and not t.deletion_mark}
               for t in sorted((types[c] for c in used if c in types), key=lambda t: (t.sort, t.code))]
    return {"days": _days_header(ctx), "rows": rows, "codes": CODE_LABELS, "manual_codes": [*MANUAL_CODES, *CODE_LABELS],
            "hour_types": columns}


def visible_ids(user):
    from apps.staff import services as staff

    return staff.visible_subdivision_ids(user, "worktime")
