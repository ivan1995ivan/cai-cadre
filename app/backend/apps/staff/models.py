"""Dosarul angajatului (fișa personală MR-2 electronică) — Etapa 2 din PLAN.md.

Persoana (`Employee`) are mai multe raporturi de muncă (`Employment`): de bază, cumul intern / extern, rezident,
suplinire. Fiecare raport are istoricul lui (`EmploymentHistory`): funcția, subdiviziunea, norma și salariul „din data”.
Ordinele (Etapa 3) vor scrie în istoric prin `services`; până atunci istoricul se completează la angajare și la import.
"""
import re
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.org.models import DictItem, Occupation, Specialty, Subdivision


def validate_idnp(value: str):
    if value and not re.fullmatch(r"\d{13}", value):
        raise ValidationError("IDNP are 13 cifre.")


def _upload_to(instance, filename):
    return f"staff/{instance.employee_id or 'new'}/{timezone.now():%Y%m%d%H%M%S}-{filename}"


def _dict(kind, **extra):
    return {"to": DictItem, "on_delete": models.PROTECT, "null": True, "blank": True, "related_name": "+",
            "limit_choices_to": {"kind": kind}, **extra}


class Employee(models.Model):
    SEXES = [("M", "Masculin"), ("F", "Feminin")]
    STATUSES = [("active", "Activ"), ("suspended", "Contract suspendat"), ("dismissed", "Eliberat"), ("candidate", "Candidat")]

    tab_number = models.CharField("Numărul de tabel", max_length=20, unique=True)
    last_name = models.CharField("Numele", max_length=80)
    first_name = models.CharField("Prenumele", max_length=80)
    patronymic = models.CharField("Patronimicul", max_length=80, blank=True)
    previous_names = models.CharField("Numele anterior", max_length=160, blank=True)
    idnp = models.CharField("IDNP", max_length=13, blank=True, db_index=True, validators=[validate_idnp])
    birth_date = models.DateField("Data nașterii", null=True, blank=True)
    birth_place = models.CharField("Locul nașterii", max_length=200, blank=True)
    sex = models.CharField("Sexul", max_length=1, choices=SEXES, blank=True)
    citizenship = models.CharField("Cetățenia", max_length=80, blank=True, default="Republica Moldova")
    nationality = models.ForeignKey(**_dict("nationality"), verbose_name="Naționalitatea")
    marital_status = models.ForeignKey(**_dict("marital"), verbose_name="Starea familială")
    photo = models.FileField("Fotografia", upload_to="staff/photos/", blank=True)
    phone = models.CharField("Telefon", max_length=64, blank=True)
    phone2 = models.CharField("Telefon suplimentar", max_length=64, blank=True)
    email = models.EmailField("E-mail", blank=True)
    address = models.CharField("Adresa de domiciliu (viză)", max_length=300, blank=True)
    address_actual = models.CharField("Adresa de reședință", max_length=300, blank=True)
    cnam_code = models.CharField("Cod asigurare medicală (CNAM)", max_length=32, blank=True)
    cpas = models.CharField("Cod personal de asigurări sociale (CPAS)", max_length=32, blank=True)
    iban = models.CharField("IBAN (card salarial)", max_length=34, blank=True)
    bank_name = models.CharField("Banca", max_length=120, blank=True)
    emergency_contact = models.CharField("Persoană de contact în caz de urgență", max_length=200, blank=True)
    disability = models.CharField("Grad de dizabilitate", max_length=60, blank=True)
    # echipamentul de lucru (halate, costume, încălțăminte): pentru comanda echipamentului pe secții
    clothing_size = models.CharField("Mărimea îmbrăcămintei", max_length=20, blank=True)
    shoe_size = models.CharField("Mărimea încălțămintei", max_length=10, blank=True)
    height = models.PositiveSmallIntegerField("Înălțimea (cm)", null=True, blank=True)
    status = models.CharField("Starea", max_length=10, choices=STATUSES, default="active", db_index=True)
    is_archived = models.BooleanField("Dosar arhivat", default=False)
    checklist = models.JSONField("Lista de verificare (angajare / eliberare)", default=dict, blank=True)
    notes = models.TextField("Observații", blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="employee", verbose_name="Contul în sistem (cabinetul personal)")
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["last_name", "first_name", "patronymic"]
        verbose_name = "Angajat"

    def __str__(self):
        return self.full_name()

    def full_name(self) -> str:
        return " ".join(x for x in (self.last_name, self.first_name, self.patronymic) if x)

    def short_name(self) -> str:
        initials = "".join(f"{x[0]}." for x in (self.first_name, self.patronymic) if x)
        return f"{self.last_name} {initials}".strip()

    def main_employment(self):
        active = [e for e in self.employments.all() if e.status != "ended"]
        pool = active or list(self.employments.all())
        main = [e for e in pool if e.kind in ("main", "main_student", "resident")]
        return (main or pool or [None])[0]


