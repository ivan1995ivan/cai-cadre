"""Importul dosarelor din Excel (fără bază 1C de preluat): angajații cu raportul de muncă, apoi filele dosarului.

Ordinea recomandată: subdiviziunile și funcțiile (Etapa 1) → angajații → actele, familia, studiile, stagiul.
Angajatul din fișierele secundare se găsește după „Nr. tabel” sau „IDNP”.
"""
from decimal import Decimal

from apps.core.excel_import import Column, RowError, Spec
from apps.org.models import DictItem, Occupation, Specialty, Subdivision

from . import services
from .models import EMPLOYMENT_KINDS, Education, Employee, EmployeeDocument, FamilyMember, PriorExperience

KIND_ALIASES = {
    "de baza": "main", "baza": "main", "main": "main", "основное": "main",
    "de baza (student)": "main_student", "student": "main_student",
    "cumul intern": "internal", "intern": "internal", "internal": "internal", "внутреннее совместительство": "internal",
    "cumul extern": "external", "extern": "external", "external": "external", "внешнее совместительство": "external",
    "contract de prestari servicii": "contractor", "prestari servicii": "contractor", "contract civil": "contractor",
    "contractat": "contractor", "contractor": "contractor", "договор оказания услуг": "contractor", "по договору": "contractor",
    "suplinire": "substitute", "suplinire temporara": "substitute", "substitute": "substitute",
}
KINDS_HINT = "Tipul angajării: " + ", ".join(name for _, name in EMPLOYMENT_KINDS)


def _norm(text) -> str:
    import unicodedata

    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower() if text else ""
    return " ".join(text.split())


def _kind(value) -> str:
    if not value:
        return "main"
    key = _norm(value) or str(value).strip().lower()
    if key in KIND_ALIASES:
        return KIND_ALIASES[key]
    raw = str(value).strip().lower()
    if raw in KIND_ALIASES:
        return KIND_ALIASES[raw]
    raise RowError(f"Tipul angajării „{value}” nu există. {KINDS_HINT}")


def _dict_item(kind, value, label):
    if not value:
        return None
    v = str(value).strip()
    item = (DictItem.objects.filter(kind=kind, code__iexact=v).first() or DictItem.objects.filter(kind=kind, name_ro__iexact=v).first()
            or DictItem.objects.filter(kind=kind, name_ru__iexact=v).first())
    if item is None:
        names = ", ".join(DictItem.objects.filter(kind=kind).values_list("name_ro", flat=True)[:12])
        raise RowError(f"{label} „{value}” nu există în clasificator ({names}).")
    return item


def _sex(value):
    if not value:
        return ""
    v = _norm(value)
    if v in ("m", "masculin", "b", "barbat", "male") or str(value).strip().lower() in ("м", "мужской"):
        return "M"
    if v in ("f", "feminin", "femeie", "female") or str(value).strip().lower() in ("ж", "женский"):
        return "F"
    raise RowError(f"Sexul „{value}”: scrieți M sau F.")


def _subdivision(value):
    obj = Subdivision.objects.filter(code=value).first() or Subdivision.objects.filter(name_ro__iexact=value).first()
    if not obj:
        raise RowError(f"Subdiviziunea „{value}” nu există. Importați întâi subdiviziunile.")
    return obj


def _occupation(code, name, ctx):
    obj = Occupation.objects.filter(code=code).first() if code else None
    obj = obj or (Occupation.objects.filter(name_ro__iexact=name).first() if name else None)
    if not obj and name and ctx.get("create_occupations"):
        obj = Occupation.objects.create(code=code or "", name_ro=name)
    if not obj:
        label = f"{code or ''} {name or ''}".strip()
        raise RowError(f"Funcția „{label}” nu există în clasificator (sau bifați „Creează funcțiile lipsă”).")
    return obj


