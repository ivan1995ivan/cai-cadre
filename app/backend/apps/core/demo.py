"""Datele demo: o întreprindere privată fictivă („Demo Producție” SRL — fabricarea de construcții metalice) pentru prezentări.

Subdiviziunile (administrația, contabilitatea, vânzările, atelierul de producție cu două sectoare — unul cu condiții
vătămătoare —, depozitul, transportul), statele de personal aprobate prin ordinul directorului, ~70 de angajați cu dosarele
completate (actele, familia, studiile, stagiul anterior), raporturile de muncă (de bază, cumul intern / extern, un contract de
prestări servicii), turele de zi / noapte din atelier, concedii și cereri, foi de boală, examenele medicale și instructajele SSM,
formarea profesională, un ordin de premiere semnat, pontajul și salariul lunii trecute (calculul aprobat, îndreptarea
achitată) și câte un utilizator pentru fiecare rol. Funcțiile se iau din clasificatorul livrat (CORM 006-2021); nimic nu se
inventează local. Totul trece prin serviciile modulelor, ca în lucru."""
import random
import unicodedata
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone


class DemoError(Exception):
    pass


DEMO_PASSWORD = "Demo-Cadre-2026"
DEMO_DOMAIN = "demo-productie.example"  # domeniul rezervat (RFC 2606): e-mailurile demo nu ajung la nimeni real

# Constantele firmei; se completează doar câmpurile goale (ce s-a scris în asistentul de instalare rămâne)
COMPANY = {
    "name_ro": "Demo Producție", "name_ru": "Демо Производство", "name_en": "Demo Production", "legal_form": "SRL",
    "idno": "1000000000000",  # fictiv, evident
    "caem": "2511",  # fabricarea de construcții metalice și părți componente ale structurilor metalice
    "legal_address": "MD-2000, mun. Chișinău, str. Exemplului 1", "phone": "022 000 000", "email": f"office@{DEMO_DOMAIN}",
    "director": "Gheorghe Ciobanu", "director_position_ro": "Director", "director_position_ru": "Директор",
    "chief_accountant": "Valentina Cojocaru", "hr_head": "Silvia Moraru",
}
DEFAULT_COMPANY_NAME = "Firma mea"  # denumirea pusă de Company.get() pe o bază fără asistent
COMPANY_IBAN = ("MD00AG000000000000000000", "BC „Moldova-Agroindbank” S.A.", "AGRNMD2X")

MEN = ["Ion", "Vasile", "Andrei", "Mihai", "Sergiu", "Victor", "Igor", "Dumitru", "Alexandru", "Nicolae", "Petru", "Vladimir",
       "Radu", "Eugen", "Valeriu"]
WOMEN = ["Ana", "Maria", "Elena", "Natalia", "Tatiana", "Svetlana", "Olga", "Irina", "Cristina", "Diana", "Lilia", "Aurelia",
         "Galina", "Victoria", "Mariana"]
SURNAMES = ["Popescu", "Rusu", "Ceban", "Lungu", "Moraru", "Ciobanu", "Rotaru", "Munteanu", "Cojocaru", "Sârbu", "Bivol",
            "Țurcanu", "Gheorghiță", "Bodrug", "Botnaru", "Croitoru", "Melnic", "Railean", "Stratan", "Cebotari", "Guțu",
            "Popa", "Grosu", "Vrabie", "Lupu", "Ursu", "Prodan", "Cazacu", "Roșca", "Mereuță"]

