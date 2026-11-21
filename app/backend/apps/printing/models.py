from django.db import models
from django.utils import timezone

DOC_TYPES = [
    ("order", "Ordin (un angajat)"),
    ("order_collective", "Ordin colectiv (mai mulți angajați)"),
    ("order_extract", "Extras din ordin"),
    ("staff_list", "State de personal"),
    ("employee_card", "Fișa personală (MR-2)"),
    ("certificate_work", "Adeverință de la locul de muncă"),
    ("certificate_seniority", "Adeverință de vechime"),
    ("certificate_salary", "Adeverință privind salariul (pentru bancă)"),
    ("contract", "Contract individual de muncă"),
    ("timesheet", "Tabel de pontaj"),
    ("roster", "Graficul de ture"),
    ("leave_schedule", "Graficul concediilor"),
    ("orders_register", "Registrul ordinelor"),
    ("employee_list", "Lista angajaților"),
    ("payslip", "Fișa de calcul (salariu)"),
    ("payroll_sheet", "Stat de calcul / de plată"),
    ("payment_sheet", "Stat de plată"),
    ("bank_list", "Lista pentru bancă"),
    ("annual_card", "Fișa personală anuală a veniturilor"),
    ("report", "Raport (din catalogul de rapoarte)"),
]


class PrintTemplate(models.Model):
    """Șablon de tipar (HTML + CSS, limbajul de șabloane Django), editabil de administrator."""

    doc_type = models.CharField(max_length=24, choices=DOC_TYPES, db_index=True)
    code = models.SlugField(max_length=40)
    name = models.CharField(max_length=120)
    body = models.TextField()
    css = models.TextField(blank=True)
    orientation = models.CharField(max_length=10, choices=[("portrait", "Portret"), ("landscape", "Peisaj")],
                                   default="portrait")
    # Opțiunile implicite propuse la tipărire (de ex. {"show_images": true}).
    default_options = models.JSONField(default=dict, blank=True)
    # Editorul simplu: textele cu nume ({"ro": {"slogan": "..."}, "ru": {...}}) și stilul ({"font_size", "show_logo"})
    texts = models.JSONField(default=dict, blank=True)
    style = models.JSONField(default=dict, blank=True)
    # Coloanele tabelului alese în editor: [{"field": "logistics.box_qty", "title_ro", "title_ru", "width", "align",
    # "factor", "decimals"}] — ce valoare din fișa produsului sau din rând trage fiecare coloană (vezi fields.py).
    columns = models.JSONField(default=list, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    # Șabloanele livrate cu sistemul păstrează originalul, ca să poată fi restaurate.
    is_system = models.BooleanField(default=False)
    original_body = models.TextField(blank=True)
    original_css = models.TextField(blank=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["doc_type", "-is_default", "name"]
        constraints = [models.UniqueConstraint(fields=["doc_type", "code"], name="uniq_template_code")]

    def __str__(self):
        return self.name
