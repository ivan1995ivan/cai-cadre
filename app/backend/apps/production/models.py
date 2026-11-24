"""Producția — salarizarea în acord (S5a, PLAN-SRL.md): grila tarifară, nomenclatorul lucrărilor cu normele și tarifele lor,
brigăzile și raportul de producție (volumele lucrate, rebutul).

Drumul: lucrarea (operația / produsul) are, cu istoric, **norma** (de timp — ore pe unitate, sau de producție — unități pe
oră) și **categoria lucrării** din grila tarifară; tariful pe unitate = tariful pe oră al categoriei × norma de timp (CM
art. 170: tariful categoriei ÷ norma de producție pe oră) sau un tarif scris direct. Raportul de producție aprobat (individual
sau pe brigadă) intră în calculul salariului lunii lui (apps.payroll.engine → apps.production.services.month_summary).

Mărimile care țin de întreprindere (tarifele, coeficienții categoriilor, treptele acordului progresiv, procentul de plată a
rebutului parțial) nu se preîncarcă: le scrie utilizatorul din contractul colectiv / regulamentul de salarizare.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.org.models import Subdivision
from apps.staff.models import Employment

ZERO = Decimal("0")


class TariffGrid(models.Model):
    """Grila tarifară (CM art. 130, 170; contractul colectiv / regulamentul de salarizare): tariful pe oră al categoriei I și
    coeficienții categoriilor, „în vigoare din”. O grilă nouă din altă dată = rând nou cu același cod; lucrările țin codul
    grilei și categoria, iar tariful se ia din versiunea în vigoare la data lucrării."""

    code = models.CharField("Codul", max_length=16)
    name = models.CharField("Denumirea", max_length=160)
    date_from = models.DateField("În vigoare din")
    base_rate = models.DecimalField("Tariful pe oră al categoriei I (lei)", max_digits=10, decimal_places=2)
    document = models.CharField("Temeiul (contractul colectiv, regulamentul de salarizare)", max_length=200, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["code", "-date_from"]
        verbose_name = "Grila tarifară"
        constraints = [models.UniqueConstraint(fields=["code", "date_from"], name="uniq_tariff_grid")]

    def __str__(self):
        return f"{self.code} {self.name} din {self.date_from:%d.%m.%Y}"


class TariffRank(models.Model):
    """Categoria grilei: coeficientul față de categoria I; tariful pe oră = tariful categoriei I × coeficientul, sau scris
    direct (`rate`)."""

    grid = models.ForeignKey(TariffGrid, on_delete=models.CASCADE, related_name="ranks")
    rank = models.PositiveSmallIntegerField("Categoria")
    coefficient = models.DecimalField("Coeficientul", max_digits=6, decimal_places=3, default=Decimal("1"))
    rate = models.DecimalField("Tariful pe oră scris direct (lei; gol — categoria I × coeficientul)", max_digits=10,
                               decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["grid", "rank"]
        verbose_name = "Categoria grilei tarifare"
        constraints = [models.UniqueConstraint(fields=["grid", "rank"], name="uniq_tariff_rank")]

    def hourly(self) -> Decimal:
        if self.rate is not None:
            return self.rate
        return (self.grid.base_rate * self.coefficient).quantize(Decimal("0.01"))


UNITS = [("buc", "bucăți"), ("set", "seturi"), ("kg", "kg"), ("t", "tone"), ("m", "metri"), ("m2", "m²"), ("m3", "m³"),
         ("l", "litri"), ("op", "operații"), ("other", "alta")]


class Operation(models.Model):
    """Lucrarea în acord (operația, produsul): unitatea de măsură, secția, dacă se plătește progresiv peste normă; normele și
    tarifele — cu istoric, în `OperationRate`."""

    code = models.CharField("Codul", max_length=24, unique=True)
    name_ro = models.CharField("Denumire (RO)", max_length=200)
    name_ru = models.CharField("Denumire (RU)", max_length=200, blank=True)
    name_en = models.CharField("Denumire (EN)", max_length=200, blank=True)
    unit = models.CharField("Unitatea de măsură", max_length=8, choices=UNITS, default="buc")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
                                    verbose_name="Secția / atelierul (gol — toate)")
    progressive = models.BooleanField("Acord progresiv: producția peste normă se plătește după treptele tipului ACORDP",
                                      default=False)
    note = models.CharField("Observații", max_length=300, blank=True)
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["sort", "code"]
        verbose_name = "Lucrarea în acord"

    def __str__(self):
        return f"{self.code} — {self.name_ro}"


NORM_KINDS = [("time", "Norma de timp (ore pe unitate)"), ("output", "Norma de producție (unități pe oră)")]


class OperationRate(models.Model):
    """Norma și tariful lucrării din data dată. Tariful pe unitate: scris direct (`piece_rate`) sau tariful pe oră al categoriei
    lucrării (`grid_code` + `rank`) × norma de timp."""

    operation = models.ForeignKey(Operation, on_delete=models.CASCADE, related_name="rates")
    date_from = models.DateField("În vigoare din")
    norm_kind = models.CharField("Norma", max_length=6, choices=NORM_KINDS, default="time")
    norm_value = models.DecimalField("Mărimea normei", max_digits=12, decimal_places=4)
    grid_code = models.CharField("Grila tarifară (codul)", max_length=16, blank=True)
    rank = models.PositiveSmallIntegerField("Categoria lucrării", null=True, blank=True)
    piece_rate = models.DecimalField("Tariful pe unitate scris direct (lei; gol — din grilă)", max_digits=12, decimal_places=4,
                                     null=True, blank=True)
    document = models.CharField("Temeiul (ordinul, regulamentul de normare)", max_length=200, blank=True)

    class Meta:
        ordering = ["operation", "-date_from"]
        verbose_name = "Norma și tariful lucrării"
        constraints = [models.UniqueConstraint(fields=["operation", "date_from"], name="uniq_operation_rate")]

    def norm_time(self) -> Decimal:
        """Norma de timp: ore pe o unitate."""
        if not self.norm_value:
            return ZERO
        return self.norm_value if self.norm_kind == "time" else Decimal(1) / self.norm_value


class Brigade(models.Model):
    """Brigada (echipa) în acord: suma ei din raportul de producție se împarte membrilor după ore × coeficientul de participare
    (KTU), sau după ore × tariful orar al membrului × coeficient."""

    DISTRIBUTIONS = [("hours", "Ore lucrate × coeficientul de participare"),
                     ("tariff", "Ore lucrate × tariful orar al membrului × coeficientul de participare")]
    code = models.CharField("Codul", max_length=16, unique=True)
    name = models.CharField("Denumirea", max_length=160)
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
                                    verbose_name="Secția / atelierul")
    distribution = models.CharField("Împărțirea sumei", max_length=8, choices=DISTRIBUTIONS, default="hours")
    leader = models.ForeignKey(Employment, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                               verbose_name="Brigadierul")
    note = models.CharField("Observații", max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["code"]
        verbose_name = "Brigada"

    def __str__(self):
        return f"{self.code} — {self.name}"


class BrigadeMember(models.Model):
    """Membrul brigăzii (raportul de muncă), cu coeficientul de participare implicit și perioada în brigadă."""

    brigade = models.ForeignKey(Brigade, on_delete=models.CASCADE, related_name="members")
    employment = models.ForeignKey(Employment, on_delete=models.CASCADE, related_name="brigade_memberships",
                                   verbose_name="Raportul de muncă")
    coefficient = models.DecimalField("Coeficientul de participare (KTU)", max_digits=5, decimal_places=2, default=Decimal("1"))
    date_from = models.DateField("În brigadă de la")
    date_to = models.DateField("Până la", null=True, blank=True)

    class Meta:
        ordering = ["brigade", "date_from", "id"]
        verbose_name = "Membrul brigăzii"

    def in_force(self, day) -> bool:
        return self.date_from <= day and (self.date_to is None or self.date_to >= day)


class ProductionReport(models.Model):
    """Raportul de producție (bonul de lucru în acord): lucrările făcute de un angajat sau de o brigadă — cantitatea bună,
    rebutul pe vinovați (CM art. 162) și orele. Aprobat, intră în calculul salariului lunii datei lui; tarifele se fixează pe
    rânduri la aprobare (o schimbare ulterioară a nomenclatorului nu schimbă raportul aprobat)."""

    KINDS = [("individual", "Individual"), ("brigade", "Pe brigadă")]
    STATUSES = [("draft", "Ciornă"), ("approved", "Aprobat")]
    number = models.CharField("Numărul", max_length=30, blank=True)
    date = models.DateField("Data (lucrările din luna ei)", default=timezone.localdate)
    kind = models.CharField("Felul", max_length=10, choices=KINDS, default="individual")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
                                    verbose_name="Secția / atelierul")
    brigade = models.ForeignKey(Brigade, on_delete=models.PROTECT, null=True, blank=True, related_name="reports",
                                verbose_name="Brigada")
    status = models.CharField(max_length=10, choices=STATUSES, default="draft", db_index=True)
    # garanția la neîndeplinirea normei (CM art. 161): din vina angajatorului — cel puțin salariul mediu pe orele lucrate;
    # fără vina părților — cel puțin 2/3 din salariul de bază (tariful categoriei); gol — norma îndeplinită sau din vina
    # lucrătorului (se plătește doar producția)
    SHORTFALL = [("employer", "Din vina angajatorului"), ("nobody", "Fără vina angajatorului și a lucrătorului")]
    shortfall_cause = models.CharField("Neîndeplinirea normei", max_length=10, choices=SHORTFALL, blank=True, default="",
                                       db_default="")
    note = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "Raportul de producție"

    def __str__(self):
        return f"Raportul de producție nr. {self.number or '—'} din {self.date:%d.%m.%Y}"

    def reference(self) -> str:
        return f"nr. {self.number} din {self.date:%d.%m.%Y}" if self.number else f"din {self.date:%d.%m.%Y}"


class ProductionLine(models.Model):
    """Lucrarea din raport: cantitatea bună, rebutul (fără vina lucrătorului — plătit ca produsul bun; parțial din vina lui —
    la procentul din contractul colectiv; total din vina lui — neplătit), orele lucrate. La raportul individual rândul are
    angajatul (raportul de muncă); la cel pe brigadă — nu (suma se împarte membrilor). Tariful, norma de timp, suma și orele
    normate se socotesc la salvare și se fixează la aprobare."""

    report = models.ForeignKey(ProductionReport, on_delete=models.CASCADE, related_name="lines")
    employment = models.ForeignKey(Employment, on_delete=models.PROTECT, null=True, blank=True, related_name="production_lines",
                                   verbose_name="Raportul de muncă (la raportul individual)")
    operation = models.ForeignKey(Operation, on_delete=models.PROTECT, related_name="lines", verbose_name="Lucrarea")
    quantity = models.DecimalField("Cantitatea bună", max_digits=12, decimal_places=3, default=ZERO)
    defect_nofault = models.DecimalField("Rebut fără vina lucrătorului", max_digits=12, decimal_places=3, default=ZERO)
    defect_partial = models.DecimalField("Rebut parțial din vina lucrătorului", max_digits=12, decimal_places=3, default=ZERO)
    defect_partial_pct = models.DecimalField("Plata rebutului parțial (% din tarif)", max_digits=6, decimal_places=2, null=True,
                                             blank=True)
    defect_worker = models.DecimalField("Rebut total din vina lucrătorului (neplătit)", max_digits=12, decimal_places=3, default=ZERO)
    hours = models.DecimalField("Orele lucrate efectiv", max_digits=7, decimal_places=2, null=True, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    # socotite (la salvare) și fixate (la aprobare)
    rate = models.DecimalField("Tariful pe unitate (lei)", max_digits=12, decimal_places=4, null=True, blank=True)
    norm_time = models.DecimalField("Norma de timp (ore pe unitate)", max_digits=12, decimal_places=6, null=True, blank=True)
    amount = models.DecimalField("Suma", max_digits=12, decimal_places=2, default=ZERO)
    normed_hours = models.DecimalField("Orele normate", max_digits=10, decimal_places=2, default=ZERO)
    how = models.CharField("Cum s-a socotit", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "Lucrarea din raportul de producție"


class ProductionMember(models.Model):
    """Membrul brigăzii în raport: orele lucrate și coeficientul de participare din luna raportului; partea lui din suma
    brigăzii și din orele normate se socotesc la salvare și se fixează la aprobare."""

    report = models.ForeignKey(ProductionReport, on_delete=models.CASCADE, related_name="members")
    employment = models.ForeignKey(Employment, on_delete=models.PROTECT, related_name="production_shares",
                                   verbose_name="Raportul de muncă")
    hours = models.DecimalField("Orele lucrate", max_digits=7, decimal_places=2, default=ZERO)
    coefficient = models.DecimalField("Coeficientul de participare (KTU)", max_digits=5, decimal_places=2, default=Decimal("1"))
    hourly = models.DecimalField("Tariful orar al membrului (la împărțirea după tarif)", max_digits=10, decimal_places=2, null=True,
                                 blank=True)
    amount = models.DecimalField("Partea din suma brigăzii", max_digits=12, decimal_places=2, default=ZERO)
    progressive_amount = models.DecimalField("Din ea — lucrările în acord progresiv", max_digits=12, decimal_places=2, default=ZERO)
    normed_hours = models.DecimalField("Partea din orele normate", max_digits=10, decimal_places=2, default=ZERO)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "Membrul brigăzii în raportul de producție"
        constraints = [models.UniqueConstraint(fields=["report", "employment"], name="uniq_production_member")]
