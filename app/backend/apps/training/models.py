"""Formarea profesională continuă (EMC), planul anual de formare și atestarea (categoriile de calificare)."""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.org.models import DictItem, Specialty
from apps.staff.models import Employee

KINDS = [
    ("course", "Curs de perfecționare"),
    ("thematic", "Curs tematic / de specializare"),
    ("conference", "Conferință / congres"),
    ("seminar", "Seminar / atelier"),
    ("internship", "Stagiu"),
    ("online", "Curs online (e-learning)"),
    ("publication", "Publicație / prezentare"),
    ("other", "Altă activitate"),
]


class TrainingRecord(models.Model):
    """O activitate de formare a angajatului: cursul, organizatorul, orele și creditele EMC, certificatul."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="trainings")
    kind = models.CharField("Tipul", max_length=12, choices=KINDS, default="course")
    title = models.CharField("Denumirea cursului / activității", max_length=300)
    provider = models.CharField("Organizatorul (instituția)", max_length=250, blank=True)
    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Specialitatea")
    date_from = models.DateField("De la")
    date_to = models.DateField("Până la", null=True, blank=True)
    hours = models.DecimalField("Ore", max_digits=6, decimal_places=1, default=Decimal("0"))
    credits = models.DecimalField("Credite EMC", max_digits=6, decimal_places=1, default=Decimal("0"))
    certificate_number = models.CharField("Nr. certificatului", max_length=60, blank=True)
    certificate_date = models.DateField("Data certificatului", null=True, blank=True)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="trainings",
                                   verbose_name="Ordinul de trimitere")
    note = models.CharField("Observații", max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-date_from", "-id"]
        verbose_name = "Activitate de formare (EMC)"

    def __str__(self):
        return f"{self.employee} — {self.title}"


class TrainingPlan(models.Model):
    """Planul anual de formare al instituției (cerut de Regulamentul EMFC)."""

    STATUSES = [("draft", "Ciornă"), ("approved", "Aprobat")]

    year = models.PositiveSmallIntegerField("Anul", unique=True)
    number = models.CharField("Numărul", max_length=40, blank=True)
    date = models.DateField("Data", default=timezone.localdate)
    status = models.CharField(max_length=10, choices=STATUSES, default="draft")
    note = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True, blank=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-year"]
        verbose_name = "Planul anual de formare"

    def __str__(self):
        return f"Planul de formare {self.year}"


class TrainingPlanLine(models.Model):
    plan = models.ForeignKey(TrainingPlan, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="training_plan_lines")
    kind = models.CharField("Tipul", max_length=12, choices=KINDS, default="course")
    title = models.CharField("Cursul / tematica", max_length=300)
    provider = models.CharField("Organizatorul", max_length=250, blank=True)
    month = models.PositiveSmallIntegerField("Luna", null=True, blank=True)
    hours = models.DecimalField("Ore", max_digits=6, decimal_places=1, default=Decimal("0"))
    credits = models.DecimalField("Credite", max_digits=6, decimal_places=1, default=Decimal("0"))
    record = models.ForeignKey(TrainingRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="plan_lines",
                               verbose_name="Realizat prin")
    note = models.CharField("Observații", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]


class Attestation(models.Model):
    """Dosarul de atestare: cine, la ce categorie, când se prezintă la comisie și ce a decis comisia."""

    STATUSES = [("planned", "Planificat"), ("submitted", "Dosarul depus"), ("awarded", "Categorie conferită"),
                ("confirmed", "Categorie confirmată"), ("refused", "Respins"), ("postponed", "Amânat")]
    POSITIVE = ("awarded", "confirmed")

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attestations")
    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Specialitatea")
    current_category = models.ForeignKey(DictItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                                         limit_choices_to={"kind": "qualification"}, verbose_name="Categoria actuală")
    due_date = models.DateField("Categoria expiră la", null=True, blank=True)
    requested_category = models.ForeignKey(DictItem, on_delete=models.PROTECT, related_name="+", limit_choices_to={"kind": "qualification"},
                                           verbose_name="Categoria solicitată")
    session_date = models.DateField("Data comisiei", null=True, blank=True)
    submitted_on = models.DateField("Dosarul depus la", null=True, blank=True)
    status = models.CharField("Starea", max_length=10, choices=STATUSES, default="planned", db_index=True)
    result_category = models.ForeignKey(DictItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
                                        limit_choices_to={"kind": "qualification"}, verbose_name="Categoria obținută")
    result_date = models.DateField("Data deciziei comisiei", null=True, blank=True)
    decision = models.CharField("Nr. deciziei / procesului-verbal", max_length=80, blank=True)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="attestations",
                                   verbose_name="Ordinul de conferire")
    note = models.CharField("Observații", max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Atestare"
