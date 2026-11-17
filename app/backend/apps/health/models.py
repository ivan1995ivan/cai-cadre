"""Sănătatea în muncă: examenele medicale, vaccinările și instructajul de securitate și sănătate în muncă (SSM)."""
from django.db import models
from django.utils import timezone

from apps.org.models import DictItem
from apps.staff.models import Employee


class MedicalExam(models.Model):
    KINDS = [("preliminary", "La angajare"), ("periodic", "Periodic"), ("extraordinary", "Suplimentar"),
             ("return", "La reluarea activității")]
    CONCLUSIONS = [("fit", "Apt"), ("restricted", "Apt condiționat (cu restricții)"), ("temporary", "Inapt temporar"),
                   ("unfit", "Inapt")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="medical_exams")
    kind = models.CharField("Tipul", max_length=14, choices=KINDS, default="periodic")
    date = models.DateField("Data examenului")
    institution = models.CharField("Instituția medicală", max_length=200, blank=True)
    conclusion = models.CharField("Concluzia", max_length=12, choices=CONCLUSIONS, default="fit")
    restrictions = models.CharField("Restricțiile / recomandările", max_length=300, blank=True)
    next_date = models.DateField("Următorul examen", null=True, blank=True)
    document = models.CharField("Fișa / certificatul (nr.)", max_length=60, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "Examen medical"


class Vaccination(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="vaccinations")
    vaccine = models.ForeignKey(DictItem, on_delete=models.PROTECT, related_name="+", limit_choices_to={"kind": "vaccine"},
                                verbose_name="Vaccinul")
    dose = models.PositiveSmallIntegerField("Doza (nr.)", default=1)
    date = models.DateField("Data")
    series = models.CharField("Seria / lotul", max_length=60, blank=True)
    next_date = models.DateField("Următoarea doză / revaccinarea", null=True, blank=True)
    refused = models.BooleanField("Refuz (în scris)", default=False)
    note = models.CharField("Observații", max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "Vaccinare"


class SafetyBriefing(models.Model):
    KINDS = [("introductory", "Introductiv general"), ("initial", "Primar la locul de muncă"), ("periodic", "Periodic"),
             ("unplanned", "Neplanificat"), ("targeted", "Special (lucrări cu risc)")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="safety_briefings")
    kind = models.CharField("Tipul instructajului", max_length=14, choices=KINDS, default="periodic")
    date = models.DateField("Data")
    instructor = models.CharField("A instruit (numele, funcția)", max_length=200, blank=True)
    topic = models.CharField("Tematica", max_length=300, blank=True)
    next_date = models.DateField("Următorul instructaj", null=True, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "Instructaj SSM"
