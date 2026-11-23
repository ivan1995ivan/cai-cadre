"""Salarizarea (Etapa 4b, partea 1): constantele cu istoric, tipurile de calcul flexibile, cererea de scutire,
reținerile / sporurile personale și calculul lunar al salariului (angajat × raport de muncă × tip de calcul).

Totul se calculează pe **raportul de muncă** (de bază, cumul, suplinire, contract de prestări servicii — fiecare cu
norma și salariul lui); scutirea de impozit se acordă o singură dată pe persoană, pe tot venitul de la acest angajator — la
locul de muncă de bază sau la cel prin cumul, după cererea angajatului (HG 697/2014, Regulamentul, pct. 9).
"""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.org.models import Subdivision
from apps.staff.models import Employee, Employment

ZERO = Decimal("0")


class PayConstant(models.Model):
    """O constantă a salariului (impozit, scutiri, contribuții...) cu valoarea „în vigoare din data”."""

    code = models.CharField("Codul", max_length=40, db_index=True)
    name = models.CharField("Denumirea", max_length=200)
    value = models.DecimalField("Valoarea", max_digits=14, decimal_places=4)
    date_from = models.DateField("În vigoare din")
    source = models.CharField("Temeiul (actul normativ)", max_length=200, blank=True)
    unit = models.CharField("Unitatea (%, lei, zile, luni)", max_length=10, blank=True)

    class Meta:
        ordering = ["code", "-date_from"]
        verbose_name = "Constanta salariului"
        constraints = [models.UniqueConstraint(fields=["code", "date_from"], name="uniq_pay_constant")]

    def __str__(self):
        return f"{self.name} = {self.value} din {self.date_from:%d.%m.%Y}"


