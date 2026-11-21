"""Datele demo: un spital fictiv pentru prezentări — subdiviziuni, statele de personal, ~50 de angajați cu dosarele
completate (studii, categorii, EMC, examene medicale, evidența militară), concedii și cereri, un ordin semnat, pontajul și
calculul salariului pe luna trecută, câte un utilizator pentru fiecare rol. Totul trece prin serviciile modulelor, ca în lucru."""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone


class DemoError(Exception):
    pass


DEMO_PASSWORD = "Demo-Cadre-2026"

MEN = ["Ion", "Vasile", "Andrei", "Mihai", "Sergiu", "Victor", "Igor", "Dumitru", "Alexandru", "Nicolae", "Petru", "Vladimir",
       "Radu", "Eugen", "Valeriu"]
WOMEN = ["Ana", "Maria", "Elena", "Natalia", "Tatiana", "Svetlana", "Olga", "Irina", "Cristina", "Diana", "Lilia", "Aurelia",
         "Galina", "Victoria", "Mariana"]
SURNAMES = ["Popescu", "Rusu", "Ceban", "Lungu", "Moraru", "Ciobanu", "Rotaru", "Munteanu", "Cojocaru", "Sârbu", "Bivol",
            "Țurcanu", "Gheorghiță", "Bodrug", "Botnaru", "Croitoru", "Melnic", "Railean", "Stratan", "Cebotari", "Guțu",
            "Popa", "Grosu", "Vrabie", "Lupu", "Ursu", "Prodan", "Cazacu", "Roșca", "Mereuță"]

# subdiviziunea: (cod, denumirea, tipul, paturi, condiții vătămătoare, [(funcția, unități aprobate, salariul)])
STRUCTURE = [
    ("ADM", "Administrația", "department", 0, False, [("Director", 1, 32000), ("Director adjunct medical", 1, 28000),
                                                ("Contabil-șef", 1, 22000), ("Contabil", 2, 13500), ("Specialist resurse umane", 2, 12500),
                                                ("Economist", 1, 13000), ("Jurist", 1, 13000)]),
    ("TR1", "Secția traumatologie nr. 1", "section", 40, False, [("Șef secție — medic", 1, 24000), ("Medic traumatolog-ortoped", 5, 17500),
                                                                ("Asistent medical de secție", 8, 10500), ("Infermieră", 4, 7200)]),
    ("TR2", "Secția traumatologie nr. 2 (copii)", "section", 30, False, [("Șef secție — medic", 1, 24000),
                                                                        ("Medic traumatolog-ortoped", 4, 17500),
                                                                        ("Asistent medical de secție", 6, 10500), ("Infermieră", 3, 7200)]),
    ("ATI", "Secția anestezie și terapie intensivă", "section", 12, True, [("Șef secție — medic", 1, 25000),
                                                                           ("Medic anesteziolog-reanimatolog", 5, 19000),
                                                                           ("Asistent medical anestezist", 8, 11500), ("Infermieră", 3, 7600)]),
    ("BLO", "Blocul operator", "section", 0, False, [("Asistent medical de operație", 6, 11500), ("Infermieră de operație", 3, 7600)]),
    ("RAD", "Secția radiologie", "section", 0, True, [("Medic radiolog-imagist", 2, 18500), ("Laborant radiolog", 4, 10500)]),
    ("LAB", "Laboratorul clinic", "section", 0, False, [("Medic de laborator", 1, 17500), ("Laborant", 3, 9800)]),
    ("FAR", "Farmacia", "department", 0, False, [("Farmacist", 2, 14500)]),
    ("GOS", "Serviciul gospodăresc", "department", 0, False, [("Inginer", 1, 12000), ("Conducător auto", 2, 8500),
                                                           ("Bucătar", 2, 7500), ("Îngrijitor încăperi", 4, 6800)]),
]
# Funcțiile demo care nu mai sunt în clasificatorul livrat (S1 — fără funcții de spital): felul vechi al personalului (pentru
# datele demo) și grupa CORM (categoria de personal). Datele demo se refac pentru un SRL după unirea ramurilor S1.
DEMO_OCCUPATIONS = {
    "Director": ("leadership", "1"), "Director adjunct medical": ("leadership", "1"), "Contabil-șef": ("leadership", "1"),
    "Șef secție — medic": ("physicians", "2"), "Medic traumatolog-ortoped": ("physicians", "2"),
    "Medic anesteziolog-reanimatolog": ("physicians", "2"), "Medic radiolog-imagist": ("physicians", "2"),
    "Medic de laborator": ("physicians", "2"), "Medic de gardă": ("physicians", "2"), "Farmacist": ("pharmacists", "2"),
    "Asistent medical de secție": ("nurses", "3"), "Asistent medical anestezist": ("nurses", "3"),
    "Asistent medical de operație": ("nurses", "3"), "Laborant radiolog": ("nurses", "3"), "Laborant": ("nurses", "3"),
    "Infermieră": ("junior", "5"), "Infermieră de operație": ("junior", "5"),
}