# subdiviziunea: (cod, codul părintelui, denumirea, felul, condiții vătămătoare, [(funcția din clasificator, unități, salariul)])
STRUCTURE = [
    ("ADM", "", "Administrația", "department", False, [
        ("Director al întreprinderii", 1, 35000), ("Director adjunct", 1, 28000), ("Specialist în resurse umane", 2, 14000),
        ("Jurist", 1, 16000), ("Secretar", 1, 9500), ("Inginer securitate și sănătate în muncă", 1, 15000),
        ("Administrator rețea de calculatoare", 1, 17000), ("Îngrijitor încăperi", 2, 7000)]),
    ("CONT", "", "Contabilitatea", "section", False, [
        ("Contabil-șef", 1, 26000), ("Contabil", 3, 15000), ("Economist", 1, 15000), ("Casier", 1, 9000)]),
    ("VNZ", "", "Vânzări", "section", False, [
        ("Manager în vânzări", 2, 18000), ("Agent de vânzări", 5, 12000), ("Operator call center", 2, 9500),
        ("Merceolog", 1, 11000)]),
    ("ATL", "", "Atelierul de producție", "workshop", False, [
        ("Inginer în industrie și producție", 1, 20000), ("Inginer tehnolog în industrie și producție", 1, 18000),
        ("Dispecer în programare și supraveghere a producției", 1, 11000), ("Lăcătuș-reparator instalații tehnologice", 2, 12500),
        ("Electrician echipamente electrice și energetice", 1, 12500)]),
    ("ATL1", "ATL", "Sectorul de prelucrare mecanică", "workshop", False, [
        ("Maistru în industria prelucrătoare", 2, 15000), ("Operator la mașini și utilaje în alte ramuri", 12, 11500),
        ("Ambalator manual", 3, 8000), ("Muncitor auxiliar", 2, 7500)]),
    ("ATL2", "ATL", "Sectorul de sudură și vopsire", "workshop", True, [
        ("Maistru în industria prelucrătoare", 1, 15500), ("Sudor", 6, 13500),
        ("Operator la mașini și utilaje în alte ramuri", 2, 12000)]),
    ("DEP", "", "Depozitul", "warehouse", False, [
        ("Magaziner", 3, 10000), ("Expeditor-logistician în transporturi", 1, 11000), ("Muncitor auxiliar", 2, 7500)]),
    ("TRN", "", "Transportul", "section", False, [
        ("Dispecer în transporturi", 1, 11000), ("Conducător de autocamion", 5, 13000), ("Conducător auto", 2, 11000),
        ("Mecanic auto", 1, 12500)]),
]
HARMFUL_EXTRA_LEAVE_DAYS = 4  # concediul suplimentar pentru condiții vătămătoare (CM art. 121)
HARMFUL_WEEKLY_HOURS = Decimal("35")  # durata redusă a timpului de muncă (CM art. 96)
SHIFT_SECTOR = "ATL1"  # operatorii lucrează pe ture de 12 ore (zi / noapte)
SHIFT_OCCUPATION = "Operator la mașini și utilaje în alte ramuri"
PRODUCTION = ("ATL", "ATL1", "ATL2", "DEP", "TRN")  # subdiviziunile cu examen medical periodic și cursuri tehnice

# persoanele-cheie: (subdiviziunea, funcția, al câtelea pe funcție) → (sexul, numele, prenumele)
KEY_PEOPLE = {
    ("ADM", "Director al întreprinderii", 0): ("M", "Ciobanu", "Gheorghe"),
    ("ADM", "Specialist în resurse umane", 0): ("F", "Moraru", "Silvia"),
    ("ADM", "Specialist în resurse umane", 1): ("F", "Rotaru", "Lucia"),
    ("CONT", "Contabil-șef", 0): ("F", "Cojocaru", "Valentina"),
    ("ATL", "Inginer în industrie și producție", 0): ("M", "Munteanu", "Andrei"),
}
HEADS = {"ADM": "Gheorghe Ciobanu", "CONT": "Valentina Cojocaru", "ATL": "Andrei Munteanu"}  # șefii subdiviziunilor

# câte femei sunt, de obicei, pe funcție (restul — bărbați); implicit 0.5, muncitorii și șoferii — 0.1
FEMALE_SHARE = {"Contabil-șef": 0.9, "Contabil": 0.85, "Economist": 0.7, "Casier": 0.9, "Specialist în resurse umane": 0.9,
                "Secretar": 0.95, "Operator call center": 0.8, "Îngrijitor încăperi": 0.85, "Ambalator manual": 0.6,
                "Merceolog": 0.7, "Magaziner": 0.4}
WORKER_GROUPS = ("7", "8")  # grupele CORM ale muncitorilor calificați și ale operatorilor / conducătorilor auto

# studiile după funcție: (nivelul, instituția, specialitatea, felul specialității)
UTM, ASEM, ULIM = "Universitatea Tehnică a Moldovei", "Academia de Studii Economice a Moldovei", \
    "Universitatea Liberă Internațională din Moldova"