def find_employee(values) -> Employee:
    tab, idnp = values.get("tab_number"), values.get("employee_idnp")
    emp = None
    if tab:
        emp = Employee.objects.filter(tab_number=tab).first()
    if emp is None and idnp:
        emp = Employee.objects.filter(idnp=idnp).first()
    if emp is None:
        raise RowError(f"Angajatul (nr. tabel „{tab or ''}”, IDNP „{idnp or ''}”) nu există. Importați întâi angajații.")
    return emp


EMP_REF = [
    Column("tab_number", "Nr. tabel", example="101", aliases=("numar tabelar", "nr tabel", "табельный номер")),
    Column("employee_idnp", "IDNP angajat", example="2001000123456", aliases=("idnp angajatului",)),
]


# --- angajații cu raportul de muncă ------------------------------------------------------
def _save_employee(values, ctx):
    idnp, tab = values.get("idnp", ""), values.get("tab_number", "")
    if idnp and len(idnp) != 13:
        raise RowError("IDNP are 13 cifre.")
    emp = Employee.objects.filter(idnp=idnp).first() if idnp else None
    emp = emp or (Employee.objects.filter(tab_number=tab).first() if tab else None)
    if emp is None and not idnp and not tab:
        emp = Employee.objects.filter(last_name__iexact=values["last_name"], first_name__iexact=values["first_name"],
                                      birth_date=values.get("birth_date")).first()
    status = "updated" if emp else "created"
    if emp is None:
        emp = Employee(tab_number=tab or services.next_tab_number())
    elif tab and emp.tab_number != tab:
        if Employee.objects.filter(tab_number=tab).exclude(pk=emp.pk).exists():
            raise RowError(f"Numărul de tabel {tab} este al altui angajat.")
        emp.tab_number = tab
    for f in ("last_name", "first_name"):
        setattr(emp, f, values[f])
    for f in ("patronymic", "idnp", "birth_place", "phone", "email", "address", "cnam_code", "cpas", "iban", "bank_name",
              "clothing_size", "shoe_size"):
        if values.get(f):
            setattr(emp, f, values[f])
    if values.get("height"):
        if not 50 <= values["height"] <= 250:
            raise RowError(f"Înălțimea {values['height']} cm nu pare corectă.")
        emp.height = values["height"]
    if values.get("birth_date"):
        emp.birth_date = values["birth_date"]
    if values.get("sex"):
        emp.sex = _sex(values["sex"])
    if values.get("marital"):
        emp.marital_status = _dict_item("marital", values["marital"], "Starea familială")
    if values.get("nationality"):
        emp.nationality = _dict_item("nationality", values["nationality"], "Naționalitatea")
    emp.save()

    if values.get("subdivision"):
        sub = _subdivision(values["subdivision"])
        occ = _occupation(values.get("occupation_code"), values.get("occupation"), ctx)
        kind = _kind(values.get("kind"))
        if not values.get("date_from"):
            raise RowError("Data angajării este obligatorie când se dă subdiviziunea.")
        rate = values.get("rate") or Decimal("1")
        if rate > Decimal("1.5"):  # norma scrisă în procente (50 → 0,5)
            rate = rate / 100
        job = emp.employments.filter(subdivision=sub, occupation=occ, kind=kind).exclude(status="ended").first()
        fields = {"rate": rate, "base_salary": values.get("base_salary") or Decimal("0"),
                  "allowance_pct": values.get("allowance_pct") or Decimal("0"), "date_from": values["date_from"]}
        extra = {k: values[k] for k in ("date_to", "probation_until", "contract_number", "contract_date") if values.get(k)}
        if job is None:
            job = services.hire(emp, kind=kind, subdivision=sub, occupation=occ, user=ctx.get("user"), event="import",
                                order=values.get("hire_order", ""), **fields, **extra)
        else:  # rândul repetat: se corectează datele raportului existent (fără istoric nou)
            for k, v in {**fields, **extra}.items():
                setattr(job, k, v)
            job.save()
            first = job.history.order_by("date", "id").first()
            if first:
                for f in services.SNAPSHOT_FIELDS:
                    setattr(first, f, getattr(job, f))
                first.date = job.date_from
                first.save()
        _import_combination(job, values.get("combination_pct"))
    return emp, status