class EmployeeDocument(models.Model):
    """Actele angajatului: identitate, diplome, certificate (cu termen), livret militar, scanări."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.ForeignKey(**_dict("document"), verbose_name="Tipul actului")
    title = models.CharField("Denumirea (dacă nu e în clasificator)", max_length=200, blank=True)
    series = models.CharField("Seria", max_length=20, blank=True)
    number = models.CharField("Numărul", max_length=40, blank=True)
    issued_by = models.CharField("Eliberat de", max_length=200, blank=True)
    issue_date = models.DateField("Data eliberării", null=True, blank=True)
    expiry_date = models.DateField("Valabil până la", null=True, blank=True)
    file = models.FileField("Fișierul (scanare)", upload_to=_upload_to, blank=True)
    is_identity = models.BooleanField("Act de identitate", default=False)
    note = models.CharField("Observații", max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-is_identity", "doc_type__sort", "-issue_date", "id"]

    def __str__(self):
        name = self.doc_type.name_ro if self.doc_type_id else self.title
        return f"{name} {self.series} {self.number}".strip()


class FamilyMember(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="family")
    relation = models.ForeignKey(**_dict("family"), verbose_name="Gradul de rudenie")
    full_name = models.CharField("Numele, prenumele", max_length=160)
    idnp = models.CharField("IDNP", max_length=13, blank=True, validators=[validate_idnp])
    birth_date = models.DateField("Data nașterii", null=True, blank=True)
    dependent = models.BooleanField("Persoană întreținută (scutire)", default=False)
    disabled = models.BooleanField("Cu dizabilitate", default=False)
    note = models.CharField("Observații", max_length=200, blank=True)

    class Meta:
        ordering = ["birth_date", "id"]

    def __str__(self):
        return self.full_name


class Education(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="education")
    level = models.ForeignKey(**_dict("education"), verbose_name="Nivelul studiilor")
    institution = models.CharField("Instituția de învățământ", max_length=250)
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Specialitatea")
    specialty_text = models.CharField("Specialitatea (text)", max_length=200, blank=True)
    qualification = models.CharField("Calificarea obținută", max_length=200, blank=True)
    form = models.ForeignKey(**_dict("education_form"), verbose_name="Forma de învățământ")
    year_from = models.PositiveSmallIntegerField("Anul admiterii", null=True, blank=True)
    year_to = models.PositiveSmallIntegerField("Anul absolvirii", null=True, blank=True)
    diploma_series = models.CharField("Diploma: seria", max_length=20, blank=True)
    diploma_number = models.CharField("Diploma: numărul", max_length=40, blank=True)
    diploma_date = models.DateField("Diploma: data", null=True, blank=True)

    class Meta:
        ordering = ["year_to", "id"]

    def __str__(self):
        return f"{self.institution} ({self.year_to or ''})"


class Qualification(models.Model):
    """Categoria de calificare pe specialitate (Ordinul MS 386/2018): se conferă / confirmă la atestare."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="qualifications")
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Specialitatea")
    category = models.ForeignKey(**_dict("qualification"), verbose_name="Categoria")
    certificate_number = models.CharField("Nr. certificatului / ordinului", max_length=60, blank=True)
    awarded_on = models.DateField("Conferită la", null=True, blank=True)
    valid_until = models.DateField("Valabilă până la", null=True, blank=True)
    degree = models.ForeignKey(**_dict("degree"), verbose_name="Gradul științific")
    title = models.ForeignKey(**_dict("title"), verbose_name="Titlul științifico-didactic")
    note = models.CharField("Observații", max_length=200, blank=True)

    class Meta:
        ordering = ["-awarded_on", "id"]


