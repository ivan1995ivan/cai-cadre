"""Cererile angajatului din cabinet care nu sunt concedii: adeverințe, modificarea datelor personale, altele."""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.staff.models import Employee


class EmployeeRequest(models.Model):
    KINDS = [("certificate_work", "Adeverință de la locul de muncă"), ("certificate_seniority", "Adeverință privind vechimea"),
             ("certificate_salary", "Adeverință despre salariu"), ("data_change", "Modificarea datelor personale"),
             ("other", "Altă cerere")]
    STATUSES = [("new", "Depusă"), ("in_work", "În lucru"), ("done", "Gata"), ("rejected", "Respinsă"), ("withdrawn", "Retrasă")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="portal_requests")
    kind = models.CharField("Tipul", max_length=24, choices=KINDS)
    text = models.TextField("Conținutul (pentru ce instituție, ce date se schimbă)", blank=True)
    copies = models.PositiveSmallIntegerField("Exemplare", default=1)
    status = models.CharField("Starea", max_length=10, choices=STATUSES, default="new", db_index=True)
    answer = models.CharField("Răspunsul cadrelor", max_length=300, blank=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    handled_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Cererea angajatului"