class PayType(models.Model):
    """Tipul de calcul (acumulare, reținere sau contribuția angajatorului) cu formula și regulile fiscale."""

    CATEGORIES = [("accrual", "Acumulare"), ("deduction", "Reținere"), ("employer", "Contribuția angajatorului")]
    FORMULAS = [
        ("auto", "Se calculează singur (din pontaj, concedii, foi de boală, ordine)"),
        ("fixed", "Sumă fixă (din rândul angajatului)"),
        ("pct_salary", "% din salariul de funcție"),
        ("pct_base", "% din baza de calcul (tipurile alese)"),
        ("hourly", "Tarif orar × ore lucrate"),
        ("scale", "% după treapta de vechime totală în muncă"),
        ("expr", "Formulă"),
    ]
    APPLIES = [("row", "Doar angajații care au rândul (fila „Salariu”, ordinul, documentul)"),
               ("all", "Toți angajații (tip general, de ex. un spor din pontaj)")]
    # formulele care se pot calcula și fără rândul angajatului (procentul / baza / formula sunt ale tipului)
    GENERAL_FORMULAS = ("expr", "scale", "pct_salary", "pct_base")
    # cheia motorului de calcul pentru formula „auto” (apps.payroll.engine)
    AUTO = [
        ("salary", "Salariul de funcție (pro-rata la orele lucrate)"), ("allowance", "Sporurile fixe din raportul de muncă (%)"),
        ("combination", "Plata pentru cumularea funcțiilor / suplinire (CM art. 156, din raportul de muncă)"),
        ("hour_types", "Ore pe tipuri: ore plătite × tariful (cu orele garantate)"),
        ("piece", "Salarizarea în acord: lucrările din rapoartele de producție aprobate"),
        ("piece_prog", "Acord progresiv: sporul pentru producția peste normă (treptele tipului)"),
        ("night", "Munca de noapte (+ % la tariful orar)"),
        ("holiday", "Munca în zile de sărbătoare (+ % la tariful orar)"), ("overtime", "Ore suplimentare (+ % la tariful orar)"),
        ("leave", "Indemnizația de concediu de odihnă (media × zile)"), ("leave_comp", "Compensarea concediului nefolosit"),
        ("sick", "Incapacitate temporară: zilele plătite de angajator"),
        ("sick_accident", "Accident de muncă / boală profesională: zilele plătite de angajator"),
        ("min_wage", "Completare până la salariul minim"), ("bonus", "Premii din ordine"),
        ("aid", "Ajutor material din ordine"), ("advance", "Avansul plătit (se ia din plăți, pe fluturaș)"),
        ("income_tax", "Impozitul pe venit (se reține la plată)"), ("cnam", "Prima de asigurare medicală (se reține la plată)"),
        ("cas", "Contribuția de asigurări sociale (angajator)"),
        ("cas_min", "CAS pe diferența până la baza minimă (salariul minim)"), ("none", "—"),
    ]
    code = models.CharField("Codul", max_length=24, unique=True)
    name_ro = models.CharField("Denumire (RO)", max_length=200)
    name_ru = models.CharField("Denumire (RU)", max_length=200, blank=True)
    name_en = models.CharField("Denumire (EN)", max_length=200, blank=True)
    category = models.CharField("Categoria", max_length=10, choices=CATEGORIES, default="accrual")
    formula = models.CharField("Formula", max_length=12, choices=FORMULAS, default="fixed")
    auto = models.CharField("Calculul automat", max_length=16, choices=AUTO, default="none")
    percent = models.DecimalField("Procentul (la formulele cu %)", max_digits=7, decimal_places=3, default=ZERO)
    expression = models.TextField("Formula (expresia)", blank=True,
                                  help_text="De ex. TarifOrar * OreNoapte * C.night_pct / 100 (apps.payroll.formula)")
    applies_to = models.CharField("Se calculează pentru", max_length=4, choices=APPLIES, default="row")
    base_codes = models.JSONField("Baza de calcul (codurile tipurilor)", default=list, blank=True)
    scale = models.JSONField("Treptele [{de la: %}] — anii de vechime; la acordul progresiv — % îndeplinire a normei",
                             default=list, blank=True)
    taxable = models.BooleanField("Se impozitează cu impozitul pe venit", default=True)
    cas = models.BooleanField("Intră în baza CAS", default=True)
    cnam = models.BooleanField("Intră în baza CNAM", default=True)
    exempt_month = models.DecimalField("Plafon neimpozabil pe lună (lei)", max_digits=12, decimal_places=2, default=ZERO)
    exempt_year = models.DecimalField("Plafon neimpozabil pe an (lei)", max_digits=12, decimal_places=2, default=ZERO)
    exempt_avg_pct = models.DecimalField("Plafon neimpozabil: % din salariul mediu pe economie", max_digits=6, decimal_places=2,
                                         default=ZERO)
    in_average = models.BooleanField("Intră în salariul mediu (concedii, boală)", default=True)
    ipc_code = models.CharField("Codul sursei de venit (IPC21 / IALS21)", max_length=10, blank=True, default="SAL")
    account = models.CharField("Contul contabil", max_length=20, blank=True)
    on_payslip = models.BooleanField("Pe fișa de calcul", default=True)
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField("Livrat cu sistemul", default=False)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["category", "sort", "code"]
        verbose_name = "Tip de calcul"

    def __str__(self):
        return f"{self.code} {self.name_ro}"


