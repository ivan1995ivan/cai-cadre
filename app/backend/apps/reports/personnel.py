"""Rapoartele despre personal: mișcarea cadrelor, structura, vechimea, zilele de naștere, pensionările, posturile vacante."""
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q

from apps.org.models import STAFF_CATEGORY, DictItem, Occupation, Subdivision
from apps.staff import services as staff
from apps.staff.models import CIVIL_KINDS, EMPLOYMENT_KINDS, MAIN_KINDS, Employee, Employment, EmploymentHistory

from .registry import col, report, subtitle_parts

NO_CATEGORY = ("Fără categorie", "Без категории", "No category")
KIND_T = {
    "main": ("De bază", "Основная", "Main"), "main_student": ("De bază (student)", "Основная (студент)", "Main (student)"),
    "internal": ("Cumul intern", "Внутреннее совместительство", "Internal part-time"),
    "external": ("Cumul extern", "Внешнее совместительство", "External part-time"),
    "substitute": ("Suplinire temporară", "Временное замещение", "Temporary substitution"),
    "contractor": ("Prestări servicii", "Договор услуг", "Service contract"),
}
SEX_T = {"M": ("Bărbați", "Мужчины", "Men"), "F": ("Femei", "Женщины", "Women"), "": ("Nespecificat", "Не указан", "Not set")}
COMMON = {
    "tab": ("Nr. tabel", "Таб. №", "Tab no."), "name": ("Numele, prenumele", "Фамилия, имя", "Full name"),
    "sub": ("Subdiviziunea", "Подразделение", "Department"), "occ": ("Funcția", "Должность", "Position"),
    "kind": ("Tipul", "Вид", "Type"), "date": ("Data", "Дата", "Date"), "total": ("Total", "Всего", "Total"),
    "women": ("Femei", "Женщины", "Women"), "pct": ("%", "%", "%"), "rate": ("Norma", "Ставка", "Rate"),
}


class Lookup:
    """Subdiviziunile și funcțiile într-un singur query (tabelele sunt mici)."""

    def __init__(self, lang):
        self.lang = lang
        self.subs = {s.pk: s for s in Subdivision.objects.all()}
        self.occs = {o.pk: o for o in Occupation.objects.select_related("category")}

    def sub(self, pk):
        s = self.subs.get(pk)
        return s.local_name(self.lang) if s else ""

    def occ(self, pk):
        o = self.occs.get(pk)
        return o.local_name(self.lang) if o else ""

    def category(self, occ_pk):
        """Id-ul categoriei de personal a funcției (clasificatorul „Categoriile de personal”), None — fără categorie."""
        o = self.occs.get(occ_pk)
        return o.category_id if o else None

    def category_code(self, occ_pk) -> str:
        o = self.occs.get(occ_pk)
        return o.category.code if o and o.category_id else ""

    def category_name(self, occ_pk, t) -> str:
        o = self.occs.get(occ_pk)
        return o.category.local_name(self.lang) if o and o.category_id else t(NO_CATEGORY)

    def in_category(self, occ_pk, wanted: str) -> bool:
        """Filtrul raportului: `wanted` e id-ul categoriei (text din adresă), „none” — fără categorie, gol — toate."""
        if not wanted:
            return True
        cat = self.category(occ_pk)
        return cat is None if wanted == "none" else str(cat or "") == wanted


def category_order(lang) -> list:
    """Denumirile categoriilor în ordinea clasificatorului (pentru secțiunile rapoartelor)."""
    return [c.local_name(lang) for c in DictItem.objects.filter(kind=STAFF_CATEGORY)]


def snapshot(emp: Employment, day) -> dict:
    """Subdiviziunea, funcția și norma la data dată, din istoricul preîncărcat."""
    recs = [h for h in emp.history.all() if h.date <= day]
    if not recs:
        return {"subdivision_id": emp.subdivision_id, "occupation_id": emp.occupation_id, "rate": emp.rate}
    h = max(recs, key=lambda r: (r.date, r.id))
    return {"subdivision_id": h.subdivision_id, "occupation_id": h.occupation_id, "rate": h.rate}