class PriorExperience(models.Model):
    """Stagiul de muncă anterior (din carnetul de muncă până în 2019, din certificate după)."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="experience")
    organization = models.CharField("Unitatea", max_length=250)
    position = models.CharField("Funcția", max_length=200, blank=True)
    date_from = models.DateField("De la")
    date_to = models.DateField("Până la")
    in_specialty = models.BooleanField("În specialitate (medicală)", default=True)
    in_healthcare = models.BooleanField("În sistemul sănătății", default=True)
    document = models.CharField("Documentul (carnet, certificat)", max_length=200, blank=True)

    class Meta:
        ordering = ["date_from", "id"]

    def clean(self):
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValidationError({"date_to": "Data de sfârșit este înaintea celei de început."})


class MilitaryRecord(models.Model):
    """Evidența militară (HG 631/2003) — câmpurile din configurația 1C „Cadre”."""

    CATEGORIES = [("1", "Categoria 1"), ("2", "Categoria 2")]
    COMPOSITIONS = [("command", "De comandă"), ("sergeants", "Sergenți"), ("soldiers", "Soldați"), ("medical", "Medicină")]
    STATUSES = [("liable", "Supus evidenței"), ("not_liable", "Nesupus evidenței"), ("recruit", "Recrut")]

    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="military")
    status = models.CharField("Este la evidență", max_length=12, choices=STATUSES, default="liable")
    category = models.CharField("Categoria evidenței", max_length=1, choices=CATEGORIES, blank=True)
    group = models.ForeignKey(**_dict("military_group"), verbose_name="Grupa evidenței")
    composition = models.CharField("Componența", max_length=12, choices=COMPOSITIONS, blank=True)
    rank = models.ForeignKey(**_dict("military_rank"), verbose_name="Gradul militar")
    specialty_code = models.CharField("Specialitatea militară (cod)", max_length=40, blank=True)
    center = models.ForeignKey(**_dict("military_center"), verbose_name="Centrul militar")
    fit = models.BooleanField("Apt pentru serviciul militar", default=True)
    special_record = models.BooleanField("Evidență specială (rezervat după instituție)", default=False)
    book = models.CharField("Livret militar / certificat de recrutare (seria, nr.)", max_length=60, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)


EMPLOYMENT_KINDS = [
    ("main", "De bază"),
    ("main_student", "De bază (student)"),
    ("internal", "Cumul intern"),
    ("external", "Cumul extern"),
    ("resident", "Rezident"),
    ("substitute", "Suplinire temporară"),
    ("contractor", "Contract de prestări servicii"),
]
# care raporturi ocupă postul din statele de personal (suplinirea ocupă postul celui absent, nu unul nou;
# contractul de prestări servicii e civil — nu ocupă post, nu dă concediu și nu intră în vechimea în muncă)
OCCUPYING_KINDS = {"main", "main_student", "internal", "external", "resident"}
CIVIL_KINDS = {"contractor"}


class Employment(models.Model):
    """Raportul de muncă (contractul individual de muncă) cu valorile curente; istoricul — în EmploymentHistory."""

    STATUSES = [("active", "Activ"), ("suspended", "Suspendat"), ("ended", "Încetat")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employments")
    kind = models.CharField("Tipul", max_length=14, choices=EMPLOYMENT_KINDS, default="main")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, verbose_name="Subdiviziunea")
    occupation = models.ForeignKey(Occupation, on_delete=models.PROTECT, verbose_name="Funcția")
    rate = models.DecimalField("Norma (unități)", max_digits=4, decimal_places=2, default=Decimal("1"))
    base_salary = models.DecimalField("Salariul de funcție", max_digits=12, decimal_places=2, default=Decimal("0"))
    allowance_pct = models.DecimalField("Sporuri fixe (%)", max_digits=6, decimal_places=2, default=Decimal("0"))
    combination_pct = models.DecimalField("Plata pentru cumul (% din salariul funcției)", max_digits=6, decimal_places=2,
                                          default=Decimal("0"))
    date_from = models.DateField("Data angajării")
    date_to = models.DateField("Pe durată determinată până la", null=True, blank=True)
    probation_until = models.DateField("Perioada de probă până la", null=True, blank=True)
    contract_number = models.CharField("Nr. CIM", max_length=40, blank=True)
    contract_date = models.DateField("Data CIM", null=True, blank=True)
    substitutes = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="substituted_by",
                                    verbose_name="Suplinește raportul")
    status = models.CharField("Starea", max_length=10, choices=STATUSES, default="active", db_index=True)
    suspended_from = models.DateField("Suspendat de la", null=True, blank=True)
    suspension_reason = models.CharField("Motivul suspendării", max_length=200, blank=True)
    end_date = models.DateField("Data încetării", null=True, blank=True)
    termination_reason = models.ForeignKey(**_dict("termination"), verbose_name="Motivul încetării")
    hire_order = models.CharField("Ordinul de angajare (nr., data)", max_length=80, blank=True)
    end_order = models.CharField("Ordinul de încetare (nr., data)", max_length=80, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)

    class Meta:
        ordering = ["date_from", "id"]
        verbose_name = "Raport de muncă"

    def __str__(self):
        return f"{self.employee} — {self.occupation.name_ro} ({self.get_kind_display()}, {self.rate})"

    def is_active_on(self, day) -> bool:
        return self.date_from <= day and (self.end_date is None or self.end_date >= day)


class EmploymentHistory(models.Model):
    """O înregistrare în istoria raportului: ce s-a schimbat din data respectivă și prin ce act."""

    EVENTS = [("hire", "Angajare"), ("change", "Modificare"), ("salary", "Salariu / sporuri"), ("suspend", "Suspendare"),
              ("resume", "Reluare"), ("end", "Încetare"), ("import", "Import inițial")]
    employment = models.ForeignKey(Employment, on_delete=models.CASCADE, related_name="history")
    event = models.CharField(max_length=10, choices=EVENTS)
    date = models.DateField("Din data")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, related_name="+")
    occupation = models.ForeignKey(Occupation, on_delete=models.PROTECT, related_name="+")
    rate = models.DecimalField(max_digits=4, decimal_places=2)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowance_pct = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    combination_pct = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    order = models.CharField("Actul (ordinul)", max_length=80, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["date", "id"]


class AccessLog(models.Model):
    """Cine a deschis, tipărit sau exportat dosarul (Legea 133/2011 privind protecția datelor cu caracter personal)."""

    ACTIONS = [("view", "Vizualizare"), ("print", "Tipar"), ("export", "Export")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="access_log")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    action = models.CharField(max_length=8, choices=ACTIONS, default="view")
    detail = models.CharField(max_length=120, blank=True)
    at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-at"]
