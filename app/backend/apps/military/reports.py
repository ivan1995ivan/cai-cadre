"""Evidența militară (HG 631/2003): registrul recruților și rezerviștilor, modificările lunii pentru centrul militar,
lista recruților, angajații fără fișă de evidență militară."""
import calendar
from datetime import date, datetime, time

from django.utils import timezone

from apps.reports.personnel import COMMON, MAIN_KINDS, Lookup, _d, age_on, jobs_on, snapshot
from apps.reports.registry import GROUPS, col, report, subtitle_parts
from apps.staff.models import Employment, EmploymentHistory, MilitaryRecord

GROUPS.setdefault("health", ("Sănătate și evidență militară", "Здоровье и воинский учёт", "Health and military records"))
MEDICAL = {"physicians", "pharmacists", "nurses", "junior"}
STATUS = dict(MilitaryRecord.STATUSES)
COMPOSITION = dict(MilitaryRecord.COMPOSITIONS)
# datele care se comunică centrului militar când se schimbă
WATCHED = {"last_name": "numele", "first_name": "prenumele", "patronymic": "patronimicul", "address": "domiciliul",
           "address_actual": "reședința", "marital_status": "starea familială", "phone": "telefonul", "idnp": "IDNP"}
MILITARY_FIELDS = {"status": "starea evidenței", "category": "categoria", "group": "grupa", "composition": "componența",
                   "rank": "gradul", "specialty_code": "specialitatea militară", "center": "centrul militar", "fit": "aptitudinea",
                   "special_record": "evidența specială", "book": "livretul militar"}


def _people(p, look, day):
    """Angajații în funcție la data dată, cu raportul de bază (sau primul)."""
    out = {}
    for e, snap in jobs_on(p, day, look, kinds="all"):
        cur = out.get(e.employee_id)
        if cur is None or (e.kind in MAIN_KINDS and cur[0].kind not in MAIN_KINDS):
            out[e.employee_id] = (e, snap)
    return out


def _record_cells(m: MilitaryRecord, lang):
    return {"status": STATUS.get(m.status, ""), "category": m.category, "group": m.group.local_name(lang) if m.group_id else "",
            "composition": COMPOSITION.get(m.composition, ""), "rank": m.rank.local_name(lang) if m.rank_id else "",
            "specialty": m.specialty_code, "center": m.center.local_name(lang) if m.center_id else "",
            "fit": "apt" if m.fit else "inapt", "special": "da" if m.special_record else "", "book": m.book}


@report("military_register", "health", ("Registrul evidenței militare", "Реестр воинского учёта", "Military record register"),
        ("Recruții și rezerviștii angajați: categoria, grupa, componența, gradul, specialitatea, centrul militar, aptitudinea, "
         "evidența specială, livretul — registrul ținut de angajator.",
         "Призывники и военнообязанные: категория, группа, состав, звание, ВУС, военкомат, годность, бронь, военный билет.",
         "Recruits and reservists employed: category, group, rank, specialty, military centre, fitness, reservation."),
        ["on_date", "subdivision"], perm="military.view")
def military_register(p):
    look = Lookup(p.lang)
    people = _people(p, look, p.on_date)
    records = {m.employee_id: m for m in MilitaryRecord.objects.filter(employee_id__in=people, status__in=("liable", "recruit"))
               .select_related("group", "rank", "center")}
    rows = []
    for emp_id, m in records.items():
        e, snap = people[emp_id]
        emp = e.employee
        rows.append({"tab": emp.tab_number, "name": emp.full_name(), "birth": _d(emp.birth_date), "sub": look.sub(snap["subdivision_id"]),
                     "occ": look.occ(snap["occupation_id"]), **_record_cells(m, p.lang)})
    rows.sort(key=lambda r: (r["status"], r["name"]))
    recruits = sum(1 for m in records.values() if m.status == "recruit")
    return {
        "subtitle": subtitle_parts(p, f"{p.t(('la data de', 'на', 'as of'))} {p.on_date:%d.%m.%Y}"),
        "columns": [col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("birth", p.t(("Data nașterii", "Дата рождения", "Born")), "date"),
                    col("sub", p.t(COMMON["sub"])), col("occ", p.t(COMMON["occ"])), col("status", p.t(("Evidența", "Учёт", "Record"))),
                    col("category", p.t(("Cat.", "Кат.", "Cat."))), col("group", p.t(("Grupa", "Группа", "Group"))),
                    col("composition", p.t(("Componența", "Состав", "Composition"))), col("rank", p.t(("Gradul", "Звание", "Rank"))),
                    col("specialty", p.t(("Specialitatea", "ВУС", "Specialty"))), col("center", p.t(("Centrul militar", "Военкомат", "Centre"))),
                    col("fit", p.t(("Apt", "Годность", "Fit"))), col("special", p.t(("Ev. specială", "Бронь", "Reserved"))),
                    col("book", p.t(("Livretul", "Военный билет", "Book")))],
        "rows": rows,
        "summary": [{"label": p.t(("Rezerviști", "Военнообязанные", "Reservists")), "value": len(rows) - recruits},
                    {"label": p.t(("Recruți", "Призывники", "Recruits")), "value": recruits}],
    }