def load_jobs(p, day_from, day_to, kinds=None) -> list:
    """Raporturile de muncă care se suprapun cu perioada (fără contractele civile), cu istoricul preîncărcat."""
    qs = (Employment.objects.filter(date_from__lte=day_to).filter(Q(end_date__isnull=True) | Q(end_date__gte=day_from))
          .exclude(kind__in=CIVIL_KINDS).select_related("employee").prefetch_related("history"))
    if (kinds or p.kinds) == "main":
        qs = qs.filter(kind__in=MAIN_KINDS)
    return list(qs)


def jobs_on(p, day, look: Lookup, kinds=None, preloaded=None):
    """Raporturile în vigoare la data dată, în subdiviziunile văzute și categoria aleasă: [(raportul, instantaneul)]."""
    out = []
    for e in (preloaded if preloaded is not None else load_jobs(p, day, day, kinds)):
        if e.date_from > day or (e.end_date and e.end_date < day):
            continue
        snap = snapshot(e, day)
        if not p.allowed(snap["subdivision_id"]):
            continue
        if not look.in_category(snap["occupation_id"], p.category):
            continue
        out.append((e, snap))
    return out


def _d(day):
    return day.isoformat() if day else None


def _pct(part, whole):
    return round(part * 100 / whole, 1) if whole else 0


# --- mișcarea cadrelor -------------------------------------------------------------------------------------------------
@report("movement", "personnel", ("Mișcarea cadrelor", "Движение кадров", "Staff turnover"),
        ("Angajații, eliberații și transferații în perioadă, cu motivele; efectivul la început și la sfârșit, rata fluctuației.",
         "Принятые, уволенные и переведённые за период, с причинами; численность на начало и конец, коэффициент текучести.",
         "Hired, dismissed and transferred in the period with reasons; headcount at start and end, turnover rate."),
        ["period", "subdivision", "category", "kinds"])