POLY, SCHOOL, LYCEUM = "Colegiul Politehnic din Chișinău", "Școala profesională nr. 3 din Chișinău", "Liceul teoretic"
MECH = "Inginerie și management în construcția de mașini"
STUDIES = {
    "Director al întreprinderii": ("higher", UTM, MECH, "higher"),
    "Director adjunct": ("higher", ASEM, "Business și administrare", "higher"),
    "Specialist în resurse umane": ("higher", ASEM, "Business și administrare", "higher"),
    "Jurist": ("higher", ULIM, "Drept", "higher"),
    "Secretar": ("vocational", POLY, "Birotică", "postsecondary"),
    "Inginer securitate și sănătate în muncă": ("higher", UTM, "Inginerie și management în transporturi", "higher"),
    "Administrator rețea de calculatoare": ("higher", UTM, "Tehnologia informației", "higher"),
    "Programator": ("higher", UTM, "Tehnologia informației", "higher"),
    "Contabil-șef": ("higher", ASEM, "Contabilitate", "higher"),
    "Contabil": ("higher", ASEM, "Contabilitate", "higher"),
    "Economist": ("higher", ASEM, "Economie generală", "higher"),
    "Casier": ("vocational", POLY, "Contabilitate", "postsecondary"),
    "Manager în vânzări": ("higher", ASEM, "Marketing și logistică", "higher"),
    "Agent de vânzări": ("higher", ASEM, "Marketing și logistică", "higher"),
    "Operator call center": ("secondary", LYCEUM, "", ""),
    "Merceolog": ("vocational", POLY, "Merceologie", "postsecondary"),
    "Inginer în industrie și producție": ("higher", UTM, MECH, "higher"),
    "Inginer tehnolog în industrie și producție": ("higher", UTM, MECH, "higher"),
    "Dispecer în programare și supraveghere a producției": ("vocational", POLY, "Tehnologia construcțiilor de mașini",
                                                            "postsecondary"),
    "Lăcătuș-reparator instalații tehnologice": ("vocational", POLY, "Electromecanică", "postsecondary"),
    "Electrician echipamente electrice și energetice": ("vocational", POLY, "Electromecanică", "postsecondary"),
    "Maistru în industria prelucrătoare": ("vocational", POLY, "Tehnologia construcțiilor de mașini", "postsecondary"),
    "Operator la mașini și utilaje în alte ramuri": ("secondary", SCHOOL, "Operator la mașini-unelte cu comandă numerică",
                                                     "secondary"),
    "Sudor": ("secondary", SCHOOL, "Sudor", "secondary"),
    "Magaziner": ("vocational", POLY, "Merceologie", "postsecondary"),
    "Expeditor-logistician în transporturi": ("higher", ASEM, "Marketing și logistică", "higher"),
    "Dispecer în transporturi": ("vocational", POLY, "Transport auto", "postsecondary"),
    "Conducător de autocamion": ("secondary", SCHOOL, "Mecanic auto, conducător auto", "secondary"),
    "Conducător auto": ("secondary", SCHOOL, "Mecanic auto, conducător auto", "secondary"),
    "Mecanic auto": ("secondary", SCHOOL, "Mecanic auto, conducător auto", "secondary"),
}
DRIVERS = ("Conducător de autocamion", "Conducător auto")
PREVIOUS_EMPLOYERS = ["„Alfa Demo” SRL", "„Beta Demo” SA", "„Gama Demo” SRL", "„Delta Demo” SRL"]
CLINIC = "Centrul de sănătate „Demo” SRL"  # fictiv: examenele medicale periodice (SSM)
# formarea profesională: (denumirea, organizatorul, ore); „production” — pentru atelier, depozit, transport
COURSES = {
    "production": [("Securitatea și sănătatea în muncă la locul de muncă", "Centrul de instruire „Demo SSM”", 16),
                   ("Sudarea MIG / MAG — perfecționare", "Centrul de formare profesională „Demo Tehnic”", 40),
                   ("Programarea mașinilor-unelte cu comandă numerică", "Centrul de formare profesională „Demo Tehnic”", 72),
                   ("Conducerea preventivă și transportul mărfurilor", "Școala auto „Demo”", 24)],
    "office": [("Codul muncii în 2026: modificările Legii nr. 193/2025", "Centrul de instruire „Demo Consult”", 8),
               ("Salariul, IPC21 și IALS21 în practică", "Centrul de instruire „Demo Consult”", 16),
               ("Tehnici de vânzare B2B", "Centrul de formare „Demo Business”", 24),
               ("Protecția datelor cu caracter personal (Legea nr. 195/2024)", "Centrul de instruire „Demo Consult”", 8)],
}

# câți oameni se angajează pe fiecare funcție (restul unităților rămân vacante)
FILL = 0.8

# (login, rolul, prenumele, numele); „angajat” primește numele angajatului de care e legat
USERS = [("cadre", "hr_head", "Silvia", "Moraru"), ("inspector", "hr_inspector", "Lucia", "Rotaru"),
         ("director", "director", "Gheorghe", "Ciobanu"), ("sef.productie", "department_head", "Andrei", "Munteanu"),
         ("contabil", "accountant", "Valentina", "Cojocaru"), ("angajat", "employee", "", "")]