@report("military_missing", "health", ("Fără fișă de evidență militară", "Без карточки воинского учёта", "Without military record"),
        ("Bărbații de 16–60 de ani și femeile cu pregătire medicală de 18–50 de ani, angajați, care nu au fișa de evidență "
         "militară completată — de verificat livretul sau certificatul de recrutare.",
         "Мужчины 16–60 лет и женщины-медики 18–50 лет без карточки воинского учёта.",
         "Employees who should be on the military record but have no record."),
        ["on_date", "subdivision"], perm="military.view")
def military_missing(p):
    look = Lookup(p.lang)
    people = _people(p, look, p.on_date)
    have = set(MilitaryRecord.objects.filter(employee_id__in=people).values_list("employee_id", flat=True))
    rows = []
    for emp_id, (e, snap) in people.items():
        emp = e.employee
        if emp_id in have or not emp.birth_date:
            continue
        age = age_on(emp.birth_date, p.on_date)
        man = emp.sex == "M" and 16 <= age <= 60
        woman = emp.sex == "F" and 18 <= age <= 50 and look.category(snap["occupation_id"]) in MEDICAL
        if man or woman:
            rows.append({"tab": emp.tab_number, "name": emp.full_name(), "birth": _d(emp.birth_date), "age": age,
                         "sub": look.sub(snap["subdivision_id"]), "occ": look.occ(snap["occupation_id"])})
    rows.sort(key=lambda r: r["name"])
    return {
        "subtitle": subtitle_parts(p, f"{p.t(('la data de', 'на', 'as of'))} {p.on_date:%d.%m.%Y}"),
        "columns": [col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("birth", p.t(("Data nașterii", "Дата рождения", "Born")), "date"),
                    col("age", p.t(("Vârsta", "Возраст", "Age")), "int"), col("sub", p.t(COMMON["sub"])), col("occ", p.t(COMMON["occ"]))],
        "rows": rows,
    }


@report("military_changes", "health", ("Modificările lunii pentru centrul militar", "Изменения за месяц для военкомата",
                                       "Monthly changes for the military centre"),
        ("Recruții și rezerviștii angajați, eliberați, transferați în lună și schimbările datelor lor (nume, domiciliu, starea "
         "familială, datele de evidență) — informația lunară către centrul militar teritorial.",
         "Принятые, уволенные, переведённые военнообязанные и изменения их данных — ежемесячная информация в военкомат.",
         "Hired, dismissed, transferred reservists and changes of their data — the monthly report to the military centre."),
        ["month", "subdivision"], perm="military.view")