def kind_of(occupation) -> str:
    """Felul vechi al personalului unei funcții demo (medici, asistenți...); celelalte — „admin”."""
    return DEMO_OCCUPATIONS.get(occupation.name_ro, ("admin", ""))[0]


def demo_occupations() -> dict:
    """Funcțiile din STRUCTURE, după denumire; cele care lipsesc din clasificator se adaugă."""
    from apps.org.models import STAFF_CATEGORY, DictItem, Occupation

    groups = {c.code: c for c in DictItem.objects.filter(kind=STAFF_CATEGORY)}
    found = {o.name_ro: o for o in Occupation.objects.all()}
    names = [name for *_rest, jobs in STRUCTURE for name, _units, _salary in jobs] + list(DEMO_OCCUPATIONS)
    for name in names:
        if name not in found:
            group = DEMO_OCCUPATIONS.get(name, ("admin", "2"))[1]
            found[name] = Occupation.objects.create(name_ro=name, category=groups.get(group), weekly_hours=35)
    return found


# câți oameni se angajează pe fiecare funcție (restul unităților rămân vacante)
FILL = 0.8

USERS = [("cadre", "hr_head", "Silvia", "Moraru"), ("inspector", "hr_inspector", "Lucia", "Rotaru"),
         ("director", "director", "Gheorghe", "Ciobanu"), ("sef.trauma", "department_head", "Andrei", "Munteanu"),
         ("contabil", "accountant", "Valentina", "Cojocaru"), ("angajat", "employee", "", "")]


def has_business_data() -> bool:
    from apps.staff.models import Employee

    return Employee.objects.exists()


def password() -> str:
    return DEMO_PASSWORD


def _idnp(rnd) -> str:
    return "2" + "".join(str(rnd.randint(0, 9)) for _ in range(12))


def _years_ago(rnd, today, lo, hi):
    return today - timedelta(days=rnd.randint(int(lo * 365), int(hi * 365)))


