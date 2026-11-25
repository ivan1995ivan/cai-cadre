"""Concediile (Etapa 4): absențele din ordine, dreptul și soldul, graficul anual, cererile și foile de boală.

Absențele (`Absence`) le fac ordinele la semnare și foile de boală; soldul se calculează din ele (apps.leave.balance),
cu drepturile personale (`LeaveRight`) și corectările (`LeaveAdjustment`) puse de cadre.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.org.models import Subdivision
from apps.staff.models import Employee, Employment

ABSENCE_KINDS = [
    ("annual", "Concediu de odihnă anual"),
    ("extra", "Concediu suplimentar plătit"),
    ("unpaid", "Concediu neplătit"),
    ("maternity", "Concediu de maternitate"),
    ("paternity", "Concediu paternal"),
    ("childcare", "Concediu parțial plătit pentru îngrijirea copilului"),
    ("childcare_unpaid", "Concediu neplătit pentru îngrijirea copilului"),
    ("study", "Concediu de studii"),
    ("days_off", "Zile libere plătite"),
    ("travel", "Deplasare în interes de serviciu"),
    ("training", "Formare profesională"),
    ("sick", "Concediu medical"),
    # S5b: timpul fără producție, din ordin (CM art. 80, 80¹) — se plătesc după cauză (apps.payroll.engine)
    ("idle", "Staționare"),
    ("tech_unemployment", "Șomaj tehnic"),
]
# staționarea: cauza (CM art. 80¹) — din vina angajatorului se plătește integral, fără vina nimănui — cel puțin 2/3 din salariul
# de bază pe oră (nu sub salariul minim pe oră), din vina salariatului — nu se plătește
IDLE_CAUSES = [("employer", "Din vina angajatorului"), ("nobody", "Fără vina angajatorului și a salariatului"),
               ("worker", "Din vina salariatului")]
IDLE_KINDS = ("idle", "tech_unemployment")

# tipul de ordin → tipul absenței
ORDER_ABSENCE = {
    "leave_annual": "annual", "leave_extra": "extra", "leave_unpaid": "unpaid", "leave_maternity": "maternity",
    "leave_paternity": "paternity", "leave_childcare": "childcare", "leave_childcare_unpaid": "childcare_unpaid",
    "leave_study": "study", "days_off_paid": "days_off", "travel": "travel", "training": "training",
    "idle": "idle", "tech_unemployment": "tech_unemployment",
}
# tipul absenței → tipul de ordin (cererile de concediu se transformă în ordine)
ABSENCE_ORDER = {kind: code for code, kind in ORDER_ABSENCE.items()}
# concediile pentru îngrijirea copilului suspendă contractul (postul devine temporar vacant)
SUSPENDING = {"childcare", "childcare_unpaid"}
# concediile socotite în zile calendaristice fără sărbători; celelalte — zile calendaristice simple
WITHOUT_HOLIDAYS = {"annual", "extra", "unpaid", "study", "days_off"}
# ce se poate cere printr-o cerere de concediu (deplasările, perfecționarea și boala nu se cer)
REQUEST_KINDS = [k for k in ABSENCE_KINDS if k[0] in ABSENCE_ORDER and k[0] not in ("travel", "training", *IDLE_KINDS)]


class Absence(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="absences")
    employment = models.ForeignKey(Employment, on_delete=models.SET_NULL, null=True, blank=True, related_name="absences")
    kind = models.CharField("Tipul", max_length=18, choices=ABSENCE_KINDS)
    date_from = models.DateField("De la")
    date_to = models.DateField("Până la")
    days = models.PositiveSmallIntegerField("Zile", default=0)
    work_year_from = models.DateField("Anul de muncă de la", null=True, blank=True)
    work_year_to = models.DateField("Anul de muncă până la", null=True, blank=True)
    destination = models.CharField("Destinația / locul", max_length=200, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    # staționarea / șomajul tehnic: cauza și procentul plății scrise în ordin (gol — cel din Constantele salarizării)
    cause = models.CharField("Cauza (staționarea)", max_length=10, choices=IDLE_CAUSES, blank=True, default="", db_default="")
    pay_pct = models.DecimalField("Plata (% din salariul de bază)", max_digits=6, decimal_places=2, null=True, blank=True)
    recalled_on = models.DateField("Rechemat la", null=True, blank=True)
    days_returned = models.PositiveSmallIntegerField("Zile neutilizate (rechemare)", default=0)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="absences")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date_from", "id"]
        verbose_name = "Absență"

    def __str__(self):
        return f"{self.get_kind_display()} {self.date_from:%d.%m.%Y}–{self.date_to:%d.%m.%Y}"


class LeaveRight(models.Model):
    """Zile de concediu suplimentar ale angajatului, pe fiecare an de muncă (peste cele din funcție și subdiviziune)."""

    REASONS = [
        ("children", "Copii (mamă / tată cu copii mici sau cu dizabilități)"),
        ("disability", "Dizabilitatea angajatului"),
        ("collective", "Contractul colectiv de muncă"),
        ("seniority", "Vechimea în muncă"),
        ("conditions", "Condiții de muncă (individual)"),
        ("other", "Alt temei"),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_rights")
    reason = models.CharField("Temeiul", max_length=12, choices=REASONS, default="other")
    days = models.PositiveSmallIntegerField("Zile pe an")
    date_from = models.DateField("Valabil de la", null=True, blank=True)
    date_to = models.DateField("Valabil până la", null=True, blank=True)
    note = models.CharField("Observații (actul, copilul)", max_length=300, blank=True)

    class Meta:
        ordering = ["date_from", "id"]
        verbose_name = "Drept la concediu suplimentar"


class LeaveAdjustment(models.Model):
    """Corectarea soldului: soldul inițial la pornirea evidenței, compensarea în bani, corectări."""

    KINDS = [
        ("opening", "Sold inițial (la pornirea evidenței)"),
        ("compensated", "Compensat în bani"),
        ("correction", "Corectare"),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_adjustments")
    kind = models.CharField("Tipul", max_length=12, choices=KINDS, default="correction")
    date = models.DateField("Data", default=timezone.localdate)
    work_year_from = models.DateField("Anul de muncă (începutul)", null=True, blank=True)
    days = models.DecimalField("Zile (+ adaugă, − scade)", max_digits=6, decimal_places=2)
    note = models.CharField("Observații", max_length=300, blank=True)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="leave_adjustments")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["date", "id"]
        verbose_name = "Corectarea soldului de concediu"


class LeaveSchedule(models.Model):
    """Graficul anual al concediilor de odihnă pe subdiviziune: planificat de șeful subdiviziunii, aprobat prin ordin."""

    STATUSES = [("draft", "Ciornă"), ("submitted", "Transmis la resurse umane"), ("approved", "Aprobat")]
    year = models.PositiveSmallIntegerField("Anul")
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, related_name="leave_schedules",
                                    verbose_name="Subdiviziunea")
    status = models.CharField("Starea", max_length=10, choices=STATUSES, default="draft", db_index=True)
    approved_by = models.CharField("Aprobat prin", max_length=200, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField("Observații", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-year", "subdivision__sort", "subdivision__name_ro"]
        verbose_name = "Graficul concediilor"
        constraints = [models.UniqueConstraint(fields=["year", "subdivision"], name="uniq_leave_schedule")]

    def __str__(self):
        return f"Graficul concediilor {self.year} — {self.subdivision.name_ro}"


class LeaveScheduleLine(models.Model):
    schedule = models.ForeignKey(LeaveSchedule, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_plan")
    date_from = models.DateField("Data planificată", null=True, blank=True)
    days = models.PositiveSmallIntegerField("Zile", default=0)
    date_to = models.DateField("Până la (calculat)", null=True, blank=True)
    moved_to = models.DateField("Amânat la", null=True, blank=True)
    note = models.CharField("Mențiuni", max_length=300, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]


class LeaveRequest(models.Model):
    """Cererea de concediu: depusă de angajat (sau scrisă de cadre), aprobată de șef, apoi ordinul."""

    STATUSES = [("new", "Depusă"), ("approved", "Aprobată de șef"), ("rejected", "Respinsă"), ("ordered", "Ordin emis"),
                ("withdrawn", "Retrasă")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    kind = models.CharField("Tipul concediului", max_length=18, choices=REQUEST_KINDS, default="annual")
    date_from = models.DateField("De la")
    days = models.PositiveSmallIntegerField("Zile", default=0)
    date_to = models.DateField("Până la")
    work_year_from = models.DateField("Anul de muncă de la", null=True, blank=True)
    work_year_to = models.DateField("Anul de muncă până la", null=True, blank=True)
    reason = models.CharField("Motivul / mențiuni", max_length=300, blank=True)
    status = models.CharField("Starea", max_length=10, choices=STATUSES, default="new", db_index=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField("Mențiunea șefului", max_length=300, blank=True)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="leave_requests")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Cerere de concediu"


def _sick_upload(instance, filename):
    # partea privată (date despre sănătate): scanarea se dă doar prin API
    return f"private/sick/{instance.employee_id or 'new'}/{timezone.now():%Y%m%d%H%M%S}-{filename}"


class SickLeave(models.Model):
    """Certificatul de concediu medical (foaia de boală): se înregistrează și devine absență în dosar și în pontaj."""

    KINDS = [
        ("illness", "Boală obișnuită"),
        ("household_injury", "Traumatism în afara serviciului"),
        ("work_accident", "Accident de muncă / boală profesională"),
        ("pregnancy", "Sarcină și lăuzie"),
        ("child_care", "Îngrijirea copilului bolnav"),
        ("family_care", "Îngrijirea unui membru de familie bolnav"),
        ("quarantine", "Carantină"),
        ("prosthesis", "Protezare în staționar"),
        ("other", "Altă cauză"),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="sick_leaves")
    series = models.CharField("Seria", max_length=10, blank=True)
    number = models.CharField("Numărul", max_length=30)
    issued_on = models.DateField("Data eliberării", null=True, blank=True)
    issued_by = models.CharField("Instituția medicală", max_length=200, blank=True)
    kind = models.CharField("Cauza incapacității", max_length=18, choices=KINDS, default="illness")
    date_from = models.DateField("Scutit de la")
    date_to = models.DateField("Până la")
    days = models.PositiveSmallIntegerField("Zile calendaristice", default=0)
    continuation_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="continuations",
                                        verbose_name="Continuarea certificatului")
    return_date = models.DateField("Se prezintă la lucru", null=True, blank=True)
    file = models.FileField("Scanarea", upload_to=_sick_upload, blank=True)
    note = models.CharField("Observații", max_length=300, blank=True)
    absence = models.OneToOneField(Absence, on_delete=models.SET_NULL, null=True, blank=True, related_name="sick_leave")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-date_from", "-id"]
        verbose_name = "Certificat de concediu medical"
        constraints = [models.UniqueConstraint(fields=["series", "number"], name="uniq_sick_leave_number")]

    def __str__(self):
        return f"Certificatul {self.series} {self.number}".replace("  ", " ")