class EmployeePayItem(models.Model):
    """Acumulările și reținerile planificate ale angajatului (sindicat, pensie alimentară, împrumut, spor individual, plata la
    contract). Se pun de mână în fila „Salariu” sau vin dintr-un document: punctul ordinului de personal (`order_item`) ori
    rândul documentului „Modificarea acumulărilor planificate” (`change_line`); cele din documente se schimbă / se opresc
    doar printr-un document (anularea lui le întoarce)."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="pay_items")
    employment = models.ForeignKey(Employment, on_delete=models.CASCADE, null=True, blank=True, related_name="pay_items",
                                   verbose_name="Raportul de muncă (gol = cel de bază)")
    pay_type = models.ForeignKey(PayType, on_delete=models.PROTECT, related_name="employee_items", verbose_name="Tipul")
    amount = models.DecimalField("Suma pe lună (lei)", max_digits=12, decimal_places=2, null=True, blank=True)
    percent = models.DecimalField("Procentul", max_digits=7, decimal_places=3, null=True, blank=True)
    quantity = models.DecimalField("Cantitatea (ore, zile, bucăți)", max_digits=12, decimal_places=3, null=True, blank=True)
    date_from = models.DateField("De la")
    date_to = models.DateField("Până la", null=True, blank=True)
    document = models.CharField("Temeiul (ordinul, titlul executoriu, cererea)", max_length=200, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.PROTECT, null=True, blank=True, related_name="pay_items",
                                   verbose_name="Din punctul ordinului")
    change_line = models.ForeignKey("PayItemChangeLine", on_delete=models.PROTECT, null=True, blank=True, related_name="pay_items",
                                    verbose_name="Din documentul „Modificarea acumulărilor planificate”")

    class Meta:
        ordering = ["employee", "pay_type__category", "date_from"]
        verbose_name = "Sporul / reținerea angajatului"

    @property
    def from_document(self) -> bool:
        return bool(self.order_item_id or self.change_line_id)


class OccupationPayItem(models.Model):
    """Acumularea-tip a funcției: la angajare tabelul „Acumulări și rețineri” al ordinului se completează din ea."""

    occupation = models.ForeignKey("org.Occupation", on_delete=models.CASCADE, related_name="pay_items")
    pay_type = models.ForeignKey(PayType, on_delete=models.PROTECT, related_name="occupation_items", verbose_name="Tipul")
    amount = models.DecimalField("Suma (lei)", max_digits=12, decimal_places=2, null=True, blank=True)
    percent = models.DecimalField("Procentul", max_digits=7, decimal_places=3, null=True, blank=True)
    quantity = models.DecimalField("Cantitatea", max_digits=12, decimal_places=3, null=True, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "Acumularea-tip a funcției"


class PayItemChange(models.Model):
    """Documentul „Modificarea acumulărilor planificate”: schimbările fără ordin de personal (titlul executoriu, cotizația
    sindicală la cerere, tichetele de masă…) pentru unul sau mai mulți angajați. Aprobat — rândurile intră în fila
    „Salariu”; anularea aprobării le întoarce."""

    STATUSES = [("draft", "Ciornă"), ("approved", "Aprobat")]
    number = models.CharField("Numărul", max_length=30, blank=True)
    date = models.DateField("Data", default=timezone.localdate)
    status = models.CharField(max_length=10, choices=STATUSES, default="draft", db_index=True)
    note = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "Modificarea acumulărilor planificate"

    def __str__(self):
        return f"Modificarea acumulărilor planificate nr. {self.number or '—'} din {self.date:%d.%m.%Y}"

    def reference(self) -> str:
        return f"nr. {self.number} din {self.date:%d.%m.%Y}" if self.number else f"din {self.date:%d.%m.%Y}"


PAY_ACTIONS = [("add", "Adaugă"), ("modify", "Modifică"), ("stop", "Oprește")]


class PayItemChangeLine(models.Model):
    """Un rând al documentului: angajatul, raportul de muncă, tipul, acțiunea, valorile, perioada, temeiul."""

    change = models.ForeignKey(PayItemChange, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="pay_item_changes")
    employment = models.ForeignKey(Employment, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
                                   verbose_name="Raportul de muncă (gol = cel de bază)")
    pay_type = models.ForeignKey(PayType, on_delete=models.PROTECT, related_name="+", verbose_name="Tipul")
    action = models.CharField("Acțiunea", max_length=6, choices=PAY_ACTIONS, default="add")
    target = models.ForeignKey(EmployeePayItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                               verbose_name="Rândul care se modifică / se oprește")
    amount = models.DecimalField("Suma (lei)", max_digits=12, decimal_places=2, null=True, blank=True)
    percent = models.DecimalField("Procentul", max_digits=7, decimal_places=3, null=True, blank=True)
    quantity = models.DecimalField("Cantitatea", max_digits=12, decimal_places=3, null=True, blank=True)
    date_from = models.DateField("De la (gol = data documentului)", null=True, blank=True)
    date_to = models.DateField("Până la", null=True, blank=True)
    document = models.CharField("Temeiul (titlul executoriu, cererea…)", max_length=200, blank=True)
    result = models.JSONField("Ce s-a schimbat la aprobare (pentru anulare)", default=dict, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "Rândul modificării acumulărilor planificate"


def next_month(day):
    """Prima zi a lunii următoare."""
    return (day.replace(day=1) + timedelta(days=32)).replace(day=1)


# Codul fiscal, art. 33 alin. (2) lit. a)–f): categoriile cu scutire majorată (M) — textul literei e în Codul fiscal
MAJOR_CATEGORIES = [(c, f"art. 33 alin. (2) lit. {c})") for c in "abcdef"]


class ExemptionRequest(models.Model):
    """Cererea angajatului privind acordarea scutirilor la impozitul pe venit (Codul fiscal, art. 33–35; anexa 6 la
    Regulamentul aprobat prin HG 697/2014). Nu se reînnoiește anual: e valabilă de la / până la și se înlocuiește cu o cerere
    nouă la orice schimbare (pct. 22 din Regulament — în 10 zile); se aplică din luna următoare depunerii. Persoanele
    întreținute sunt rânduri (`ExemptionDependent`), fiecare cu perioada dreptului ei."""

    KINDS = [("none", "Fără scutire personală"), ("personal", "Scutirea personală (P)"), ("major", "Scutirea personală majorată (M)")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="exemptions")
    number = models.CharField("Numărul de înregistrare", max_length=30, blank=True)
    date = models.DateField("Data depunerii", default=timezone.localdate)
    date_from = models.DateField("Se aplică din (gol = luna următoare depunerii)", null=True, blank=True)
    date_to = models.DateField("Valabilă până la (gol = până la o cerere nouă)", null=True, blank=True)
    kind = models.CharField("Scutirea personală", max_length=10, choices=KINDS, default="personal")
    major_category = models.CharField("Categoria scutirii majorate (CF art. 33 alin. (2))", max_length=1, choices=MAJOR_CATEGORIES,
                                      blank=True)
    major_document = models.CharField("Documentul pentru scutirea majorată", max_length=200, blank=True)
    spouse_major = models.BooleanField("Scutirea pentru soț / soție (Sm, CF art. 34 alin. (2))", default=False)
    spouse_name = models.CharField("Soțul / soția (numele, prenumele)", max_length=200, blank=True)
    spouse_idnp = models.CharField("Codul fiscal (IDNP) al soțului / soției (IALS21, col. 4)", max_length=13, blank=True)
    spouse_category = models.CharField("Categoria soțului / soției (CF art. 33 alin. (2))", max_length=1, choices=MAJOR_CATEGORIES,
                                       blank=True)
    spouse_document = models.CharField("Documentul soțului / soției", max_length=200, blank=True)
    waiver_date = models.DateField("Renunțarea la P / M (venitul anual peste plafon): data cererii", null=True, blank=True)
    # HG 697/2014, Regulamentul, pct. 9: scutirea se cere la locul de muncă de bază sau la cel prin cumul — o singură dată
    PLACES = [("main", "Locul de muncă de bază"), ("secondary", "Locul de muncă prin cumul")]
    place = models.CharField("Cererea e depusă la acest angajator ca", max_length=10, choices=PLACES, default="main")
    documents = models.CharField("Alte documente anexate", max_length=300, blank=True)
    needs_review = models.BooleanField("De verificat", default=False)
    review_note = models.CharField("Ce trebuie verificat", max_length=300, blank=True)
    is_active = models.BooleanField("Activă (necontestată / neanulată)", default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "Cerere de scutire"

    def __str__(self):
        return f"Cererea de scutire {self.code()} din {self.date:%d.%m.%Y}"

    def save(self, *args, **kwargs):
        if self.date_from is None and self.date:
            self.date_from = next_month(self.date)  # se aplică din luna următoare depunerii
        super().save(*args, **kwargs)

    def replace_previous(self):
        """Cererea nouă o înlocuiește pe cea în vigoare (pct. 22 din Regulament): cea veche se închide în ajunul cererii noi;
        una care ar începe abia după cererea nouă se anulează."""
        start = self.date_from or next_month(self.date)
        for old in ExemptionRequest.objects.filter(employee_id=self.employee_id, is_active=True).exclude(pk=self.pk):
            if old.date_to is not None and old.date_to < start:
                continue
            if (old.date_from or next_month(old.date)) >= start:
                old.is_active = False
                old.save(update_fields=["is_active"])
            else:
                old.date_to = start - timedelta(days=1)
                old.save(update_fields=["date_to"])

    def valid_in(self, first) -> bool:
        """Cererea e în vigoare în luna care începe la `first`."""
        start = (self.date_from or next_month(self.date)).replace(day=1)
        return self.is_active and start <= first and (self.date_to is None or self.date_to >= first)

    def personal_in(self, first) -> str:
        """P / M în luna dată: din luna următoare renunțării nu se mai acordă (fără recalcularea lunilor trecute)."""
        if self.kind == "none" or (self.waiver_date and first >= next_month(self.waiver_date)):
            return ""
        return {"personal": "P", "major": "M"}[self.kind]

    def dependents_in(self, first) -> list:
        return [d for d in self.dependents.all() if d.valid_in(first)]

    def code(self, first=None) -> str:
        """Codul scutirilor din cerere (pe lună, dacă se dă `first`): P / M, Sm, Nx (întreținuți), Hx (cu dizabilitate)."""
        deps = self.dependents_in(first) if first else [d for d in self.dependents.all() if d.income_ok]
        parts = [self.personal_in(first) if first else {"personal": "P", "major": "M"}.get(self.kind, "")]
        if self.spouse_major:
            parts.append("Sm")
        normal = sum(1 for d in deps if d.code == "N")
        disabled = sum(1 for d in deps if d.code == "H")
        if normal:
            parts.append(f"N{normal}")
        if disabled:
            parts.append(f"H{disabled}")
        return "".join(parts) or "—"


class ExemptionDependent(models.Model):
    """Persoana întreținută din cererea de scutire (CF art. 35): N, sau H dacă are dizabilitate din copilărie, severă sau
    accentuată. Scutirea se aplică din luna următoare lunii apariției dreptului (art. 35 alin. (4)) — `date_from`; până la
    `date_to` inclusiv (luna încetării dreptului). Venitul anual al persoanei nu trebuie să depășească plafonul (12 400 lei)."""

    RELATIONS = [("child", "Copil"), ("parent", "Părinte"), ("sibling", "Frate / soră (doar cu dizabilitate)"),
                 ("other", "Altă persoană întreținută")]
    DISABILITIES = [("", "Fără dizabilitate"), ("childhood", "Dizabilitate din copilărie"), ("severe", "Dizabilitate severă"),
                    ("accentuated", "Dizabilitate accentuată"), ("medium", "Dizabilitate medie")]
    H_DISABILITIES = {"childhood", "severe", "accentuated"}
    request = models.ForeignKey(ExemptionRequest, on_delete=models.CASCADE, related_name="dependents")
    family_member = models.ForeignKey("staff.FamilyMember", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                                      verbose_name="Membrul familiei din dosar")
    name = models.CharField("Numele, prenumele", max_length=160)
    idnp = models.CharField("Codul fiscal (IDNP)", max_length=13, blank=True)
    birth_date = models.DateField("Data nașterii", null=True, blank=True)
    relation = models.CharField("Rudenia", max_length=10, choices=RELATIONS, default="child")
    disability = models.CharField("Dizabilitatea", max_length=12, choices=DISABILITIES, blank=True)
    date_from = models.DateField("Dreptul a apărut la (gol = de la cerere)", null=True, blank=True)
    date_to = models.DateField("Dreptul încetează la", null=True, blank=True)
    document = models.CharField("Documentul (certificatul de naștere, de dizabilitate...)", max_length=200, blank=True)
    income_ok = models.BooleanField("Venitul anual al persoanei nu depășește plafonul (CF art. 35)", default=True)
    note = models.CharField("Observații", max_length=200, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "Persoana întreținută"

    @property
    def code(self) -> str:
        return "H" if self.disability in self.H_DISABILITIES else "N"

    def valid_in(self, first) -> bool:
        if not self.income_ok:
            return False
        if self.date_from and next_month(self.date_from) > first:
            return False
        return self.date_to is None or self.date_to >= first


class Payroll(models.Model):
    """Calculul salariului pe lună (toată întreprinderea sau o subdiviziune): acumulările, reținerile și CAS al angajatorului.
    Impozitul pe venit și CNAM nu sunt aici — se rețin la plată, în îndreptarea spre plată (Payment) făcută în baza lui."""

    STATUSES = [("draft", "Ciornă"), ("checked", "Verificat"), ("approved", "Aprobat")]
    number = models.CharField("Numărul", max_length=30, blank=True)
    date = models.DateField("Data", default=timezone.localdate)
    year = models.PositiveSmallIntegerField("Anul")
    month = models.PositiveSmallIntegerField("Luna")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, null=True, blank=True, related_name="payrolls",
                                    verbose_name="Subdiviziunea (gol = toată întreprinderea)")
    status = models.CharField(max_length=10, choices=STATUSES, default="draft", db_index=True)
    totals = models.JSONField(default=dict, blank=True)
    note = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    calculated_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-year", "-month", "-id"]
        verbose_name = "Calculul salariului"

    def __str__(self):
        return f"Calculul salariului {self.month:02d}.{self.year}" + (f" — {self.subdivision.name_ro}" if self.subdivision_id else "")


class PayrollLine(models.Model):
    """Un raport de muncă în calcul: datele din pontaj și totalurile — brutul, bazele impozitului și CNAM (din care
    îndreptarea spre plată socotește impozitul și CNAM), CAS, celelalte rețineri și restul înainte de impozit."""

    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="payroll_lines")
    employment = models.ForeignKey(Employment, on_delete=models.PROTECT, related_name="payroll_lines")
    info = models.JSONField("Funcția, subdiviziunea, norma, salariul, pontajul (la data calculului)", default=dict, blank=True)
    gross = models.DecimalField("Brut (acumulări)", max_digits=12, decimal_places=2, default=ZERO)
    taxable = models.DecimalField("Baza impozitului pe venit (acumulările impozabile)", max_digits=12, decimal_places=2, default=ZERO)
    cnam_base = models.DecimalField("Baza CNAM", max_digits=12, decimal_places=2, default=ZERO)
    cas = models.DecimalField("CAS (angajator)", max_digits=12, decimal_places=2, default=ZERO)
    deductions = models.DecimalField("Alte rețineri", max_digits=12, decimal_places=2, default=ZERO)
    net = models.DecimalField("Brutul minus reținerile (înainte de impozit și CNAM)", max_digits=12, decimal_places=2, default=ZERO)
    # regimul IT Park (CF art. 377 alin. (1)): salariul din CIM e impozitat final — fără impozit, CNAM și CAS; rămâne regimul
    # lunii calculului și când se plătește într-o lună cu alt regim (art. 375)
    it_park = models.BooleanField("Impozitat final — impozit unic IT Park", default=False)
    note = models.CharField("Observații", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        constraints = [models.UniqueConstraint(fields=["payroll", "employment"], name="uniq_payroll_line")]


class PayrollItem(models.Model):
    """O acumulare / reținere din calcul: tipul, cantitatea (ore, zile), baza, procentul, suma; „manual” rămâne la recalculare."""

    line = models.ForeignKey(PayrollLine, on_delete=models.CASCADE, related_name="items")
    pay_type = models.ForeignKey(PayType, on_delete=models.PROTECT, related_name="items")
    quantity = models.DecimalField("Cantitatea (ore / zile)", max_digits=10, decimal_places=2, null=True, blank=True)
    base = models.DecimalField("Baza", max_digits=12, decimal_places=2, null=True, blank=True)
    percent = models.DecimalField("Procentul", max_digits=7, decimal_places=3, null=True, blank=True)
    amount = models.DecimalField("Suma", max_digits=12, decimal_places=2, default=ZERO)
    taxable_part = models.DecimalField("Din care impozabil", max_digits=12, decimal_places=2, default=ZERO)
    manual = models.BooleanField("Scris de mână", default=False)
    note = models.CharField("Explicația", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]


class Payment(models.Model):
    """Îndreptarea spre plată (salariu sau avans): la ea se rețin CNAM și impozitul pe venit. Salariul se completează din
    calculul aprobat ales (`payroll`, documentul de bază) sau, fără el, pe sold — restul lunii din toate calculele aprobate.
    Apoi achitarea (card — fișierul pentru bancă; numerar — casa)."""

    KINDS = [("salary", "Salariu"), ("advance", "Avans")]
    METHODS = [("all", "Card și numerar"), ("card", "Card (transfer la bancă)"), ("cash", "Numerar (casa)")]
    STATUSES = [("draft", "Ciornă"), ("approved", "Aprobat"), ("paid", "Achitat")]
    number = models.CharField("Numărul", max_length=30, blank=True)
    date = models.DateField("Data", default=timezone.localdate)
    year = models.PositiveSmallIntegerField("Anul")
    month = models.PositiveSmallIntegerField("Luna")
    kind = models.CharField("Ce se plătește", max_length=8, choices=KINDS, default="salary")
    payroll = models.ForeignKey(Payroll, on_delete=models.PROTECT, null=True, blank=True, related_name="payments",
                                verbose_name="În baza calculului (gol = pe sold)")
    method = models.CharField("Modalitatea", max_length=5, choices=METHODS, default="all")
    status = models.CharField(max_length=10, choices=STATUSES, default="draft", db_index=True)
    paid_on = models.DateField("Achitat la", null=True, blank=True)
    reference = models.CharField("Documentul de plată (ordinul de plată, dispoziția de casă)", max_length=120, blank=True)
    note = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-year", "-month", "-date", "-id"]
        verbose_name = "Îndreptarea spre plată"

    def __str__(self):
        return f"{self.get_kind_display()} {self.month:02d}.{self.year} nr. {self.number}"


class PaymentLine(models.Model):
    """Un angajat în îndreptarea spre plată. Impozitul se reține aici: la avans — din suma avansului (CNAM 9 %, apoi 12 %
    din rest); la salariu — CNAM, scutirea și impozitul pe tot venitul plătit în lună, minus ce s-a reținut deja la plățile ei.
    `amount` e suma de plată (netul); `basis` ține sumele puse la completare, ca o corectare să le poată împărți la fel."""

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="payment_lines")
    method = models.CharField("Modalitatea", max_length=5, choices=[("card", "Card"), ("cash", "Numerar")], default="card")
    iban = models.CharField("IBAN", max_length=34, blank=True)
    gross = models.DecimalField("Venitul achitat (brut)", max_digits=12, decimal_places=2, default=ZERO)
    exemption = models.DecimalField("Scutirea", max_digits=12, decimal_places=2, default=ZERO)
    cnam = models.DecimalField("CNAM reținut", max_digits=12, decimal_places=2, default=ZERO)
    income_tax = models.DecimalField("Impozitul reținut", max_digits=12, decimal_places=2, default=ZERO)
    deductions = models.DecimalField("Alte rețineri", max_digits=12, decimal_places=2, default=ZERO)
    final_gross = models.DecimalField("Din venit: salariul impozitat final (IT Park)", max_digits=12, decimal_places=2, default=ZERO)
    basis = models.JSONField("Sumele de la completare", default=dict, blank=True)
    manual = models.BooleanField("Corectat de mână", default=False)
    amount = models.DecimalField("Suma de plată (net)", max_digits=12, decimal_places=2, default=ZERO)
    note = models.CharField("Observații", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        constraints = [models.UniqueConstraint(fields=["payment", "employee"], name="uniq_payment_line")]


class PayslipDispatch(models.Model):
    """Trimiterea fluturașului pe e-mail (arhivă ZIP cu parolă — ultimele 5 cifre ale IDNP): cui, la ce adresă, rezultatul.
    Se trimite din îndreptarea spre plată pe salariu (`payment`); trimiterile de până la 1.5.1 țin calculul (`payroll`)."""

    STATUSES = [("sent", "Trimis"), ("skipped", "Netrimis"), ("error", "Eroare")]
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True, related_name="dispatches")
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, null=True, blank=True, related_name="dispatches")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payslip_dispatches")
    email = models.CharField("Adresa", max_length=254, blank=True)
    status = models.CharField(max_length=8, choices=STATUSES, default="sent")
    message = models.CharField("Motivul / eroarea", max_length=300, blank=True)
    sent_at = models.DateTimeField(default=timezone.now)
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-sent_at", "-id"]
        verbose_name = "Trimiterea fluturașului"


class FiscalRegime(models.Model):
    """Regimul fiscal al întreprinderii, cu istoric: general sau rezident IT Park (Legea 77/2016; Codul fiscal, titlul X,
    cap. 1, art. 367–379). Regimul nou se aplică din luna următoare obținerii / retragerii statutului (art. 375 alin. (1)) —
    `date_from` e mereu prima zi a lunii; lunile vechi se calculează după regimul lor."""

    REGIMES = [("general", "Regimul general"), ("it_park", "Rezident IT Park (impozitul unic)")]
    regime = models.CharField("Regimul", max_length=10, choices=REGIMES, default="general")
    date_from = models.DateField("În vigoare din (luna)")
    status_date = models.DateField("Data obținerii / retragerii statutului", null=True, blank=True)
    document = models.CharField("Temeiul (certificatul de rezident, decizia)", max_length=200, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date_from"]
        verbose_name = "Regimul fiscal"
        constraints = [models.UniqueConstraint(fields=["date_from"], name="uniq_fiscal_regime_month")]

    def __str__(self):
        return f"{self.get_regime_display()} din {self.date_from:%m.%Y}"

    def save(self, *args, **kwargs):
        if self.date_from is None and self.status_date:
            self.date_from = next_month(self.status_date)  # din luna următoare obținerii / retragerii statutului
        if self.date_from:
            self.date_from = self.date_from.replace(day=1)
        super().save(*args, **kwargs)


class ItParkMonth(models.Model):
    """Datele lunii pentru impozitul unic (declarația IU17): venitul din vânzări îl scrie contabilul (HR nu-l are); numărul
    angajaților și impozitul se calculează (apps.payroll.it_park)."""

    year = models.PositiveSmallIntegerField("Anul")
    month = models.PositiveSmallIntegerField("Luna")
    sales_income = models.DecimalField("Venitul din vânzări al lunii (lei)", max_digits=14, decimal_places=2, null=True, blank=True)
    submitted_on = models.DateField("IU17 depusă la", null=True, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-year", "-month"]
        verbose_name = "Impozitul unic IT Park — luna"
        constraints = [models.UniqueConstraint(fields=["year", "month"], name="uniq_it_park_month")]

    def __str__(self):
        return f"Impozitul unic IT Park {self.month:02d}.{self.year}"