@transaction.atomic
def run(force=False):
    from apps.core import seed
    from apps.core.models import Company
    from apps.org.models import DictItem, Occupation, Specialty, StaffList, StaffListLine, Subdivision
    from apps.staff import services as staff
    from apps.staff.models import Education, Employee, FamilyMember, MilitaryRecord
    from apps.users.models import Role, User

    if has_business_data() and not force:
        raise DemoError("Baza are deja angajați; datele demo se pun doar într-o bază nouă (sau cu --force).")
    seed.run()
    rnd = random.Random(2026)
    today = timezone.localdate()
    company = Company.get()
    for field, value in (("director", "Gheorghe Ciobanu"), ("chief_accountant", "Valentina Cojocaru"),
                         ("hr_head", "Silvia Moraru"), ("legal_address", "mun. Chișinău, str. Demo 1"), ("phone", "022 000 000")):
        if not getattr(company, field):
            setattr(company, field, value)
    company.save()

    occupations = demo_occupations()
    specialties = list(Specialty.objects.all()[:10]) or [Specialty.objects.create(name_ro=n) for n in (
        "Ortopedie și traumatologie", "Anesteziologie și reanimatologie", "Asistent medical generalist")]
    edu = {c.code: c for c in DictItem.objects.filter(kind="education")}
    family = {c.code: c for c in DictItem.objects.filter(kind="family")}
    groups = list(DictItem.objects.filter(kind="military_group"))
    nations = list(DictItem.objects.filter(kind="nationality").order_by("sort"))[:4]
    marital = list(DictItem.objects.filter(kind="marital"))
    center, _ = DictItem.objects.get_or_create(kind="military_center", name_ro="Centrul militar teritorial Buiucani")

    subs, lines = {}, []
    for i, (code, name, kind, beds, harmful, _jobs) in enumerate(STRUCTURE):
        subs[code] = Subdivision.objects.create(code=code, name_ro=name, kind=kind, harmful=harmful,
                                                extra_leave_days=7 if harmful else 0, sort=(i + 1) * 10)
    sl = StaffList.objects.create(number="1", date=today.replace(month=1, day=1), effective_from=today.replace(month=1, day=1),
                                  approved_by="Ordinul Ministerului Sănătății (demo)", status="approved")
    for code, *_rest, jobs in STRUCTURE:
        for occ_name, units, salary in jobs:
            occ = occupations[occ_name]
            lines.append(StaffListLine(staff_list=sl, subdivision=subs[code], occupation=occ, units=Decimal(units),
                                       base_salary=Decimal(salary)))
    StaffListLine.objects.bulk_create(lines)

    used, people, tab = set(), [], 0

    def name(sex):
        while True:
            pair = (rnd.choice(SURNAMES), rnd.choice(MEN if sex == "M" else WOMEN))
            if pair not in used:
                used.add(pair)
                return pair

    for code, *_rest, jobs in STRUCTURE:
        for occ_name, units, salary in jobs:
            occ = occupations[occ_name]
            for _ in range(max(1, round(units * FILL))):
                tab += 1
                female = rnd.random() < (0.85 if kind_of(occ) in ("nurses", "junior") else 0.5)
                sex = "F" if female else "M"
                last, first = name(sex)
                birth = _years_ago(rnd, today, 24, 62)
                emp = Employee.objects.create(
                    tab_number=str(tab), last_name=last, first_name=first, sex=sex, birth_date=birth, idnp=_idnp(rnd),
                    phone=f"069{rnd.randint(100000, 999999)}", email=f"{first.lower()}.{last.lower()}@demo.md".replace("ș", "s").replace("ț", "t")
                    .replace("â", "a").replace("ă", "a").replace("î", "i"), address=f"mun. Chișinău, str. {rnd.choice(SURNAMES)} {rnd.randint(1, 120)}",
                    citizenship="Republica Moldova", nationality=rnd.choice(nations) if nations else None,
                    marital_status=rnd.choice(marital) if marital else None)
                hired = max(_years_ago(rnd, today, 0.3, 25), birth + timedelta(days=365 * 22))
                job = staff.hire(emp, kind="main", subdivision=subs[code], occupation=occ, rate=Decimal("1"),
                                 base_salary=Decimal(salary), date_from=hired, contract_number=f"{tab}/{hired.year}", contract_date=hired,
                                 probation_until=hired + timedelta(days=90) if (today - hired).days < 80 else None)
                people.append((emp, job))
                medical = kind_of(occ) in ("physicians", "nurses", "pharmacists")
                level = "higher" if kind_of(occ) in ("physicians", "pharmacists", "leadership") else (
                    "vocational" if kind_of(occ) == "nurses" else "secondary")
                Education.objects.create(employee=emp, level=edu.get(level), institution=(
                    "USMF „Nicolae Testemițanu”" if level == "higher" else "Colegiul de Medicină din Chișinău" if level == "vocational"
                    else "Liceul teoretic"), year_to=min(hired.year, birth.year + 23), specialty=rnd.choice(specialties) if medical else None)
                if rnd.random() < 0.35:
                    FamilyMember.objects.create(employee=emp, relation=family.get(rnd.choice(["son", "daughter"])), full_name=f"{last} {rnd.choice(MEN + WOMEN)}",
                                                birth_date=_years_ago(rnd, today, 1, 17), dependent=True)
                if sex == "M" and today.year - birth.year <= 55 or (female and medical and today.year - birth.year <= 45 and rnd.random() < 0.5):
                    MilitaryRecord.objects.create(employee=emp, status="recruit" if today.year - birth.year < 27 else "liable",
                                                  category="2", group=rnd.choice(groups) if groups else None,
                                                  composition="medical" if medical else "soldiers", center=center,
                                                  book=f"AA {rnd.randint(100000, 999999)}")
    _cumul(people, subs, occupations, staff, rnd, today)
    _activity(people, subs, rnd, today)
    users = _users(people, subs, Role, User)
    return {"employees": len(people), "users": users, "password": DEMO_PASSWORD}