IMPORT_NOTE = "Din importul Excel („Cumularea funcțiilor, %”)"


def _import_combination(job, pct):
    """Coloana „Cumularea funcțiilor (% din salariul propriu)”: înregistrarea de cumulare a raportului (CM art. 156) din data
    angajării; rândul repetat o corectează, 0 / gol o scoate pe cea din import."""
    from .models import FunctionCombination

    rec = job.combinations.filter(note=IMPORT_NOTE).first()
    if not pct:
        if rec is not None and pct is not None:
            rec.delete()
        return
    if pct < 0 or pct > 200:
        raise RowError("Cumularea funcțiilor: procentul este între 0 și 200.")
    if rec is None:
        FunctionCombination.objects.create(employment=job, kind="combination", occupation=job.occupation, pay_mode="pct_own",
                                           value=pct, date_from=job.date_from, date_to=job.end_date or job.date_to,
                                           order=job.hire_order, note=IMPORT_NOTE)
    else:
        rec.value, rec.date_from = pct, job.date_from
        rec.save(update_fields=["value", "date_from"])


EMPLOYEES = Spec(
    code="employees", title="Angajații (cu raportul de muncă)", sheet_title="Angajati",
    columns=[
        Column("tab_number", "Nr. tabel", example="101", aliases=("numar tabelar", "nr tabel", "табельный номер")),
        Column("last_name", "Numele", required=True, example="Popescu", aliases=("nume", "фамилия")),
        Column("first_name", "Prenumele", required=True, example="Ion", aliases=("prenume", "имя")),
        Column("patronymic", "Patronimicul", example="Vasile", aliases=("отчество",)),
        Column("idnp", "IDNP", example="2001000123456"),
        Column("birth_date", "Data nașterii", kind="date", example="15.03.1980", aliases=("data nasterii", "дата рождения")),
        Column("birth_place", "Locul nașterii"),
        Column("sex", "Sexul (M/F)", example="M", aliases=("sexul", "sex", "пол")),
        Column("marital", "Starea familială"),
        Column("nationality", "Naționalitatea"),
        Column("phone", "Telefon", example="069123456"),
        Column("email", "E-mail"),
        Column("address", "Adresa de domiciliu"),
        Column("cnam_code", "Cod asigurare medicală (CNAM)"),
        Column("cpas", "CPAS"),
        Column("iban", "IBAN"),
        Column("bank_name", "Banca"),
        Column("clothing_size", "Mărimea îmbrăcămintei", example="48", aliases=("marimea hainelor", "размер одежды")),
        Column("shoe_size", "Mărimea încălțămintei", example="39", aliases=("marimea incaltamintei", "размер обуви")),
        Column("height", "Înălțimea (cm)", kind="int", example=170, aliases=("inaltimea", "рост")),
        Column("subdivision", "Subdiviziunea (cod sau denumire)", example="CONT", aliases=("subdiviziunea", "sectia", "secția")),
        Column("occupation_code", "Cod CORM", example=""),
        Column("occupation", "Funcția", example="Contabil", aliases=("functia", "должность")),
        Column("kind", "Tipul angajării", example="de bază", aliases=("tip angajare",)),
        Column("rate", "Norma (1 / 0,5 sau 100% / 50%)", kind="decimal", example=1, aliases=("norma", "unitati", "ставка")),
        Column("date_from", "Data angajării", kind="date", example="01.09.2015", aliases=("data angajarii", "дата приёма")),
        Column("base_salary", "Salariul de funcție", kind="decimal", example=14660),
        Column("allowance_pct", "Sporuri fixe (%)", kind="decimal", example=10),
        Column("combination_pct", "Cumularea funcțiilor (% din salariul propriu)", kind="decimal", example=0,
               aliases=("plata pentru cumul (%)", "cumul %", "совмещение %")),
        Column("contract_number", "Nr. CIM"),
        Column("contract_date", "Data CIM", kind="date"),
        Column("date_to", "CIM pe durată determinată până la", kind="date"),
        Column("probation_until", "Perioada de probă până la", kind="date"),
        Column("hire_order", "Ordinul de angajare (nr., data)", example="45-p din 01.09.2015"),
    ],
    save_row=_save_employee,
    notes=["Un rând = un angajat și un raport de muncă. Pentru cumul intern / extern repetați persoana pe alt rând.",
           "Angajatul existent se recunoaște după IDNP, apoi după nr. de tabel; datele lui se actualizează.",
           "Fără nr. de tabel sistemul dă următorul număr liber.", KINDS_HINT,
           "Subdiviziunile (Întreprinderea și subdiviziunile) și funcțiile (Administrare → Setări → Funcții CORM) trebuie să existe sau bifați „Creează funcțiile lipsă”."],
)