def movement(p):
    look = Lookup(p.lang)
    start = {e.employee_id for e, _ in jobs_on(p, p.date_from - timedelta(days=1), look)}
    end = {e.employee_id for e, _ in jobs_on(p, p.date_to, look)}
    jobs = Employment.objects.exclude(kind__in=CIVIL_KINDS).select_related("employee", "termination_reason").prefetch_related("history")
    if p.kinds == "main":
        jobs = jobs.filter(kind__in=MAIN_KINDS)

    def keep(snap):
        return p.allowed(snap["subdivision_id"]) and look.in_category(snap["occupation_id"], p.category)

    def row(e, snap, day, detail, order=""):
        return {"date": _d(day), "tab": e.employee.tab_number, "name": e.employee.full_name(), "sub": look.sub(snap["subdivision_id"]),
                "occ": look.occ(snap["occupation_id"]), "kind": p.t(KIND_T.get(e.kind, (e.kind,))), "detail": detail, "order": order}

    hired, left, moved = [], [], []
    for e in jobs.filter(date_from__range=(p.date_from, p.date_to)):
        snap = snapshot(e, e.date_from)
        if keep(snap):
            hired.append(row(e, snap, e.date_from, "", e.hire_order))
    for e in jobs.filter(end_date__range=(p.date_from, p.date_to)):
        snap = snapshot(e, e.end_date)
        if keep(snap):
            reason = e.termination_reason.local_name(p.lang) if e.termination_reason else ""
            left.append(row(e, snap, e.end_date, reason, e.end_order))
    changes = (EmploymentHistory.objects.filter(event="change", date__range=(p.date_from, p.date_to), employment__in=jobs)
               .select_related("employment__employee").order_by("date", "id"))
    for h in changes:
        prev = (EmploymentHistory.objects.filter(employment_id=h.employment_id).filter(Q(date__lt=h.date) | Q(date=h.date, id__lt=h.id))
                .order_by("-date", "-id").first())
        if prev is None or (prev.subdivision_id == h.subdivision_id and prev.occupation_id == h.occupation_id):
            continue
        snap = {"subdivision_id": h.subdivision_id, "occupation_id": h.occupation_id}
        if not (keep(snap) or keep({"subdivision_id": prev.subdivision_id, "occupation_id": prev.occupation_id})):
            continue
        was = f"{look.sub(prev.subdivision_id)}, {look.occ(prev.occupation_id)}"
        moved.append(row(h.employment, snap, h.date, f"{p.t(('din', 'из', 'from'))}: {was}", h.order))
    rows = []
    for title, part in ((("Angajați", "Принятые", "Hired"), hired), (("Eliberați", "Уволенные", "Dismissed"), left),
                        (("Transferați", "Переведённые", "Transferred"), moved)):
        rows.append({"_section": f"{p.t(title)} ({len(part)})"})
        rows += sorted(part, key=lambda r: (r["date"], r["name"]))
    avg = (len(start) + len(end)) / 2
    left_people = len({r["tab"] for r in left})
    return {
        "subtitle": subtitle_parts(p, p.period_text()),
        "columns": [col("date", p.t(COMMON["date"]), "date"), col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])),
                    col("sub", p.t(COMMON["sub"])), col("occ", p.t(COMMON["occ"])), col("kind", p.t(COMMON["kind"])),
                    col("detail", p.t(("Motivul / de unde", "Причина / откуда", "Reason / from"))),
                    col("order", p.t(("Ordinul", "Приказ", "Order")))],
        "rows": rows,
        "summary": [
            {"label": p.t(("Efectivul la începutul perioadei", "Численность на начало периода", "Headcount at start")), "value": len(start)},
            {"label": p.t(("Angajați", "Принято", "Hired")), "value": len(hired)},
            {"label": p.t(("Eliberați", "Уволено", "Dismissed")), "value": len(left)},
            {"label": p.t(("Efectivul la sfârșitul perioadei", "Численность на конец периода", "Headcount at end")), "value": len(end)},
            {"label": p.t(("Rata fluctuației, %", "Коэффициент текучести, %", "Turnover rate, %")), "value": _pct(left_people, avg)},
        ],
    }


# --- structura personalului ----------------------------------------------------------------------------------------------
AGE_GROUPS = [(0, 29, "< 30"), (30, 39, "30–39"), (40, 49, "40–49"), (50, 59, "50–59"), (60, 64, "60–64"), (65, 200, "65 +")]
SENIORITY_GROUPS = [(0, 2, "< 3"), (3, 4, "3–5"), (5, 9, "5–10"), (10, 19, "10–20"), (20, 29, "20–30"), (30, 200, "30 +")]
EDU_ORDER = ["primary", "secondary", "vocational", "higher", "postgraduate", "doctorate"]


def age_on(birth, day):
    return day.year - birth.year - ((day.month, day.day) < (birth.month, birth.day))


def _group(value, groups):
    for lo, hi, label in groups:
        if lo <= value <= hi:
            return label
    return groups[-1][2]


def education_of(employee):
    levels = [e.level for e in employee.education.all() if e.level_id]
    if not levels:
        return None
    return max(levels, key=lambda lv: EDU_ORDER.index(lv.code) if lv.code in EDU_ORDER else -1)


@report("structure", "personnel", ("Structura personalului", "Структура персонала", "Staff structure"),
        ("Pe categorii, sex, vârstă, studii, vechime, tipul angajării și normă — baza pentru rapoartele statistice BNS.",
         "По категориям, полу, возрасту, образованию, стажу, виду занятости и ставке — основа для статистических отчётов НБС.",
         "By category, sex, age, education, seniority, employment type and rate."),
        ["on_date", "subdivision", "category", "kinds"])