def _cumul(people, subs, occupations, staff, rnd, today):
    """Câteva cumuluri interne (50 % / 25 %) și un contract de prestări servicii."""
    from apps.staff.models import Employee

    doctors = [e for e, j in people if kind_of(j.occupation) == "physicians" and j.subdivision.code in ("TR1", "TR2")]
    for emp in doctors[:3]:
        staff.hire(emp, kind="internal", subdivision=subs["ATI" if rnd.random() < 0.5 else "RAD"],
                   occupation=occupations["Medic de gardă"], rate=Decimal("0.5"), base_salary=Decimal("17500"),
                   combination_pct=Decimal("0"), date_from=today.replace(day=1) - timedelta(days=200))
    nurses = [e for e, j in people if kind_of(j.occupation) == "nurses"]
    for emp in nurses[:2]:
        staff.hire(emp, kind="internal", subdivision=subs["BLO"], occupation=occupations["Asistent medical de operație"],
                   rate=Decimal("0.25"), base_salary=Decimal("11500"), date_from=today.replace(day=1) - timedelta(days=120))
    ext = Employee.objects.create(tab_number=str(len(people) + 1), last_name="Vrabie", first_name="Tudor", sex="M",
                                  birth_date=date(today.year - 52, 4, 12))
    staff.hire(ext, kind="contractor", subdivision=subs["GOS"], occupation=occupations["Inginer"], rate=Decimal("0.5"),
               base_salary=Decimal("0"), date_from=today.replace(month=1, day=1))