# --- filele dosarului ---------------------------------------------------------------------
def _save_document(values, ctx):
    emp = find_employee(values)
    doc_type = _dict_item("document", values.get("doc_type"), "Tipul actului") if values.get("doc_type") else None
    if doc_type is None and not values.get("title"):
        raise RowError("Scrieți tipul actului (din clasificator) sau denumirea lui.")
    obj = EmployeeDocument.objects.filter(employee=emp, doc_type=doc_type, number=values.get("number", "")).first()
    status = "updated" if obj else "created"
    obj = obj or EmployeeDocument(employee=emp, doc_type=doc_type)
    for f in ("title", "series", "number", "issued_by", "note"):
        if values.get(f):
            setattr(obj, f, values[f])
    for f in ("issue_date", "expiry_date"):
        if values.get(f):
            setattr(obj, f, values[f])
    obj.is_identity = bool(doc_type and doc_type.code in ("id_card", "passport", "residence"))
    obj.save()
    return f"{emp.short_name()}: {obj}", status


DOCUMENTS = Spec(
    code="documents", title="Actele angajaților (identitate, diplome, certificate)", sheet_title="Acte",
    columns=[*EMP_REF,
             Column("doc_type", "Tipul actului", example="Buletin de identitate"),
             Column("title", "Denumirea (dacă nu e în clasificator)"),
             Column("series", "Seria", example="B"), Column("number", "Numărul", example="12345678"),
             Column("issued_by", "Eliberat de", example="ASP"), Column("issue_date", "Data eliberării", kind="date"),
             Column("expiry_date", "Valabil până la", kind="date"), Column("note", "Observații")],
    save_row=_save_document,
)


def _save_family(values, ctx):
    emp = find_employee(values)
    obj = FamilyMember.objects.filter(employee=emp, full_name__iexact=values["full_name"]).first()
    status = "updated" if obj else "created"
    obj = obj or FamilyMember(employee=emp, full_name=values["full_name"])
    if values.get("relation"):
        obj.relation = _dict_item("family", values["relation"], "Rudenia")
    for f in ("idnp", "note"):
        if values.get(f):
            setattr(obj, f, values[f])
    if values.get("birth_date"):
        obj.birth_date = values["birth_date"]
    for f in ("dependent", "disabled"):
        if values.get(f) is not None:
            setattr(obj, f, bool(values[f]))
    obj.save()
    return f"{emp.short_name()}: {obj.full_name}", status


FAMILY = Spec(
    code="family", title="Familia angajaților (soț / soție, copii)", sheet_title="Familia",
    columns=[*EMP_REF, Column("relation", "Rudenia", example="Fiică"),
             Column("full_name", "Numele, prenumele", required=True, example="Popescu Ana"),
             Column("idnp", "IDNP"), Column("birth_date", "Data nașterii", kind="date", example="10.05.2015"),
             Column("dependent", "Întreținut (da/nu)", kind="bool", example="da"),
             Column("disabled", "Cu dizabilitate (da/nu)", kind="bool", example="nu"), Column("note", "Observații")],
    save_row=_save_family,
)