def structure(p):
    look = Lookup(p.lang)
    jobs = jobs_on(p, p.on_date, look)
    people = {}
    for e, snap in jobs:
        people.setdefault(e.employee_id, []).append((e, snap))
    employees = {x.pk: x for x in Employee.objects.filter(pk__in=people).prefetch_related(
        "education__level", "experience", "employments")}
    dims = defaultdict(Counter)
    women = defaultdict(Counter)
    for pk, js in people.items():
        emp = employees[pk]
        main = next((x for x in js if x[0].kind in MAIN_KINDS), js[0])
        values = {
            "category": look.category_name(main[1]["occupation_id"], p.t),
            "sex": p.t(SEX_T.get(emp.sex, SEX_T[""])),
            "age": _group(age_on(emp.birth_date, p.on_date), AGE_GROUPS) if emp.birth_date else "—",
        }
        edu = education_of(emp)
        values["education"] = edu.local_name(p.lang) if edu else "—"
        years = staff.seniority(emp, p.on_date)["total"]["years"]
        values["seniority"] = _group(years, SENIORITY_GROUPS)
        rate = sum((s["rate"] for _, s in js), Decimal("0"))
        values["rate"] = p.t(("Normă întreagă și peste", "Полная ставка и больше", "Full rate or more")) if rate >= 1 \
            else p.t(("Normă parțială", "Неполная ставка", "Part rate"))
        for k, v in values.items():
            dims[k][v] += 1
            if emp.sex == "F":
                women[k][v] += 1
    total = len(people)
    kinds = Counter(e.kind for e, _ in jobs)
    titles = [("category", ("Pe categorii de personal", "По категориям персонала", "By staff category")),
              ("sex", ("Pe sexe", "По полу", "By sex")), ("age", ("Pe grupe de vârstă", "По возрастным группам", "By age group")),
              ("education", ("Pe studii (cele mai înalte)", "По образованию (высшее из имеющихся)", "By education (highest)")),
              ("seniority", ("Pe vechimea totală (ani)", "По общему стажу (лет)", "By total seniority (years)")),
              ("rate", ("Pe normă", "По ставке", "By rate"))]
    order = {"age": [g[2] for g in AGE_GROUPS] + ["—"], "seniority": [g[2] for g in SENIORITY_GROUPS],
             "category": [*category_order(p.lang), p.t(NO_CATEGORY)]}
    rows = []
    for key, title in titles:
        rows.append({"_section": p.t(title)})
        items = dims[key].items()
        if key in order:
            items = sorted(items, key=lambda kv: order[key].index(kv[0]) if kv[0] in order[key] else 99)
        else:
            items = sorted(items, key=lambda kv: -kv[1])
        for label, n in items:
            rows.append({"label": label, "total": n, "women": women[key][label], "pct": _pct(n, total)})
    if p.kinds == "all":
        rows.append({"_section": p.t(("Pe tipul raportului de muncă (raporturi)", "По виду трудовых отношений (должности)",
                                      "By employment type (jobs)"))})
        for code, _ in EMPLOYMENT_KINDS:
            if kinds[code]:
                rows.append({"label": p.t(KIND_T[code]), "total": kinds[code], "women": None, "pct": _pct(kinds[code], len(jobs))})
    return {
        "subtitle": subtitle_parts(p, f"{p.t(('la data de', 'на', 'as of'))} {p.on_date:%d.%m.%Y}"),
        "columns": [col("label", p.t(("Indicatorul", "Показатель", "Indicator"))), col("total", p.t(("Persoane", "Человек", "People")), "int"),
                    col("women", p.t(COMMON["women"]), "int"), col("pct", p.t(COMMON["pct"]), "pct")],
        "rows": rows,
        "summary": [{"label": p.t(("Total persoane", "Всего человек", "Total people")), "value": total},
                    {"label": p.t(("Femei", "Женщины", "Women")), "value": sum(1 for pk in people if employees[pk].sex == "F")}],
    }