def _activity(people, subs, rnd, today):
    """Concedii, cereri, formare, examene medicale, un ordin semnat, pontajul și salariul lunii trecute."""
    from apps.health.models import MedicalExam, SafetyBriefing
    from apps.leave.models import Absence, LeaveRequest
    from apps.org.models import DictItem, OrderType
    from apps.orders import services as order_services
    from apps.orders.models import OrderItem
    from apps.payroll import engine
    from apps.payroll.models import Payroll
    from apps.training.models import TrainingRecord
    from apps.worktime import services as worktime
    from apps.worktime.models import Timesheet

    first_this = today.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    first_prev = last_prev.replace(day=1)
    # evidența concediilor pornește de la 1 ianuarie anul trecut (ca la o întreprindere nouă în program)
    from apps.leave import balance

    balance.save_settings({"start_date": date(today.year - 1, 1, 1).isoformat()})
    for i, (emp, job) in enumerate(people):
        if i % 6 != 5:
            done = today - timedelta(days=rnd.randint(30, 380))
            MedicalExam.objects.create(employee=emp, kind="periodic", date=done, next_date=done + timedelta(days=365),
                                       institution="Centrul de medicină a muncii", conclusion="fit")
        SafetyBriefing.objects.create(employee=emp, kind="periodic", date=today - timedelta(days=rnd.randint(20, 200)),
                                      next_date=today + timedelta(days=rnd.randint(-10, 160)), instructor="Inginer SSM")
        if kind_of(job.occupation) in ("physicians", "nurses", "pharmacists"):
            for _ in range(rnd.randint(1, 4)):
                start = today - timedelta(days=rnd.randint(20, 1500))
                TrainingRecord.objects.create(employee=emp, kind=rnd.choice(["course", "conference", "seminar", "online"]),
                                              title=rnd.choice(["Actualități în traumatologie și ortopedie", "Urgențe medicale",
                                                                "Controlul infecțiilor", "Anestezia regională", "Congresul medicilor"]),
                                              provider=rnd.choice(["USMF „Nicolae Testemițanu”", "Centrul de excelență în medicină",
                                                                   "Societatea de ortopedie"]),
                                              date_from=start, date_to=start + timedelta(days=rnd.randint(0, 9)),
                                              hours=rnd.choice([8, 16, 36, 72]))
        # concediile: cei mai mulți și-au luat concediul anul trecut, o parte și luna trecută (anul de muncă — cel mai vechi cu sold)
        for start in ([date(today.year - 1, rnd.randint(6, 8), rnd.randint(1, 20))] if i % 5 else []) + (
                [first_prev + timedelta(days=rnd.randint(0, 10))] if i % 4 == 0 else []):
            if start <= job.date_from:
                continue
            year_from, year_to = balance.Calculator(start).suggest_work_year(emp)
            Absence.objects.create(employee=emp, employment=job, kind="annual", date_from=start, date_to=start + timedelta(days=27),
                                   days=28, work_year_from=year_from, work_year_to=year_to)
        if i % 9 == 3:
            Absence.objects.create(employee=emp, employment=job, kind="annual", date_from=today - timedelta(days=2),
                                   date_to=today + timedelta(days=11), days=14)
        if i % 11 == 7:
            Absence.objects.create(employee=emp, employment=job, kind="sick", date_from=today - timedelta(days=3),
                                   date_to=today + timedelta(days=4), days=8)
        if i in (2, 13, 21):
            start = today + timedelta(days=30 + i)
            LeaveRequest.objects.create(employee=emp, kind="annual", date_from=start, date_to=start + timedelta(days=13), days=14,
                                        reason="Concediu de odihnă anual")
    # ordinul de premiere (colectiv, semnat)
    bonus = OrderType.objects.filter(code="bonus").first()
    if bonus is not None:
        order = order_services.new_order(bonus, date=first_prev + timedelta(days=20))
        for n, (emp, _job) in enumerate(people[3:9], start=1):
            item = OrderItem.objects.create(order=order, employee=emp, params={"amount": "1000", "note": "pentru activitatea din luna"},
                                            sort=n * 10)
            order_services.refresh_text(item)
            item.save(update_fields=["text"])
        order_services.sign(order)
    # pontajul și calculul salariului pe luna trecută
    for sub in subs.values():
        worktime.fill_timesheet(Timesheet.objects.create(subdivision=sub, year=first_prev.year, month=first_prev.month))
    payroll = Payroll.objects.create(year=first_prev.year, month=first_prev.month)
    engine.calculate(payroll)
    payroll.status = "approved"
    payroll.save(update_fields=["status"])


def _users(people, subs, Role, User):
    """Câte un utilizator pentru fiecare rol (aceeași parolă demo); „angajat” e legat de un angajat din traumatologie."""
    out = []
    for username, role, first, last in USERS:
        if User.objects.filter(username=username).exists():
            continue
        if role == "employee":
            emp = next(e for e, j in people if j.subdivision.code == "TR1" and kind_of(j.occupation) == "physicians" and e.user_id is None)
            first, last = emp.first_name, emp.last_name
        user = User.objects.create_user(username=username, password=DEMO_PASSWORD, first_name=first, last_name=last,
                                        email=f"{username}@demo.md")
        user.roles.set(Role.objects.filter(code=role))
        if role == "department_head":
            subs["TR1"].users.add(user)
        if role == "employee":
            emp.user = user
            emp.save(update_fields=["user"])
        out.append(username)
    return out
