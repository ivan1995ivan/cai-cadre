"""Salarizarea (Etapa 4b, partea 1): constantele cu istoric, tipurile de calcul flexibile, cererea de scutire,
reținerile / sporurile personale și calculul lunar al salariului (angajat × raport de muncă × tip de calcul).

Totul se calculează pe **raportul de muncă** (de bază, cumul, suplinire, contract de prestări servicii — fiecare cu
norma și salariul lui); scutirea de impozit se acordă o singură dată pe persoană, la raportul de bază.
"""
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
        ("scale", "% după treapta de vechime / categoria de calificare"),
    ]
    # cheia motorului de calcul pentru formula „auto” (apps.payroll.engine)
    AUTO = [
        ("salary", "Salariul de funcție (pro-rata la orele lucrate)"), ("allowance", "Sporurile fixe din raportul de muncă (%)"),
        ("combination", "Plata pentru cumul (% din salariul de funcție)"), ("night", "Munca de noapte (+ % la tariful orar)"),
        ("holiday", "Munca în zile de sărbătoare (+ % la tariful orar)"), ("overtime", "Ore suplimentare (+ % la tariful orar)"),
        ("leave", "Indemnizația de concediu de odihnă (media × zile)"), ("leave_comp", "Compensarea concediului nefolosit"),
        ("sick", "Incapacitate temporară: zilele plătite de angajator"), ("bonus", "Premii din ordine"),
        ("aid", "Ajutor material din ordine"), ("advance", "Avansul plătit (se ia din plăți, pe fluturaș)"),
        ("income_tax", "Impozitul pe venit (se reține la plată)"), ("cnam", "Prima de asigurare medicală (se reține la plată)"),
        ("cas", "Contribuția de asigurări sociale (angajator)"), ("none", "—"),
    ]
    code = models.CharField("Codul", max_length=24, unique=True)
    name_ro = models.CharField("Denumire (RO)", max_length=200)
    name_ru = models.CharField("Denumire (RU)", max_length=200, blank=True)
    name_en = models.CharField("Denumire (EN)", max_length=200, blank=True)
    category = models.CharField("Categoria", max_length=10, choices=CATEGORIES, default="accrual")
    formula = models.CharField("Formula", max_length=12, choices=FORMULAS, default="fixed")
    auto = models.CharField("Calculul automat", max_length=16, choices=AUTO, default="none")
    percent = models.DecimalField("Procentul (la formulele cu %)", max_digits=7, decimal_places=3, default=ZERO)
    base_codes = models.JSONField("Baza de calcul (codurile tipurilor)", default=list, blank=True)
    scale = models.JSONField("Treptele {de la (ani) / categoria: %}", default=list, blank=True)
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
    """Sporurile și reținerile personale, permanente: sindicat, pensie alimentară, împrumut, spor individual, plata la contract."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="pay_items")
    employment = models.ForeignKey(Employment, on_delete=models.CASCADE, null=True, blank=True, related_name="pay_items",
                                   verbose_name="Raportul de muncă (gol = cel de bază)")
    pay_type = models.ForeignKey(PayType, on_delete=models.PROTECT, related_name="employee_items", verbose_name="Tipul")
    amount = models.DecimalField("Suma pe lună (lei)", max_digits=12, decimal_places=2, null=True, blank=True)
    percent = models.DecimalField("Procentul", max_digits=7, decimal_places=3, null=True, blank=True)
    date_from = models.DateField("De la")
    date_to = models.DateField("Până la", null=True, blank=True)
    document = models.CharField("Temeiul (ordinul, titlul executoriu, cererea)", max_length=200, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)

    class Meta:
        ordering = ["employee", "pay_type__category", "date_from"]
        verbose_name = "Sporul / reținerea angajatului"


class ExemptionRequest(models.Model):
    """Cererea de scutire la impozitul pe venit (Codul fiscal, art. 33–35): pe an, cu persoanele întreținute."""

    KINDS = [("none", "Fără scutire personală"), ("personal", "Scutirea personală (P)"), ("major", "Scutirea personală majorată (M)")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="exemptions")
    year = models.PositiveSmallIntegerField("Anul")
    date = models.DateField("Data depunerii", default=timezone.localdate)
    kind = models.CharField("Scutirea personală", max_length=10, choices=KINDS, default="personal")
    spouse = models.BooleanField("Scutirea pentru soț / soție (S)", default=False)
    spouse_name = models.CharField("Soțul / soția (numele, IDNP)", max_length=200, blank=True)
    spouse_idnp = models.CharField("IDNP-ul soțului / soției (IALS21, col. 4)", max_length=13, blank=True)
    dependents = models.JSONField("Persoanele întreținute [{name, idnp, disabled}]", default=list, blank=True)
    documents = models.CharField("Documentele anexate", max_length=300, blank=True)
    date_from = models.DateField("Se aplică din", null=True, blank=True)
    is_active = models.BooleanField("Activă", default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-year", "-date"]
        verbose_name = "Cerere de scutire"
        constraints = [models.UniqueConstraint(fields=["employee", "year"], name="uniq_exemption_year")]

    def code(self) -> str:
        """Codul scutirii din cerere: P / M + S + N (întreținuți) + H (întreținut cu dizabilitate)."""
        parts = [{"personal": "P", "major": "M"}.get(self.kind, "")]
        if self.spouse:
            parts.append("S")
        normal = [d for d in self.dependents if not d.get("disabled")]
        disabled = [d for d in self.dependents if d.get("disabled")]
        if normal:
            parts.append(f"N{len(normal)}")
        if disabled:
            parts.append(f"H{len(disabled)}")
        return "".join(parts) or "—"


class Payroll(models.Model):
    """Calculul salariului pe lună (toată instituția sau o subdiviziune): acumulările, reținerile și CAS al angajatorului.
    Impozitul pe venit și CNAM nu sunt aici — se rețin la plată, în îndreptarea spre plată (Payment) făcută în baza lui."""

    STATUSES = [("draft", "Ciornă"), ("checked", "Verificat"), ("approved", "Aprobat")]
    number = models.CharField("Numărul", max_length=30, blank=True)
    date = models.DateField("Data", default=timezone.localdate)
    year = models.PositiveSmallIntegerField("Anul")
    month = models.PositiveSmallIntegerField("Luna")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, null=True, blank=True, related_name="payrolls",
                                    verbose_name="Subdiviziunea (gol = toată instituția)")
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