def military_changes(p):
    from apps.core.models import AuditLog

    look = Lookup(p.lang)
    first = date(p.year, p.month, 1)
    last = date(p.year, p.month, calendar.monthrange(p.year, p.month)[1])
    records = {m.employee_id: m for m in MilitaryRecord.objects.filter(status__in=("liable", "recruit")).select_related("employee", "center")}
    rows = []

    def add(emp, day, what, detail, sub_id, occ_id):
        if not p.allowed(sub_id):
            return
        m = records[emp.pk]
        rows.append({"date": _d(day), "tab": emp.tab_number, "name": emp.full_name(), "birth": _d(emp.birth_date),
                     "status": STATUS.get(m.status, ""), "center": m.center.local_name(p.lang) if m.center_id else "",
                     "what": what, "detail": detail, "sub": look.sub(sub_id), "occ": look.occ(occ_id)})

    jobs = Employment.objects.filter(employee_id__in=records, kind__in=MAIN_KINDS).select_related("employee").prefetch_related("history")
    for e in jobs.filter(date_from__range=(first, last)):
        s = snapshot(e, e.date_from)
        add(e.employee, e.date_from, "angajat", e.hire_order, s["subdivision_id"], s["occupation_id"])
    for e in jobs.filter(end_date__range=(first, last)):
        s = snapshot(e, e.end_date)
        add(e.employee, e.end_date, "eliberat", e.end_order, s["subdivision_id"], s["occupation_id"])
    for h in EmploymentHistory.objects.filter(event="change", date__range=(first, last), employment__in=jobs).select_related(
            "employment__employee").order_by("date", "id"):
        add(h.employment.employee, h.date, "transferat / altă funcție", h.order, h.subdivision_id, h.occupation_id)
    start = timezone.make_aware(datetime.combine(first, time.min))
    end = timezone.make_aware(datetime.combine(last, time.max))
    logs = AuditLog.objects.filter(timestamp__range=(start, end), action__in=("update", "create")).filter(
        model__in=("staff.Employee", "staff.MilitaryRecord", "staff.Education", "staff.FamilyMember"))
    for log in logs.order_by("timestamp"):
        emp_id = int(log.object_id) if log.model == "staff.Employee" else int(log.parent_id or 0)
        if emp_id not in records:
            continue
        if log.model == "staff.Employee":
            fields = [WATCHED[k] for k in log.changes if k in WATCHED] if log.action == "update" else []
        elif log.model == "staff.MilitaryRecord":
            fields = [MILITARY_FIELDS[k] for k in log.changes if k in MILITARY_FIELDS] if log.action == "update" else []
        elif log.model == "staff.Education":
            fields = ["studiile"] if log.action == "create" else []
        else:
            fields = ["familia"] if log.action == "create" else []
        if not fields:
            continue
        emp = records[emp_id].employee
        job = next((j for j in jobs if j.employee_id == emp_id and j.status != "ended"), None)
        if job is None:
            continue
        s = snapshot(job, log.timestamp.date())
        add(emp, timezone.localtime(log.timestamp).date(), "schimbarea datelor", ", ".join(dict.fromkeys(fields)),
            s["subdivision_id"], s["occupation_id"])
    rows.sort(key=lambda r: (r["date"], r["name"]))
    return {
        "subtitle": subtitle_parts(p, p.month_name()),
        "columns": [col("date", p.t(COMMON["date"]), "date"), col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])),
                    col("birth", p.t(("Data nașterii", "Дата рождения", "Born")), "date"), col("status", p.t(("Evidența", "Учёт", "Record"))),
                    col("what", p.t(("Modificarea", "Изменение", "Change"))), col("detail", p.t(("Detalii / ordinul", "Подробности / приказ", "Details"))),
                    col("sub", p.t(COMMON["sub"])), col("occ", p.t(COMMON["occ"])), col("center", p.t(("Centrul militar", "Военкомат", "Centre")))],
        "rows": rows,
    }


@report("military_recruits", "health", ("Lista recruților", "Список призывников", "List of recruits"),
        ("Angajații cu statutul de recrut și bărbații de 16–27 de ani — lista anuală pentru centrul militar.",
         "Работники-призывники и мужчины 16–27 лет — годовой список для военкомата.",
         "Recruit employees and men aged 16–27 — the annual list for the military centre."),
        ["on_date", "subdivision"], perm="military.view")
def military_recruits(p):
    look = Lookup(p.lang)
    people = _people(p, look, p.on_date)
    records = {m.employee_id: m for m in MilitaryRecord.objects.filter(employee_id__in=people).select_related("center")}
    rows = []
    for emp_id, (e, snap) in people.items():
        emp, m = e.employee, records.get(emp_id)
        young = emp.sex == "M" and emp.birth_date and 16 <= age_on(emp.birth_date, p.on_date) <= 27
        if (m and m.status == "recruit") or (young and (m is None or m.status != "not_liable")):
            rows.append({"tab": emp.tab_number, "name": emp.full_name(), "birth": _d(emp.birth_date), "address": emp.address,
                         "sub": look.sub(snap["subdivision_id"]), "occ": look.occ(snap["occupation_id"]),
                         "status": STATUS.get(m.status, "") if m else p.t(("fără fișă", "без карточки", "no record")),
                         "center": m.center.local_name(p.lang) if m and m.center_id else ""})
    rows.sort(key=lambda r: r["name"])
    return {
        "subtitle": subtitle_parts(p, f"{p.t(('la data de', 'на', 'as of'))} {p.on_date:%d.%m.%Y}"),
        "columns": [col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("birth", p.t(("Data nașterii", "Дата рождения", "Born")), "date"),
                    col("address", p.t(("Domiciliul", "Адрес", "Address"))), col("sub", p.t(COMMON["sub"])), col("occ", p.t(COMMON["occ"])),
                    col("status", p.t(("Evidența", "Учёт", "Record"))), col("center", p.t(("Centrul militar", "Военкомат", "Centre")))],
        "rows": rows,
    }
