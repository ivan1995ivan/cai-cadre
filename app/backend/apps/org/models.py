"""Instituția: clasificatoarele, subdiviziunile și statele de personal (Etapa 1 din PLAN.md).

Denumirile au trei limbi (RO / RU / EN); dacă lipsește traducerea, se arată româna.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

# Categoriile de personal din statele IMSP (Ordinul MS 100/2008, anexa „efectivul-limită”)
STAFF_CATEGORIES = [
    ("leadership", "Personal de conducere"),
    ("physicians", "Medici (studii superioare)"),
    ("pharmacists", "Farmaciști"),
    ("nurses", "Personal medical cu studii medii"),
    ("junior", "Personal medical inferior"),
    ("admin", "Personal administrativ-gospodăresc"),
    ("other", "Alt personal"),
]


class Named(models.Model):
    code = models.CharField("Cod", max_length=32, blank=True, db_index=True)
    name_ro = models.CharField("Denumire (RO)", max_length=250)
    name_ru = models.CharField("Denumire (RU)", max_length=250, blank=True)
    name_en = models.CharField("Denumire (EN)", max_length=250, blank=True)
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        abstract = True
        ordering = ["sort", "name_ro"]

    def __str__(self):
        return f"{self.code} {self.name_ro}".strip()

    def local_name(self, lang="ro"):
        return {"ru": self.name_ru, "en": self.name_en}.get(lang) or self.name_ro


class Occupation(Named):
    """Funcția (ocupația) după Clasificatorul ocupațiilor din RM (CORM 006-21)."""

    category = models.CharField("Categoria de personal", max_length=12, choices=STAFF_CATEGORIES, default="other")
    isco_code = models.CharField("Cod ISCO-08", max_length=8, blank=True)
    weekly_hours = models.DecimalField("Ore pe săptămână", max_digits=4, decimal_places=1, default=Decimal("40"))
    base_leave_days = models.PositiveSmallIntegerField("Concediu de bază (zile)", default=28)
    extra_leave_days = models.PositiveSmallIntegerField("Concediu suplimentar (zile)", default=0)
    harmful = models.BooleanField("Condiții vătămătoare (HG 1223/2004)", default=False)
    notes = models.CharField("Observații", max_length=300, blank=True)

    class Meta(Named.Meta):
        verbose_name = "Funcție (CORM)"


class Specialty(Named):
    """Specialitatea (medicală, farmaceutică, de nursing sau alta) — pentru studii, atestare și categorii."""

    KINDS = [("medical", "Medicală"), ("pharmacy", "Farmaceutică"), ("nursing", "Nursing / studii medii"),
             ("other", "Alta")]
    kind = models.CharField(max_length=10, choices=KINDS, default="medical")
    isced = models.CharField("Cod ISCED", max_length=8, blank=True)

    class Meta(Named.Meta):
        verbose_name = "Specialitate"


class DictItem(Named):
    """Clasificatoarele mici, după tip: studii, tipuri de acte, rudenia, motivele încetării etc."""

    KINDS = [
        ("education", "Nivelul studiilor"),
        ("education_form", "Forma de învățământ"),
        ("document", "Tipuri de acte (identitate, diplome, certificate)"),
        ("family", "Gradul de rudenie"),
        ("marital", "Starea familială"),
        ("nationality", "Naționalitatea"),
        ("termination", "Motivele încetării CIM"),
        ("sanction", "Sancțiuni disciplinare"),
        ("incentive", "Tipuri de stimulare"),
        ("employment", "Tipul angajării"),
        ("military_group", "Evidența militară: grupa"),
        ("military_rank", "Evidența militară: grade"),
        ("military_center", "Centre militare teritoriale"),
        ("checklist", "Lista de verificare la angajare / eliberare"),
    ]
    kind = models.CharField(max_length=20, choices=KINDS, db_index=True)
    extra = models.JSONField(default=dict, blank=True)  # de ex. {"has_expiry": true} la tipurile de acte

    class Meta(Named.Meta):
        ordering = ["kind", "sort", "name_ro"]
        verbose_name = "Element de clasificator"


class LegalBasis(models.Model):
    """Temeiul legal pus în ordine (articol din Codul muncii, HG, ordin MS)."""

    code = models.CharField("Cod", max_length=32, unique=True)
    act = models.CharField("Actul normativ", max_length=120, default="Codul muncii nr. 154/2003")
    article = models.CharField("Articolul", max_length=20, blank=True)
    paragraph = models.CharField("Alineatul", max_length=10, blank=True)
    letter = models.CharField("Litera", max_length=10, blank=True)
    name_ro = models.CharField("Denumire (RO)", max_length=250)
    name_ru = models.CharField("Denumire (RU)", max_length=250, blank=True)
    name_en = models.CharField("Denumire (EN)", max_length=250, blank=True)
    text_ro = models.TextField("Textul în ordin (RO)", blank=True)
    text_ru = models.TextField("Textul în ordin (RU)", blank=True)
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["sort", "code"]
        verbose_name = "Temei legal"

    def __str__(self):
        return self.reference()

    def reference(self) -> str:
        """„art. 86 alin. (1) lit. c) din Codul muncii nr. 154/2003”."""
        parts = []
        if self.article:
            parts.append(f"art. {self.article}")
        if self.paragraph:
            parts.append(f"alin. ({self.paragraph})")
        if self.letter:
            parts.append(f"lit. {self.letter})")
        ref = " ".join(parts)
        return f"{ref} din {self.act}" if ref else self.act

    def provision(self) -> str:
        """Prevederea fără act: „art. 86 alin. (1) lit. c)” (gol — tot actul)."""
        parts = [f"art. {self.article}" if self.article else "", f"alin. ({self.paragraph})" if self.paragraph else "",
                 f"lit. {self.letter})" if self.letter else ""]
        return " ".join(p for p in parts if p)

    @staticmethod
    def combined(bases) -> str:
        """Temeiurile ordinului într-un singur text, pe acte, în ordinea lor: „art. 55 lit. a) și art. 60 din Codul muncii
        nr. 154/2003, pct. 5 din HG nr. 426/2004”."""
        acts: dict = {}
        for b in bases:
            acts.setdefault(b.act, [])
            if b.provision() and b.provision() not in acts[b.act]:
                acts[b.act].append(b.provision())

        def joined(items):
            return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " și " + items[-1]

        return ", ".join(f"{joined(refs)} din {act}" if refs else act for act, refs in acts.items())

    @classmethod
    def preamble(cls, bases) -> str:
        """Preambulul ordinului: „În temeiul …,” (gol fără temeiuri)."""
        text = cls.combined(bases)
        return f"În temeiul {text}," if text else ""


# Efectul ordinului asupra dosarului angajatului (se aplică la semnare — Etapa 3)
ORDER_EFFECTS = [
    ("none", "Fără efect automat"),
    ("hire", "Angajare"),
    ("change", "Modificarea CIM (funcție, subdiviziune, normă, condiții)"),
    ("salary", "Salariul de funcție / sporuri"),
    ("substitution", "Suplinire / cumul / interimat"),
    ("suspend", "Suspendarea CIM"),
    ("resume", "Reluarea activității"),
    ("terminate", "Încetarea CIM"),
    ("leave", "Concediu"),
    ("leave_recall", "Rechemare / amânare concediu"),
    ("travel", "Delegare"),
    ("worktime", "Timp de muncă (grafic, ore, zi de odihnă)"),
    ("incentive", "Stimulare (premiu, ajutor material)"),
    ("sanction", "Sancțiune disciplinară"),
    ("qualification", "Calificare / atestare / formare"),
    ("staff_list", "Statele de personal"),
    ("cancel", "Anularea unui ordin"),
]

ORDER_GROUPS = [
    ("A", "Raporturi de muncă"),
    ("B", "Concedii"),
    ("C", "Timp de muncă"),
    ("D", "Salarizare și stimulare"),
    ("E", "Disciplină"),
    ("F", "Profesional (formare, atestare)"),
    ("G", "Organizatorice (de bază)"),
]

ORDER_REGISTERS = [
    ("order_personnel", "Ordine privind personalul"),
    ("order_leave", "Ordine privind concediile"),
    ("order_travel", "Ordine privind deplasările"),
    ("order_general", "Ordine de bază (activitate generală)"),
]


class OrderType(Named):
    group = models.CharField("Grupa", max_length=1, choices=ORDER_GROUPS, default="A")
    register = models.CharField("Registrul (numerotarea)", max_length=20, choices=ORDER_REGISTERS, default="order_personnel")
    effect = models.CharField("Efectul la semnare", max_length=16, choices=ORDER_EFFECTS, default="none")
    collective = models.BooleanField("Se poate face pentru mai mulți angajați", default=False)
    needs_employee = models.BooleanField("Are angajat (angajați)", default=True)
    legal_bases = models.ManyToManyField(LegalBasis, blank=True, related_name="order_types",
                                         verbose_name="Temeiurile legale implicite")
    title_ro = models.CharField("Titlul în ordin (RO)", max_length=250, blank=True,
                                help_text="„Cu privire la acordarea concediului de odihnă anual”")
    title_ru = models.CharField("Titlul în ordin (RU)", max_length=250, blank=True)
    report_irm19 = models.BooleanField("Se raportează la CNAS (IRM19)", default=False)
    payroll_effect = models.BooleanField("Are efect asupra salariului", default=False)
    from_1c = models.BooleanField("Exista în 1C (Personal.cf)", default=False)
    # textul punctului „ORDON:” pentru un angajat; gol = textul livrat (apps.orders.texts). Câmpurile: {angajat}, {functia} …
    point_template_ro = models.TextField("Textul punctului (RO)", blank=True)
    point_template_ru = models.TextField("Textul punctului (RU)", blank=True)

    class Meta(Named.Meta):
        ordering = ["group", "sort", "name_ro"]
        verbose_name = "Tip de ordin"


class Subdivision(Named):
    """Subdiviziunea instituției (secție, laborator, serviciu); ierarhică."""

    KINDS = [("clinical", "Clinică (cu paturi)"), ("paraclinical", "Paraclinică / diagnostic"),
             ("ambulatory", "Ambulatorie / consultativă"), ("admin", "Administrativă / gospodărească"),
             ("other", "Alta")]
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children",
                               verbose_name="Subdiviziunea-părinte")
    kind = models.CharField("Tipul", max_length=12, choices=KINDS, default="clinical")
    beds = models.PositiveSmallIntegerField("Paturi", default=0)
    harmful = models.BooleanField("Condiții vătămătoare (HG 1223/2004)", default=False)
    extra_leave_days = models.PositiveSmallIntegerField("Concediu suplimentar pentru condiții (zile)", default=0)
    reduced_hours = models.DecimalField("Ore pe săptămână (zi redusă)", max_digits=4, decimal_places=1, null=True,
                                        blank=True)
    head_name = models.CharField("Șeful subdiviziunii", max_length=150, blank=True)
    # Cine vede angajații, concediile și pontajul subdiviziunii când rolul are „doar ale mele” (șeful de secție)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="subdivisions",
                                   verbose_name="Utilizatorii subdiviziunii (șeful, asistentul superior)")

    class Meta(Named.Meta):
        verbose_name = "Subdiviziune"

    def descendant_ids(self) -> set:
        ids, frontier = {self.pk}, [self.pk]
        while frontier:
            frontier = list(Subdivision.objects.filter(parent_id__in=frontier).exclude(pk__in=ids).values_list("pk", flat=True))
            ids.update(frontier)
        return ids

    def path(self) -> list:
        node, chain = self, []
        while node is not None and len(chain) < 20:
            chain.insert(0, node)
            node = node.parent
        return chain


class StaffList(models.Model):
    """Statele de personal — o versiune (cu numărul și data aprobării de fondator)."""

    STATUSES = [("draft", "Ciornă"), ("approved", "Aprobat"), ("cancelled", "Anulat")]
    number = models.CharField("Numărul", max_length=40, blank=True)
    date = models.DateField("Data documentului", default=timezone.localdate)
    effective_from = models.DateField("În vigoare de la")
    approved_by = models.CharField("Aprobat prin", max_length=300, blank=True,
                                   help_text="De ex. Decizia Consiliului raional nr. 1/1 din 20.01.2026")
    basis = models.TextField("Temeiul (normative, ordine MS)", blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="draft")
    previous = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="next_versions",
                                 verbose_name="Versiunea anterioară")
    notes = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True, blank=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-effective_from", "-id"]
        verbose_name = "State de personal"

    def __str__(self):
        return f"State de personal nr. {self.number or self.pk} din {self.effective_from:%d.%m.%Y}"


class StaffListLine(models.Model):
    staff_list = models.ForeignKey(StaffList, on_delete=models.CASCADE, related_name="lines")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, verbose_name="Subdiviziunea")
    occupation = models.ForeignKey(Occupation, on_delete=models.PROTECT, verbose_name="Funcția")
    category = models.CharField("Categoria de personal", max_length=12, choices=STAFF_CATEGORIES, blank=True)
    units = models.DecimalField("Unități", max_digits=7, decimal_places=2)
    base_salary = models.DecimalField("Salariul de funcție (lei)", max_digits=12, decimal_places=2, default=Decimal("0"))
    allowance_pct = models.DecimalField("Sporuri fixe (%)", max_digits=6, decimal_places=2, default=Decimal("0"))
    effort_note = models.CharField("Mențiune („cu 50% efort medic de familie”)", max_length=200, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "Rând din statele de personal"

    def effective_category(self) -> str:
        return self.category or self.occupation.category

    def monthly_fund(self) -> Decimal:
        """Fondul lunar al rândului: unități × salariu × (1 + sporuri %)."""
        return (self.units * self.base_salary * (1 + self.allowance_pct / 100)).quantize(Decimal("0.01"))


class Holiday(models.Model):
    """Zilele de sărbătoare nelucrătoare (Codul muncii, art. 111) — nu intră în durata concediului de odihnă.

    Sărbătorile fixe și cele de Paște se generează singure pe fiecare an (apps.org.calendar); hramul localității și
    zilele declarate de Guvern se adaugă manual."""

    date = models.DateField("Data", unique=True)
    name = models.CharField("Denumirea", max_length=120)
    auto = models.BooleanField("Generată automat", default=True)

    class Meta:
        ordering = ["date"]
        verbose_name = "Zi de sărbătoare"

    def __str__(self):
        return f"{self.date:%d.%m.%Y} {self.name}"