# --- vechimea ------------------------------------------------------------------------------------------------------------
@report("seniority", "personnel", ("Vechimea în muncă", "Трудовой стаж", "Seniority"),
        ("Vechimea totală, în specialitate și în întreprindere pe fiecare angajat — pentru adeverințe și sporuri.",
         "Общий стаж, по специальности и на предприятии по каждому работнику — для справок и надбавок.",
         "Total, specialty and company seniority per employee — for certificates and allowances."),
        ["on_date", "subdivision", "category"])
def seniority(p):
    look = Lookup(p.lang)
    p.kinds = "main"
    jobs = jobs_on(p, p.on_date, look)
    employees = {x.pk: x for x in Employee.objects.filter(pk__in={e.employee_id for e, _ in jobs}).prefetch_related("experience")}
    rows = []
    for e, snap in jobs:
        emp = employees[e.employee_id]
        s = staff.seniority(emp, p.on_date)
        rows.append({"tab": emp.tab_number, "name": emp.full_name(), "sub": look.sub(snap["subdivision_id"]),
                     "occ": look.occ(snap["occupation_id"]), "date_from": _d(e.date_from),
                     **{k: staff.seniority_text(s[k], p.lang) for k in ("total", "specialty", "institution")},
                     "years": s["total"]["years"]})
    rows.sort(key=lambda r: (r["sub"], r["name"]))
    return {
        "subtitle": subtitle_parts(p, f"{p.t(('la data de', 'на', 'as of'))} {p.on_date:%d.%m.%Y}"),
        "columns": [col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("sub", p.t(COMMON["sub"])),
                    col("occ", p.t(COMMON["occ"])), col("date_from", p.t(("Angajat la", "Принят", "Hired on")), "date"),
                    col("total", p.t(("Totală", "Общий", "Total"))),
                    col("specialty", p.t(("În specialitate", "По специальности", "Specialty"))),
                    col("institution", p.t(("În întreprindere", "На предприятии", "In the company")))],
        "rows": rows,
    }


# --- zile de naștere și pensionări ------------------------------------------------------------------------------------------
def _anniversary(birth, year):
    try:
        return birth.replace(year=year)
    except ValueError:
        return birth.replace(year=year, day=28)


def _people(p, look):
    """Angajații văzuți (raportul de bază în vigoare azi), cu subdiviziunea și funcția."""
    out = {}
    for e, snap in jobs_on(p, p.today, look, kinds="all"):
        cur = out.get(e.employee_id)
        if cur is None or (e.kind in MAIN_KINDS and cur[0].kind not in MAIN_KINDS):
            out[e.employee_id] = (e, snap)
    return out


@report("birthdays", "personnel", ("Zile de naștere și jubilee", "Дни рождения и юбилеи", "Birthdays and jubilees"),
        ("Cine are ziua de naștere în perioadă; jubileele (30, 40, 50, 55, 60 … ani) sunt marcate.",
         "У кого день рождения в периоде; юбилеи (30, 40, 50, 55, 60 … лет) отмечены.",
         "Birthdays in the period; jubilees are marked."),
        ["period", "subdivision", "category"])
def birthdays(p):
    look = Lookup(p.lang)
    rows = []
    for e, snap in _people(p, look).values():
        birth = e.employee.birth_date
        if not birth:
            continue
        for year in range(p.date_from.year, p.date_to.year + 1):
            day = _anniversary(birth, year)
            if p.date_from <= day <= p.date_to:
                age = year - birth.year
                jubilee = age % 10 == 0 or (age >= 50 and age % 5 == 0)
                rows.append({"date": _d(day), "tab": e.employee.tab_number, "name": e.employee.full_name(),
                             "sub": look.sub(snap["subdivision_id"]), "occ": look.occ(snap["occupation_id"]), "age": age,
                             "jubilee": p.t(("Jubileu", "Юбилей", "Jubilee")) if jubilee else ""})
    rows.sort(key=lambda r: (r["date"], r["name"]))
    return {
        "subtitle": subtitle_parts(p, p.period_text()),
        "columns": [col("date", p.t(COMMON["date"]), "date"), col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])),
                    col("sub", p.t(COMMON["sub"])), col("occ", p.t(COMMON["occ"])), col("age", p.t(("Împlinește", "Исполняется", "Turns")), "int"),
                    col("jubilee", "")],
        "rows": rows,
    }