def _specialty(value):
    if not value:
        return None
    return Specialty.objects.filter(name_ro__iexact=value).first() or Specialty.objects.filter(code=value).first()


def _save_education(values, ctx):
    emp = find_employee(values)
    obj = Education.objects.filter(employee=emp, institution__iexact=values["institution"], year_to=values.get("year_to")).first()
    status = "updated" if obj else "created"
    obj = obj or Education(employee=emp, institution=values["institution"])
    if values.get("level"):
        obj.level = _dict_item("education", values["level"], "Nivelul studiilor")
    if values.get("form"):
        obj.form = _dict_item("education_form", values["form"], "Forma de învățământ")
    spec = _specialty(values.get("specialty"))
    obj.specialty = spec or obj.specialty
    if values.get("specialty") and not spec:
        obj.specialty_text = values["specialty"]
    for f in ("qualification", "diploma_series", "diploma_number"):
        if values.get(f):
            setattr(obj, f, values[f])
    for f in ("year_from", "year_to", "diploma_date"):
        if values.get(f):
            setattr(obj, f, values[f])
    obj.save()
    return f"{emp.short_name()}: {obj}", status


EDUCATION = Spec(
    code="education", title="Studiile angajaților", sheet_title="Studii",
    columns=[*EMP_REF, Column("level", "Nivelul studiilor", example="Superioare"),
             Column("institution", "Instituția de învățământ", required=True, example="Universitatea Tehnică a Moldovei"),
             Column("specialty", "Specialitatea", example="Contabilitate"), Column("qualification", "Calificarea"),
             Column("form", "Forma de învățământ", example="La zi"),
             Column("year_from", "Anul admiterii", kind="int"), Column("year_to", "Anul absolvirii", kind="int", example=2004),
             Column("diploma_series", "Diploma: seria"), Column("diploma_number", "Diploma: numărul"),
             Column("diploma_date", "Diploma: data", kind="date")],
    save_row=_save_education,
)


def _save_experience(values, ctx):
    emp = find_employee(values)
    if values["date_to"] < values["date_from"]:
        raise RowError("Data de sfârșit este înaintea celei de început.")
    obj = PriorExperience.objects.filter(employee=emp, organization__iexact=values["organization"],
                                         date_from=values["date_from"]).first()
    status = "updated" if obj else "created"
    obj = obj or PriorExperience(employee=emp, organization=values["organization"], date_from=values["date_from"],
                                 date_to=values["date_to"])
    obj.date_to = values["date_to"]
    for f in ("position", "document"):
        if values.get(f):
            setattr(obj, f, values[f])
    if values.get("in_specialty") is not None:
        obj.in_specialty = bool(values["in_specialty"])
    obj.save()
    return f"{emp.short_name()}: {obj.organization}", status


EXPERIENCE = Spec(
    code="experience", title="Stagiul de muncă anterior", sheet_title="Stagiu",
    columns=[*EMP_REF, Column("organization", "Unitatea", required=True, example="„Exemplu” SRL"),
             Column("position", "Funcția", example="Contabil"),
             Column("date_from", "De la", required=True, kind="date", example="01.09.2004"),
             Column("date_to", "Până la", required=True, kind="date", example="31.08.2015"),
             Column("in_specialty", "În specialitate (da/nu)", kind="bool", example="da"),
             Column("document", "Documentul (carnet, certificat)")],
    save_row=_save_experience,
    notes=["Perioadele suprapuse se numără o singură dată la calculul vechimii."],
)

SPECS = {s.code: s for s in (EMPLOYEES, DOCUMENTS, FAMILY, EDUCATION, EXPERIENCE)}
