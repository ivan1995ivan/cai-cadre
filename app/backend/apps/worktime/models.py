"""Timpul de muncă (Etapa 4, partea 2): turele, graficele de lucru, graficul lunar pe secție (gărzi) și tabela de pontaj.

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
    """Codul turei din grafic și din pontaj: „8” (zi de 8 ore), „Z12” (zi 08–20), „N12” (noapte 20–08), „G24” (gardă)."""

    code = models.CharField("Codul", max_length=8, unique=True)
    name = models.CharField("Denumirea", max_length=120)
    hours = models.DecimalField("Ore", max_digits=4, decimal_places=1)
    night_hours = models.DecimalField("Din ele noaptea (22–06)", max_digits=4, decimal_places=1, default=Decimal("0"))
    start = models.TimeField("Începe la", null=True, blank=True)
    is_duty = models.BooleanField("Gardă", default=False)
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
    """Graficul lunar al secției (turele și gărzile): un rând pe raport de muncă, codul turei pe fiecare zi."""

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
        verbose_name = "Graficul lunar (gărzi)"
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
    """Un raport de muncă în tabelă. `days`: {zi: {"c": cod, "h": ore, "n": ore de noapte, "m": scris de mână}}."""

    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, related_name="lines")
    employment = models.ForeignKey(Employment, on_delete=models.CASCADE, related_name="timesheet_lines")
    days = models.JSONField(default=dict, blank=True)
    totals = models.JSONField(default=dict, blank=True)
    note = models.CharField("Mențiuni", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        constraints = [models.UniqueConstraint(fields=["timesheet", "employment"], name="uniq_timesheet_line")]
