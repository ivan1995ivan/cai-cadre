"""Sănătatea și securitatea în muncă: examenele medicale ale lucrătorilor (HG 1025/2016 — la angajare, periodic, …) cu
periodicitatea pe funcție / subdiviziune și instructajul de securitate și sănătate în muncă (Legea 186/2008, HG 95/2009)."""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.org.models import Occupation, Subdivision
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


class ExamRule(models.Model):
    """Periodicitatea examenului medical periodic pentru o funcție și / sau o subdiviziune (din evaluarea riscurilor și
    lista factorilor de risc, HG 1025/2016). Cea mai precisă regulă câștigă: funcția și subdiviziunea > funcția >
    subdiviziunea (cea mai apropiată în arbore); fără regulă — periodicitatea implicită din setări."""

    occupation = models.ForeignKey(Occupation, on_delete=models.CASCADE, null=True, blank=True, related_name="+",
                                   verbose_name="Funcția")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE, null=True, blank=True, related_name="+",
                                    verbose_name="Subdiviziunea (cu subordonatele)")
    months = models.PositiveSmallIntegerField("Periodicitatea (luni; 0 = fără examen periodic)")
    note = models.CharField("Factorii de risc / temeiul", max_length=300, blank=True)

    class Meta:
        ordering = ["occupation__name_ro", "subdivision__name_ro", "id"]
        verbose_name = "Periodicitatea examenului medical"

    def clean(self):
        if not self.occupation_id and not self.subdivision_id:
            raise ValidationError("Alegeți funcția, subdiviziunea sau amândouă.")


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
