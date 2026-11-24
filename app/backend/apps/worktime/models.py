"""Timpul de muncă (Etapa 4, partea 2): turele, graficele de lucru, graficul de ture al subdiviziunii și tabela de pontaj.

Totul se ține pe **raportul de muncă** (`Employment`), nu pe persoană: angajatul cu funcția de bază într-o secție și cumul
în alta are câte un rând în fiecare grafic și în fiecare tabelă, cu norma lui.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.org.models import Subdivision
from apps.staff.models import Employment


class ShiftType(models.Model):
    """Codul turei din grafic și din pontaj: „8” (zi de 8 ore), „Z12” (tură de zi 08–20), „N12” (tură de noapte 20–08)."""

    code = models.CharField("Codul", max_length=8, unique=True)
    name = models.CharField("Denumirea", max_length=120)
    hours = models.DecimalField("Ore", max_digits=4, decimal_places=1)
    night_hours = models.DecimalField("Din ele noaptea (22–06)", max_digits=4, decimal_places=1, default=Decimal("0"))
    start = models.TimeField("Începe la", null=True, blank=True)
    color = models.CharField("Culoarea", max_length=9, blank=True)
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["sort", "code"]
        verbose_name = "Tură"

    def __str__(self):
        return f"{self.code} — {self.name}"


class WorkSchedule(models.Model):
    """Graficul de lucru: săptămânal (codul turei pe fiecare zi a săptămânii) sau ciclic (ture la rând, de la o dată)."""

    KINDS = [("week", "Săptămânal (5 / 6 zile)"), ("cycle", "Pe ture (ciclic)")]
    code = models.CharField("Codul", max_length=16, blank=True)
    name = models.CharField("Denumirea", max_length=120)
    kind = models.CharField("Tipul", max_length=6, choices=KINDS, default="week")
    weekly_hours = models.DecimalField("Ore pe săptămână (norma întreagă)", max_digits=4, decimal_places=1,
                                       default=Decimal("40"))
    week = models.JSONField("Turele pe zilele săptămânii (luni–duminică)", default=list, blank=True)
    cycle = models.JSONField("Turele ciclului, la rând", default=list, blank=True)
    cycle_start = models.DateField("Ciclul începe la", null=True, blank=True)
    holidays_off = models.BooleanField("Sărbătorile sunt zile libere", default=True)
    # evidența globală (cumulată) a timpului de muncă (CM art. 99): perioada de calcul în luni (1 — evidența lunară) și luna
    # cu care începe prima perioadă (gol — ianuarie); suplimentarele = orele peste norma perioadei, în ultima ei lună
    accounting_months = models.PositiveSmallIntegerField("Perioada de calcul (luni, evidența globală)", default=1, db_default=1)
    accounting_start = models.DateField("Prima perioadă de calcul începe cu luna", null=True, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Grafic de lucru"

    def __str__(self):
        return self.name


class JobSchedule(models.Model):
    """Graficul de lucru al unui raport de muncă, din data dată (cu decalajul în ciclu — echipa / brigada)."""

    employment = models.ForeignKey(Employment, on_delete=models.CASCADE, related_name="work_schedules")
    schedule = models.ForeignKey(WorkSchedule, on_delete=models.PROTECT, related_name="jobs", verbose_name="Graficul")
    date_from = models.DateField("Din data")
    cycle_offset = models.PositiveSmallIntegerField("Decalajul în ciclu (zile)", default=0)

    class Meta:
        ordering = ["employment", "-date_from", "-id"]
        verbose_name = "Graficul raportului de muncă"


class CalendarDay(models.Model):
    """Abaterile de la calendar: zile lucrătoare transferate (sâmbătă lucrătoare), zile libere declarate, zile scurtate."""

    date = models.DateField("Data", unique=True)
    working = models.BooleanField("Zi lucrătoare", default=True)
    hours_less = models.DecimalField("Mai puține ore (zi scurtată)", max_digits=3, decimal_places=1, default=Decimal("0"))
    note = models.CharField("Temeiul (hotărârea Guvernului)", max_length=200, blank=True)

    class Meta:
        ordering = ["date"]
        verbose_name = "Zi din calendarul de producție"


MONTH_STATUSES = [("draft", "Ciornă"), ("submitted", "Transmis"), ("approved", "Aprobat"), ("closed", "Închis")]


class Roster(models.Model):
    """Graficul de ture al subdiviziunii pe o lună: un rând pe raport de muncă, codul turei pe fiecare zi."""

    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, related_name="rosters", verbose_name="Subdiviziunea")
    year = models.PositiveSmallIntegerField("Anul")
    month = models.PositiveSmallIntegerField("Luna")
    status = models.CharField("Starea", max_length=10, choices=MONTH_STATUSES[:3], default="draft", db_index=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-year", "-month", "subdivision__sort", "subdivision__name_ro"]
        verbose_name = "Graficul de ture"
        constraints = [models.UniqueConstraint(fields=["subdivision", "year", "month"], name="uniq_roster")]

    def __str__(self):
        return f"Graficul {self.month:02d}.{self.year} — {self.subdivision.name_ro}"


class RosterLine(models.Model):
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name="lines")
    employment = models.ForeignKey(Employment, on_delete=models.CASCADE, related_name="roster_lines")
    days = models.JSONField("Turele pe zile {zi: cod}", default=dict, blank=True)
    note = models.CharField("Mențiuni", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        constraints = [models.UniqueConstraint(fields=["roster", "employment"], name="uniq_roster_line")]


class Timesheet(models.Model):
    """Tabela de pontaj lunară a secției: se completează din grafic și absențe, se corectează și se închide."""

    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, related_name="timesheets", verbose_name="Subdiviziunea")
    year = models.PositiveSmallIntegerField("Anul")
    month = models.PositiveSmallIntegerField("Luna")
    status = models.CharField("Starea", max_length=10, choices=[MONTH_STATUSES[i] for i in (0, 1, 3)], default="draft",
                              db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    closed_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-year", "-month", "subdivision__sort", "subdivision__name_ro"]
        verbose_name = "Tabela de pontaj"
        constraints = [models.UniqueConstraint(fields=["subdivision", "year", "month"], name="uniq_timesheet")]

    def __str__(self):
        return f"Tabela de pontaj {self.month:02d}.{self.year} — {self.subdivision.name_ro}"


class TimesheetLine(models.Model):
    """Un raport de muncă în tabelă. `days`: {zi: {"c": cod, "h": ore, "n": ore de noapte, "m": scris de mână}};
    `typed_hours` — orele pe tipuri de ore (`HourType`)."""

    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, related_name="lines")
    employment = models.ForeignKey(Employment, on_delete=models.CASCADE, related_name="timesheet_lines")
    days = models.JSONField(default=dict, blank=True)
    totals = models.JSONField(default=dict, blank=True)
    # orele pe tipuri (instruire, examinare, zbor…), scrise de mână sau din Excel — rămân la recompletarea tabelei:
    # {cod: {"days": {zi: ore}, "month": ore | null}}; „month” (totalul pe lună) înlocuiește zilele
    typed_hours = models.JSONField("Orele pe tipuri", default=dict, blank=True)
    note = models.CharField("Mențiuni", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        constraints = [models.UniqueConstraint(fields=["timesheet", "employment"], name="uniq_timesheet_line")]


# --- tipurile de ore și tarifele pe ele (S4b, cererea clientului §2.6 din PLAN-SRL.md) -----------------------------------
HOUR_GROUPS = [
    ("worked", "Ore lucrate"), ("training", "Instruire"), ("exam", "Examinare"), ("flight", "Zbor"), ("reserve", "Rezervă"),
    ("standby", "Staționare"), ("driving", "Conducere"), ("availability", "Disponibilitate"), ("other", "Alta"),
]
# cum se leagă orele tipului de timpul de muncă al liniei din pontaj (orele standard din grafic):
# - within: o parte din orele lucrate (zborul, instruirea, examinarea făcute în program) — nu se adaugă a doua oară;
# - added: timp de muncă peste orele standard — se adaugă la orele lucrate și la partea lucrată din normă;
# - none: nu e timp de muncă (rezerva acasă, disponibilitatea) — doar se plătește tariful, dacă există.
WORK_TIME = [("within", "În cadrul orelor lucrate (o parte din program)"), ("added", "Se adaugă la orele lucrate"),
             ("none", "Nu e timp de muncă")]
HOUR_ENTRY = [("day", "Pe zile sau total pe lună"), ("month", "Doar total pe lună")]
HOUR_PROFILES = [("general", "General"), ("factory", "Fabrică"), ("aviation", "Aviație"), ("transport", "Transport")]


class HourType(models.Model):
    """Tipul de ore al pontajului (instruire, examinare, zbor…): coloana din pontaj, variabila `Ore.COD` din formule și
    tariful pe oră din raportul de muncă (`JobHourRate`)."""

    code = models.CharField("Codul", max_length=16, unique=True)
    name_ro = models.CharField("Denumire (RO)", max_length=120)
    name_ru = models.CharField("Denumire (RU)", max_length=120, blank=True)
    name_en = models.CharField("Denumire (EN)", max_length=120, blank=True)
    group = models.CharField("Grupa", max_length=14, choices=HOUR_GROUPS, default="other")
    work_time = models.CharField("Legătura cu orele lucrate", max_length=8, choices=WORK_TIME, default="within")
    entry = models.CharField("Se introduc", max_length=6, choices=HOUR_ENTRY, default="day")
    profile = models.CharField("Profilul", max_length=10, choices=HOUR_PROFILES, default="general")
    in_all_timesheets = models.BooleanField("Coloană pentru toți angajații în pontaj", default=False)
    pay_type = models.ForeignKey("payroll.PayType", on_delete=models.SET_NULL, null=True, blank=True, related_name="hour_types",
                                 verbose_name="Se plătește cu tipul de calcul (gol — „Ore pe tipuri”)",
                                 limit_choices_to={"auto": "hour_types"})
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField("Livrat cu sistemul", default=False)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["sort", "code"]
        verbose_name = "Tip de ore"

    def __str__(self):
        return f"{self.code} — {self.name_ro}"


class JobHourRate(models.Model):
    """Tariful pe oră al unui tip de ore pe raportul de muncă (pe funcție), cu orele garantate pe lună și perioada lui.
    Se pune din ordin (tabelul „Tarife pe tipuri de ore”) sau de mână în fila „Raporturi de muncă”."""

    employment = models.ForeignKey(Employment, on_delete=models.CASCADE, related_name="hour_rates")
    hour_type = models.ForeignKey(HourType, on_delete=models.PROTECT, related_name="job_rates", verbose_name="Tipul de ore")
    rate = models.DecimalField("Tariful (lei pe oră)", max_digits=10, decimal_places=2)
    guaranteed_hours = models.DecimalField("Ore garantate pe lună", max_digits=6, decimal_places=2, null=True, blank=True)
    date_from = models.DateField("De la")
    date_to = models.DateField("Până la", null=True, blank=True)
    document = models.CharField("Temeiul (ordinul, contractul)", max_length=200, blank=True)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.PROTECT, null=True, blank=True, related_name="hour_rates",
                                   verbose_name="Din punctul ordinului")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["employment", "hour_type__sort", "date_from", "id"]
        verbose_name = "Tariful pe tipul de ore"

    def __str__(self):
        return f"{self.hour_type.code} {self.rate} lei/oră din {self.date_from:%d.%m.%Y}"

    def in_force(self, start, end) -> bool:
        return self.date_from <= end and (self.date_to is None or self.date_to >= start)


class OccupationHourRate(models.Model):
    """Tariful-tip pe oră al funcției: la angajare completează tabelul „Tarife pe tipuri de ore” din ordin."""

    occupation = models.ForeignKey("org.Occupation", on_delete=models.CASCADE, related_name="hour_rates")
    hour_type = models.ForeignKey(HourType, on_delete=models.PROTECT, related_name="occupation_rates", verbose_name="Tipul de ore")
    rate = models.DecimalField("Tariful (lei pe oră)", max_digits=10, decimal_places=2)
    guaranteed_hours = models.DecimalField("Ore garantate pe lună", max_digits=6, decimal_places=2, null=True, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "Tariful-tip al funcției pe tipul de ore"