@report("retirements", "personnel", ("Pensionări", "Выход на пенсию", "Retirements"),
        ("Angajații care ating vârsta de pensionare în anul ales (vârsta — din setările alertelor).",
         "Работники, достигающие пенсионного возраста в выбранном году (возраст — из настроек оповещений).",
         "Employees reaching retirement age in the chosen year."),
        ["year", "subdivision", "category"])
def retirements(p):
    from apps.alerts import engine

    cfg = engine.get_settings()
    ages = {"M": int(cfg["retirement_men"]), "F": int(cfg["retirement_women"])}
    look = Lookup(p.lang)
    rows = []
    for e, snap in _people(p, look).values():
        emp = e.employee
        if not emp.birth_date or emp.sex not in ages:
            continue
        if emp.birth_date.year + ages[emp.sex] == p.year:
            rows.append({"date": _d(_anniversary(emp.birth_date, p.year)), "tab": emp.tab_number, "name": emp.full_name(),
                         "sub": look.sub(snap["subdivision_id"]), "occ": look.occ(snap["occupation_id"]),
                         "sex": p.t(SEX_T[emp.sex]), "age": ages[emp.sex]})
    rows.sort(key=lambda r: (r["date"], r["name"]))
    return {
        "subtitle": subtitle_parts(p, str(p.year)),
        "columns": [col("date", p.t(("Data", "Дата", "Date")), "date"), col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])),
                    col("sub", p.t(COMMON["sub"])), col("occ", p.t(COMMON["occ"])), col("sex", p.t(("Sexul", "Пол", "Sex"))),
                    col("age", p.t(("Vârsta", "Возраст", "Age")), "int")],
        "rows": rows,
        "summary": [{"label": p.t(("Vârsta de pensionare: bărbați / femei", "Пенсионный возраст: мужчины / женщины",
                                   "Retirement age: men / women")), "value": f"{ages['M']} / {ages['F']}"}],
    }


# --- posturile vacante ---------------------------------------------------------------------------------
def _occupancy(p):
    from apps.org import services as org_services

    occ = org_services.occupancy(on_date=p.on_date, lang=p.lang)
    wanted = p.category

    def in_category(r):
        return not wanted or (r["category"] is None if wanted == "none" else str(r["category"] or "") == wanted)

    return [r for r in occ["rows"] if p.allowed(r["subdivision_id"]) and in_category(r)]


@report("vacancies", "personnel", ("Posturi vacante", "Вакантные должности", "Vacant positions"),
        ("Unitățile vacante din statele de personal în vigoare — pentru anunțuri, ANOFM și site.",
         "Вакантные единицы действующего штатного расписания — для объявлений, НАЗ и сайта.",
         "Vacant units in the current staff list — for announcements, the employment agency and the website."),
        ["on_date", "subdivision", "category"])