ADMIN_USERNAME = "admin"  # se creează doar dacă baza nu are niciun administrator (crm_demo fără asistentul de instalare)


def has_business_data() -> bool:
    from apps.staff.models import Employee

    return Employee.objects.exists()


def password() -> str:
    return DEMO_PASSWORD


def group_of(occupation) -> str:
    """Grupa majoră CORM a funcției (prima cifră a codului; fără cod — codul categoriei de personal)."""
    if occupation.code[:1].isdigit():
        return occupation.code[:1]
    return occupation.category.code if occupation.category_id else ""


def is_production(subdivision) -> bool:
    return subdivision.code in PRODUCTION


def _idnp(rnd) -> str:
    return "2" + "".join(str(rnd.randint(0, 9)) for _ in range(12))


def _years_ago(rnd, today, lo, hi):
    return today - timedelta(days=rnd.randint(int(lo * 365), int(hi * 365)))


def _ascii(text: str) -> str:
    """Fără diacritice și cu litere mici (pentru adresele de e-mail)."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(ch))


def occupations() -> dict:
    """Funcțiile din STRUCTURE și cele folosite de datele demo, după denumire, din clasificatorul livrat (`org/seed.py`)."""
    from apps.org.models import Occupation

    names = {name for *_rest, jobs in STRUCTURE for name, _units, _salary in jobs} | {"Programator"}
    found = {}
    for name in sorted(names):
        occ = Occupation.objects.filter(name_ro=name).order_by("deletion_mark", "id").first()
        if occ is None:
            raise DemoError(f"Funcția „{name}” lipsește din clasificatorul funcțiilor; datele demo se pun pe clasificatorul livrat.")
        found[name] = occ
    return found


def _fill_company():
    from apps.core.models import BankAccount, Company

    company = Company.get()
    for field, value in COMPANY.items():
        current = getattr(company, field)
        if not current or (field == "name_ro" and current == DEFAULT_COMPANY_NAME):
            setattr(company, field, value)
    company.save()
    if not company.bank_accounts.exists():
        iban, bank, bic = COMPANY_IBAN
        BankAccount.objects.create(company=company, iban=iban, bank_name=bank, bic=bic, is_default=True)
    return company


@transaction.atomic
def run(force=False):
    from apps.core import seed
    from apps.org.models import Specialty, StaffList, StaffListLine, Subdivision
    from apps.staff import services as staff
    from apps.staff.models import Employee
    from apps.users.models import Role, User

    if has_business_data() and not force:
        raise DemoError("Baza are deja angajați; datele demo se pun doar într-o bază nouă (sau cu --force).")
    seed.run()
    rnd = random.Random(2026)
    today = timezone.localdate()
    _fill_company()
    occ = occupations()
    specialties = {}
    for level, _inst, name, kind in STUDIES.values():
        if name and name not in specialties:
            specialties[name], _ = Specialty.objects.get_or_create(name_ro=name, defaults={"kind": kind})

    subs = {}
    for i, (code, parent, name, kind, harmful, _jobs) in enumerate(STRUCTURE):
        subs[code] = Subdivision.objects.create(
            code=code, name_ro=name, kind=kind, parent=subs.get(parent), harmful=harmful, sort=(i + 1) * 10,
            extra_leave_days=HARMFUL_EXTRA_LEAVE_DAYS if harmful else 0, reduced_hours=HARMFUL_WEEKLY_HOURS if harmful else None,
            head_name=HEADS.get(code, ""))
    first_jan = today.replace(month=1, day=1)
    sl = StaffList.objects.create(number="1", date=first_jan - timedelta(days=5), effective_from=first_jan,
                                  basis="Structura organizatorică a întreprinderii, regulamentul de salarizare")
    lines = []
    for code, *_rest, jobs in STRUCTURE:
        for n, (occ_name, units, salary) in enumerate(jobs, start=1):
            lines.append(StaffListLine(staff_list=sl, subdivision=subs[code], occupation=occ[occ_name], units=Decimal(units),
                                       base_salary=Decimal(salary), sort=n * 10))
    StaffListLine.objects.bulk_create(lines)

    used = {(last, first) for _sex, last, first in KEY_PEOPLE.values()}
    people = []

    def name(sex):
        while True:
            pair = (rnd.choice(SURNAMES), rnd.choice(MEN if sex == "M" else WOMEN))
            if pair not in used:
                used.add(pair)
                return pair

    ctx = _Dossier(rnd, today, specialties)
    for code, *_rest, jobs in STRUCTURE:
        for occ_name, units, salary in jobs:
            for k in range(max(1, round(units * FILL))):
                key = KEY_PEOPLE.get((code, occ_name, k))
                if key:
                    sex, last, first = key
                else:
                    workers = group_of(occ[occ_name]) in WORKER_GROUPS
                    sex = "F" if rnd.random() < FEMALE_SHARE.get(occ_name, 0.1 if workers else 0.5) else "M"
                    last, first = name(sex)
                emp = ctx.person(len(people) + 1, last, first, sex, occ_name, min_age=30 if key else 21)
                hired = max(_years_ago(rnd, today, 0.3, 18), emp.birth_date + timedelta(days=365 * 20))
                job = staff.hire(emp, kind="main", subdivision=subs[code], occupation=occ[occ_name], rate=Decimal("1"),
                                 base_salary=Decimal(salary), date_from=hired, contract_number=f"{emp.tab_number}/{hired.year}",
                                 contract_date=hired, probation_until=hired + timedelta(days=90) if (today - hired).days < 80 else None)
                people.append((emp, job))
    _cumul(people, subs, occ, staff, ctx, today)
    users = _users(people, subs, Role, User)
    _staff_list_order(sl, users)
    _shifts(people, today)
    _activity(people, subs, rnd, today, users)
    return {"employees": len(people), "persons": Employee.objects.count(), "subdivisions": len(subs), "users": list(users),
            "password": DEMO_PASSWORD}


class _Dossier:
    """Dosarul unei persoane: datele personale, buletinul, studiile, familia, stagiul anterior, evidența militară."""

    def __init__(self, rnd, today, specialties):
        from apps.org.models import DictItem

        self.rnd, self.today, self.specialties = rnd, today, specialties
        dicts = {}
        for item in DictItem.objects.filter(kind__in=("education", "family", "document", "marital", "military_group")):
            dicts.setdefault(item.kind, {})[item.code] = item
        self.edu, self.family, self.docs = dicts.get("education", {}), dicts.get("family", {}), dicts.get("document", {})
        self.marital = dicts.get("marital", {})
        self.groups = list(dicts.get("military_group", {}).values())
        self.nations = list(DictItem.objects.filter(kind="nationality").order_by("sort"))[:4]
        self.center, _ = DictItem.objects.get_or_create(kind="military_center", name_ro="Centrul militar teritorial Buiucani")

    def person(self, tab, last, first, sex, occ_name, min_age=21):
        from apps.staff.models import Education, Employee, EmployeeDocument, FamilyMember, MilitaryRecord, PriorExperience

        rnd, today = self.rnd, self.today
        birth = _years_ago(rnd, today, min_age, 60)
        age = today.year - birth.year
        married = age > 26 and rnd.random() < 0.65
        status = self.marital.get("married" if married else rnd.choice(["single", "single", "divorced"]))
        emp = Employee.objects.create(
            tab_number=str(tab), last_name=last, first_name=first, sex=sex, birth_date=birth, idnp=_idnp(rnd),
            birth_place=rnd.choice(["mun. Chișinău", "mun. Bălți", "or. Orhei", "or. Ialoveni", "or. Strășeni"]),
            phone=f"069{rnd.randint(100000, 999999)}", email=f"{_ascii(first)}.{_ascii(last)}@{DEMO_DOMAIN}",
            address=f"mun. Chișinău, str. {rnd.choice(SURNAMES)} {rnd.randint(1, 120)}", citizenship="Republica Moldova",
            nationality=rnd.choice(self.nations) if self.nations else None, marital_status=status)
        issued = today - timedelta(days=rnd.randint(200, 3400))
        EmployeeDocument.objects.create(employee=emp, doc_type=self.docs.get("id_card"), series="B",
                                        number=str(rnd.randint(10**8, 10**9 - 1)), issued_by="ASP", issue_date=issued,
                                        expiry_date=issued + timedelta(days=3652), is_identity=True)
        if occ_name in DRIVERS or occ_name == "Mecanic auto":
            got = today - timedelta(days=rnd.randint(300, 3000))
            EmployeeDocument.objects.create(employee=emp, doc_type=self.docs.get("driving_licence"), series="MDA",
                                            number=str(rnd.randint(10**6, 10**7 - 1)), issued_by="ASP", issue_date=got,
                                            expiry_date=got + timedelta(days=3652), note="Categoriile B, C, CE")
        level, institution, specialty, _kind = STUDIES.get(occ_name, ("secondary", LYCEUM, "", ""))
        graduated = birth.year + (22 if level == "higher" else 19 if level == "vocational" else 18)
        Education.objects.create(employee=emp, level=self.edu.get(level), institution=institution,
                                 specialty=self.specialties.get(specialty), year_from=graduated - (4 if level == "higher" else 3),
                                 year_to=graduated, diploma_number=str(rnd.randint(100000, 999999)) if specialty else "")
        if married:
            FamilyMember.objects.create(employee=emp, relation=self.family.get("wife" if sex == "M" else "husband"),
                                        full_name=f"{last} {rnd.choice(WOMEN if sex == 'M' else MEN)}",
                                        birth_date=birth + timedelta(days=rnd.randint(-1500, 1500)))
            for _ in range(rnd.choice([0, 1, 1, 2, 2, 3]) if age < 52 else 0):
                child_age = rnd.randint(1, min(17, max(1, age - 22)))
                FamilyMember.objects.create(employee=emp, relation=self.family.get(rnd.choice(["son", "daughter"])),
                                            full_name=f"{last} {rnd.choice(MEN + WOMEN)}", idnp=_idnp(rnd),
                                            birth_date=_years_ago(rnd, today, child_age, child_age + 0.9), dependent=True,
                                            disabled=rnd.random() < 0.03)
        if age > 40 and rnd.random() < 0.15:  # un părinte întreținut (persoană întreținută pentru scutire)
            FamilyMember.objects.create(employee=emp, relation=self.family.get(rnd.choice(["mother", "father"])),
                                        full_name=f"{last} {rnd.choice(MEN + WOMEN)}", idnp=_idnp(rnd),
                                        birth_date=birth - timedelta(days=365 * rnd.randint(22, 30)), dependent=True,
                                        note="Persoană întreținută (nu are venituri proprii)")
        if age > 30 and rnd.random() < 0.45:
            start = date(graduated, rnd.randint(7, 9), 1)
            end = start + timedelta(days=365 * rnd.randint(2, max(2, min(10, age - 26))))
            if end < today - timedelta(days=200):
                PriorExperience.objects.create(employee=emp, organization=rnd.choice(PREVIOUS_EMPLOYERS),
                                               position=occ_name, date_from=start, date_to=end, document="Carnetul de muncă")
        if sex == "M" and age <= 50:  # evidența militară — date păstrate; modulul rămâne oprit (Legea 112/2023)
            MilitaryRecord.objects.create(employee=emp, status="recruit" if age < 27 else "liable", category="2",
                                          group=rnd.choice(self.groups) if self.groups else None,
                                          composition=rnd.choice(["soldiers", "soldiers", "sergeants"]), center=self.center,
                                          book=f"AA {rnd.randint(100000, 999999)}")
        return emp


def _cumul(people, subs, occ, staff, ctx, today):
    """Două cumuluri interne, două cumuluri externe (pe posturile vacante) și un contract de prestări servicii."""
    def first(code, occ_name):
        return next(e for e, j in people if j.subdivision.code == code and j.occupation.name_ro == occ_name)

    since = today.replace(day=1) - timedelta(days=200)
    staff.hire(first("DEP", "Magaziner"), kind="internal", subdivision=subs["ATL1"], occupation=occ["Ambalator manual"],
               rate=Decimal("0.5"), base_salary=Decimal("8000"), date_from=since)
    staff.hire(first("TRN", "Conducător auto"), kind="internal", subdivision=subs["TRN"],
               occupation=occ["Conducător de autocamion"], rate=Decimal("0.5"), base_salary=Decimal("13000"),
               date_from=today.replace(day=1) - timedelta(days=120))
    tab = len(people)
    for i, (code, occ_name, salary, sex, last, first_name) in enumerate((
            ("CONT", "Contabil", 15000, "F", "Vrabie", "Doina"), ("VNZ", "Agent de vânzări", 12000, "M", "Bostan", "Tudor"))):
        tab += 1
        emp = ctx.person(tab, last, first_name, sex, occ_name, min_age=28)
        start = today.replace(month=1, day=10) if i == 0 else today.replace(day=1) - timedelta(days=150)
        staff.hire(emp, kind="external", subdivision=subs[code], occupation=occ[occ_name], rate=Decimal("0.5"),
                   base_salary=Decimal(salary), date_from=start, contract_number=f"{emp.tab_number}/{start.year}-C",
                   contract_date=start)
    emp = ctx.person(tab + 1, "Gheorghiță", "Eugen", "M", "Programator", min_age=30)
    staff.hire(emp, kind="contractor", subdivision=subs["ADM"], occupation=occ["Programator"], rate=Decimal("0.5"),
               base_salary=Decimal("0"), date_from=today.replace(month=1, day=1),
               contract_number=f"PS-1/{today.year}", contract_date=today.replace(month=1, day=1))


def _staff_list_order(sl, users):
    """Statele de personal se aprobă prin ordinul directorului (tipul „Aprobarea / modificarea statelor de personal”)."""
    from apps.org.models import OrderType
    from apps.orders import services as order_services
    from apps.orders.models import OrderItem

    ot = OrderType.objects.filter(code="staff_list").first()
    if ot is None:  # clasificatorul fără tipul de ordin: se aprobă direct
        from apps.org import services as org_services

        sl.approved_by = "Ordinul directorului"
        sl.save(update_fields=["approved_by"])
        org_services.approve(sl, users.get("director"))
        return
    day = sl.date
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    order = order_services.new_order(ot, user=users.get("cadre"), date=day)
    order.basis = sl.basis
    order.save(update_fields=["basis"])
    item = OrderItem.objects.create(order=order, params={"staff_list": sl.pk}, sort=10)
    order_services.refresh_text(item)
    item.save(update_fields=["text"])
    order_services.sign(order, user=users.get("director"))


def _shifts(people, today):
    """Operatorii din sectorul de prelucrare mecanică lucrează pe ture de 12 ore (zi, noapte, două zile libere), decalați
    câte o zi, ca sectorul să meargă non-stop; graficul de ture al lunii trecute e aprobat."""
    from apps.worktime import seed as worktime_seed
    from apps.worktime.models import JobSchedule, WorkSchedule

    worktime_seed.run()
    zn = WorkSchedule.objects.filter(code="ZN", deletion_mark=False).first()
    if zn is None:
        return
    shift_jobs = [j for _e, j in people if j.subdivision.code == SHIFT_SECTOR and j.occupation.name_ro == SHIFT_OCCUPATION]
    for i, job in enumerate(shift_jobs):
        JobSchedule.objects.create(employment=job, schedule=zn, date_from=job.date_from, cycle_offset=i % 4)


def _activity(people, subs, rnd, today, users):
    """Concedii, cereri, foi de boală, examene medicale și instructaje SSM, formarea, un ordin semnat, graficul de ture, pontajul
    și salariul lunii trecute (calculul aprobat, îndreptarea achitată)."""
    from apps.core.models import NumberSeries
    from apps.health.models import MedicalExam, SafetyBriefing
    from apps.leave import balance
    from apps.leave.models import Absence, LeaveRequest
    from apps.org.models import OrderType
    from apps.orders import services as order_services
    from apps.orders.models import OrderItem
    from apps.payroll import engine, payments
    from apps.payroll.models import Payment, Payroll
    from apps.training.models import TrainingRecord
    from apps.worktime import services as worktime
    from apps.worktime.models import Roster, Timesheet

    first_this = today.replace(day=1)
    last_prev = first_this - timedelta(days=1)
    first_prev = last_prev.replace(day=1)
    ssm = next((f"{e.full_name()}, inginer SSM" for e, j in people if j.occupation.name_ro.startswith("Inginer securitate")), "")
    # evidența concediilor pornește de la 1 ianuarie anul trecut (ca la o întreprindere nouă în program)
    balance.save_settings({"start_date": date(today.year - 1, 1, 1).isoformat()})
    for i, (emp, job) in enumerate(people):
        production = is_production(job.subdivision)
        if production and i % 6 != 5:
            done = today - timedelta(days=rnd.randint(30, 380))
            MedicalExam.objects.create(employee=emp, kind="periodic", date=done, next_date=done + timedelta(days=365),
                                       institution=CLINIC, conclusion="fit", document=f"F-{rnd.randint(1000, 9999)}")
        SafetyBriefing.objects.create(employee=emp, kind="periodic", date=today - timedelta(days=rnd.randint(20, 200)),
                                      next_date=today + timedelta(days=rnd.randint(-10, 160)), instructor=ssm,
                                      topic="Instructajul periodic la locul de muncă")
        if i % 3 == 0:
            title, provider, hours = rnd.choice(COURSES["production" if production else "office"])
            start = today - timedelta(days=rnd.randint(20, 900))
            TrainingRecord.objects.create(employee=emp, kind=rnd.choice(["course", "seminar", "internal", "online"]),
                                          title=title, provider=provider, date_from=start,
                                          date_to=start + timedelta(days=max(0, hours // 8 - 1)), hours=Decimal(hours),
                                          certificate_number=f"C-{start.year}-{rnd.randint(100, 999)}", certificate_date=start)
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
        if i in (2, 13, 21, 40):
            start = today + timedelta(days=30 + i)
            LeaveRequest.objects.create(employee=emp, kind="annual", date_from=start, date_to=start + timedelta(days=13), days=14,
                                        reason="Concediu de odihnă anual")
    # ordinul de premiere (colectiv, semnat)
    bonus = OrderType.objects.filter(code="bonus").first()
    if bonus is not None:
        order = order_services.new_order(bonus, user=users.get("cadre"), date=first_prev + timedelta(days=20))
        order.basis = "Demersul șefului atelierului de producție"
        order.save(update_fields=["basis"])
        workers = [(e, j) for e, j in people if j.subdivision.code in ("ATL1", "ATL2")]
        for n, (emp, _job) in enumerate(workers[:6], start=1):
            item = OrderItem.objects.create(order=order, employee=emp, sort=n * 10,
                                            params={"amount": "1500", "note": "pentru îndeplinirea planului de producție"})
            order_services.refresh_text(item)
            item.save(update_fields=["text"])
        order_services.sign(order, user=users.get("director"))
    # graficul de ture al atelierului, pontajul (pe subdiviziunile de sus, cu sectoarele lor) și salariul lunii trecute
    atl = subs["ATL"]
    roster = Roster.objects.create(subdivision=atl, year=first_prev.year, month=first_prev.month, created_by=users.get("sef.productie"))
    worktime.fill_roster(roster)
    roster.status, roster.approved_by, roster.approved_at = "approved", users.get("cadre"), timezone.now()
    roster.save(update_fields=["status", "approved_by", "approved_at"])
    for sub in subs.values():
        if sub.parent_id is None:
            worktime.fill_timesheet(Timesheet.objects.create(subdivision=sub, year=first_prev.year, month=first_prev.month,
                                                             created_by=users.get("cadre")))
    payroll = Payroll.objects.create(year=first_prev.year, month=first_prev.month, date=last_prev, created_by=users.get("contabil"),
                                     number=NumberSeries.next_number("payroll"))
    engine.calculate(payroll)
    payroll.status, payroll.approved_by, payroll.approved_at = "approved", users.get("director"), timezone.now()
    payroll.save(update_fields=["status", "approved_by", "approved_at"])
    day = min(today, last_prev + timedelta(days=7))
    pay = Payment.objects.create(year=first_prev.year, month=first_prev.month, kind="salary", method="all", date=day, payroll=payroll,
                                 created_by=users.get("contabil"), number=NumberSeries.next_number("payroll_payment"))
    if payments.fill(pay):
        pay.status, pay.paid_on = "paid", day
        pay.reference = f"Ordinul de plată nr. {rnd.randint(100, 999)} din {day:%d.%m.%Y}"
        pay.save(update_fields=["status", "paid_on", "reference"])
    else:
        pay.delete()


def _users(people, subs, Role, User) -> dict:
    """Câte un utilizator pentru fiecare rol (aceeași parolă demo); „angajat” e legat de un operator din atelier, șeful de
    subdiviziune e legat de atelierul de producție și de sectoarele lui. Administratorul e cel din asistentul de instalare; fără el
    (crm_demo pe o bază fără asistent) se face și `admin`."""
    out = {}
    rows = list(USERS)
    has_admin = User.objects.filter(is_superuser=True).exists() or User.objects.filter(roles__code="admin").exists()
    if not has_admin:
        rows.insert(0, (ADMIN_USERNAME, "admin", "Administrator", "Demo"))
    for username, role, first, last in rows:
        existing = User.objects.filter(username=username).first()
        if existing is not None:
            out[username] = existing
            continue
        emp = None
        if role == "employee":
            emp = next(e for e, j in people if j.subdivision.code == SHIFT_SECTOR and j.occupation.name_ro == SHIFT_OCCUPATION
                       and e.user_id is None)
            first, last = emp.first_name, emp.last_name
        user = User.objects.create_user(username=username, password=DEMO_PASSWORD, first_name=first, last_name=last,
                                        email=f"{username}@{DEMO_DOMAIN}")
        user.roles.set(Role.objects.filter(code=role))
        if role == "department_head":  # rolul vede „doar ale mele” (fără sub-subdiviziuni): atelierul și sectoarele lui
            for code in ("ATL", "ATL1", "ATL2"):
                subs[code].users.add(user)
        if emp is not None:
            emp.user = user
            emp.save(update_fields=["user"])
        out[username] = user
    return out
