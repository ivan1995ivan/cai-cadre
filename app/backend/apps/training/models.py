"""Formarea profesională a angajaților (Codul muncii, titlul „Formarea profesională”): registrul cursurilor și
instruirilor cu orele, certificatul și termenul lui de valabilitate, planul anual de formare."""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.org.models import Specialty
from apps.staff.models import Employee

KINDS = [
    ("course", "Curs de perfecționare"),
    ("thematic", "Curs de specializare / calificare"),
    ("internal", "Instruire internă"),
    ("conference", "Conferință"),
    ("seminar", "Seminar / atelier"),
    ("internship", "Stagiu"),
    ("online", "Curs online (e-learning)"),
    ("other", "Altă activitate"),
]


class TrainingRecord(models.Model):
    """O activitate de formare a angajatului: cursul, organizatorul, orele, certificatul și până când e valabil."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="trainings")
    kind = models.CharField("Tipul", max_length=12, choices=KINDS, default="course")
    title = models.CharField("Denumirea cursului / activității", max_length=300)
    provider = models.CharField("Organizatorul (instituția)", max_length=250, blank=True)
    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Specialitatea")
    date_from = models.DateField("De la")
    date_to = models.DateField("Până la", null=True, blank=True)
    hours = models.DecimalField("Ore", max_digits=6, decimal_places=1, default=Decimal("0"))
    certificate_number = models.CharField("Nr. certificatului", max_length=60, blank=True)
    certificate_date = models.DateField("Data certificatului", null=True, blank=True)
    valid_until = models.DateField("Certificatul e valabil până la", null=True, blank=True)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="trainings",
                                   verbose_name="Ordinul de trimitere")
    note = models.CharField("Observații", max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-date_from", "-id"]
        verbose_name = "Activitate de formare"

    def __str__(self):
        return f"{self.employee} — {self.title}"


class TrainingPlan(models.Model):
    """Planul anual de formare profesională al întreprinderii."""

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
    record = models.ForeignKey(TrainingRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="plan_lines",
                               verbose_name="Realizat prin")
    note = models.CharField("Observații", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