def vacancies(p):
    rows, totals = [], {"approved": Decimal("0"), "occupied": Decimal("0"), "vacant": Decimal("0")}
    for r in _occupancy(p):
        vacant = Decimal(r["vacant"])
        if vacant <= 0:
            continue
        rows.append({"sub": r["subdivision"], "occ": r["occupation"], "category": r["category_name"],
                     "approved": float(r["approved"]), "occupied": float(r["occupied"]), "vacant": float(vacant)})
        for k in totals:
            totals[k] += Decimal(r[k]) if k != "vacant" else vacant
    return {
        "subtitle": subtitle_parts(p, f"{p.t(('la data de', 'на', 'as of'))} {p.on_date:%d.%m.%Y}"),
        "columns": [col("sub", p.t(COMMON["sub"])), col("occ", p.t(COMMON["occ"])), col("category", p.t(("Categoria", "Категория", "Category"))),
                    col("approved", p.t(("Aprobate", "Утверждено", "Approved")), "num"),
                    col("occupied", p.t(("Ocupate", "Занято", "Occupied")), "num"), col("vacant", p.t(("Vacante", "Вакантно", "Vacant")), "num")],
        "rows": rows,
        "totals": {"sub": p.t(COMMON["total"]), **{k: float(v) for k, v in totals.items()}},
    }


# --- legăturile către rapoartele care au pagina lor ----------------------------------------------------------------------------
def _links():
    from .registry import LINKS, Link

    LINKS.extend([
        Link("employees", "personnel", ("Lista angajaților", "Список сотрудников", "Employee list"),
             ("Cu filtre, coloane alese, gruparea pe subdiviziuni, tipar și Excel.", "С фильтрами, выбором колонок, группировкой, печатью и Excel.",
              "With filters, columns, grouping, print and Excel."), "/employees", "employees.view"),
        Link("occupancy", "personnel", ("Statele de personal și ocuparea", "Штатное расписание и замещение", "Staff list and occupancy"),
             ("Unitățile aprobate / ocupate / temporar vacante / vacante pe subdiviziuni.", "Утверждённые / занятые / временно вакантные / вакантные.",
              "Approved / occupied / temporarily vacant / vacant units."), "/staff-list/occupancy", "org.view"),
        Link("contracts", "personnel", ("Registrul contractelor", "Реестр договоров", "Contracts register"),
             ("Contractele individuale de muncă, cu termenele care expiră.", "Индивидуальные трудовые договоры со сроками.",
              "Employment contracts with expiring terms."), "/contracts", "employees.view"),
        Link("alerts", "personnel", ("Expirări și termene", "Истечения и сроки", "Expiries and deadlines"),
             ("Contracte, probe, acte, certificate, concedii sociale — lista „de făcut”.",
              "Договоры, испытательные сроки, документы, сертификаты, социальные отпуска.",
              "Contracts, probation, documents, certificates, social leave — the to-do list."), "/alerts", "reports.view"),
        Link("orders_register", "orders", ("Registrul ordinelor", "Журнал приказов", "Orders register"),
             ("Toate ordinele pe registre, cu tipar și Excel.", "Все приказы по журналам, с печатью и Excel.",
              "All orders by register, with print and Excel."), "/orders/register", "orders.view"),
        Link("leave_balances", "time", ("Soldurile concediilor", "Остатки отпусков", "Leave balances"),
             ("Zilele cuvenite, folosite și rămase pe ani de muncă.", "Положенные, использованные и оставшиеся дни.",
              "Entitled, used and remaining days by work year."), "/leave", "leave.view"),
        Link("leave_schedule", "time", ("Graficul concediilor", "График отпусков", "Leave schedule"),
             ("Graficul anual pe subdiviziuni, cu tipar.", "Годовой график по подразделениям, с печатью.", "Annual schedule by department."),
             "/leave/schedule", "leave.view"),
        Link("sick_leave", "time", ("Certificatele de concediu medical", "Больничные листы", "Sick leave certificates"),
             ("Foile de boală pe perioadă, cu zilele angajatorului.", "Больничные за период, с днями работодателя.",
              "Sick leave certificates for the period."), "/sick-leave", "sick_leave.view"),
        Link("timesheets", "time", ("Tabelele de pontaj", "Табели учёта рабочего времени", "Timesheets"),
             ("Pontajul pe secție, cu tipar și Excel.", "Табель по отделению, с печатью и Excel.", "Timesheet by department."),
             "/timesheets", "worktime.view"),
        Link("tax_reports", "external", ("IPC21, IALS21, IRM19", "IPC21, IALS21, IRM19", "IPC21, IALS21, IRM19"),
             ("Declarațiile pentru SFS și CNAS, cu XML.", "Декларации для ГНС и НКСС, с XML.", "Tax and social declarations with XML."),
             "/tax-reports", "tax_reports.view"),
    ])


_links()


# --- echipamentul de lucru -----------------------------------------------------------------------------------------------
@report("workwear_sizes", "personnel", ("Mărimile echipamentului de lucru", "Размеры спецодежды", "Workwear sizes"),
        ("Pentru comanda halatelor, costumelor și încălțămintei: pe secții — angajații cu mărimea îmbrăcămintei, a "
         "încălțămintei și înălțimea, apoi câte bucăți din fiecare mărime. Cine n-are mărimile în dosar e marcat.",
         "Для заказа халатов, костюмов и обуви: по подразделениям — сотрудники с размерами одежды, обуви и ростом, затем "
         "количество по каждому размеру.", "For ordering gowns, suits and shoes: employees by department with sizes, then counts."),
        ["on_date", "subdivision", "category"])
def workwear_sizes(p):
    look = Lookup(p.lang)
    by_sub = defaultdict(list)
    seen = set()
    for e, snap in jobs_on(p, p.on_date, look, kinds="main"):
        if e.employee_id in seen:
            continue
        seen.add(e.employee_id)
        by_sub[snap["subdivision_id"]].append((e.employee, snap))
    missing_t = p.t(("fără mărimi", "без размеров", "no sizes"))
    rows = []
    clothes, shoes = Counter(), Counter()
    without = 0
    for sub_id in sorted(by_sub, key=look.sub):
        rows.append({"_section": look.sub(sub_id)})
        for emp, snap in sorted(by_sub[sub_id], key=lambda x: (x[0].last_name, x[0].first_name)):
            has = bool(emp.clothing_size or emp.shoe_size)
            without += 0 if has else 1
            if emp.clothing_size:
                clothes[emp.clothing_size] += 1
            if emp.shoe_size:
                shoes[emp.shoe_size] += 1
            rows.append({"tab": emp.tab_number, "name": emp.full_name(), "occ": look.occ(snap["occupation_id"]),
                         "sex": p.t(SEX_T.get(emp.sex or "", SEX_T[""])), "clothing": emp.clothing_size, "shoes": emp.shoe_size,
                         "height": emp.height, "note": "" if has else missing_t})

    def order(sizes: Counter) -> str:
        def key(s):
            try:
                return (0, float(s.replace(",", ".")), s)
            except ValueError:
                return (1, 0, s)
        return ", ".join(f"{s} — {n}" for s, n in sorted(sizes.items(), key=lambda x: key(x[0])))

    return {
        "subtitle": subtitle_parts(p, p.t(("la ", "на ", "on ")) + p.on_date.strftime("%d.%m.%Y")),
        "columns": [col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("occ", p.t(COMMON["occ"])),
                    col("sex", p.t(("Sexul", "Пол", "Sex"))), col("clothing", p.t(("Îmbrăcămintea", "Одежда", "Clothing"))),
                    col("shoes", p.t(("Încălțămintea", "Обувь", "Shoes"))), col("height", p.t(("Înălțimea, cm", "Рост, см", "Height, cm")), "int"),
                    col("note", "")],
        "rows": rows,
        "summary": [{"label": p.t(("Angajați", "Сотрудников", "Employees")), "value": len(seen)},
                    {"label": p.t(("Îmbrăcăminte, pe mărimi", "Одежда по размерам", "Clothing by size")), "value": order(clothes) or "—"},
                    {"label": p.t(("Încălțăminte, pe mărimi", "Обувь по размерам", "Shoes by size")), "value": order(shoes) or "—"},
                    {"label": p.t(("Fără mărimi în dosar", "Без размеров в личном деле", "Without sizes")), "value": without}],
    }
