"""Ordinele (Etapa 3): ordinul cu punctele lui; la semnare fiecare punct își aplică efectul în dosarul angajatului."""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.org.models import ORDER_REGISTERS, DictItem, LegalBasis, OrderType
from apps.staff.models import Employee, Employment


class Order(models.Model):
    STATUSES = [("draft", "Ciornă"), ("signed", "Semnat"), ("cancelled", "Anulat")]

    order_type = models.ForeignKey(OrderType, on_delete=models.PROTECT, verbose_name="Tipul ordinului")
    register = models.CharField("Registrul", max_length=20, choices=ORDER_REGISTERS)
    year = models.PositiveSmallIntegerField("Anul")
    seq = models.PositiveIntegerField("Numărul de ordine în registru", null=True, blank=True)
    number = models.CharField("Numărul", max_length=30, blank=True, db_index=True)
    date = models.DateField("Data", default=timezone.localdate)
    title = models.CharField("Titlul („Cu privire la …”)", max_length=300)
    preamble = models.TextField("Preambulul (în temeiul …)", blank=True)
    basis = models.TextField("Temei (cererea, demersul, certificatul)", blank=True)
    legal_bases = models.ManyToManyField(LegalBasis, blank=True, related_name="orders", verbose_name="Temeiurile legale")
    footer = models.TextField("Puncte finale (controlul executării etc.)", blank=True)
    signer_name = models.CharField("Semnează (numele)", max_length=150, blank=True)
    signer_position = models.CharField("Semnează (funcția)", max_length=150, blank=True, default="Director")
    approvals = models.JSONField("Vizele (coordonat cu)", default=list, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="draft", db_index=True)
    cancelled_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="cancels",
                                     verbose_name="Anulat prin ordinul")
    notes = models.TextField("Observații interne", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    signed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    signed_at = models.DateTimeField(null=True, blank=True)
    deletion_mark = models.BooleanField("Marcat pentru ștergere", default=False)

    class Meta:
        ordering = ["-date", "-seq", "-id"]
        verbose_name = "Ordin"
        constraints = [models.UniqueConstraint(fields=["register", "year", "seq"], name="uniq_order_number")]

    def __str__(self):
        num = self.number or "(fără număr)"
        return f"Ordinul nr. {num} din {self.date:%d.%m.%Y}"

    def reference(self) -> str:
        """„125-p din 12.03.2026” — cum se scrie ordinul în istoricul dosarului."""
        return f"{self.number} din {self.date:%d.%m.%Y}" if self.number else ""


class OrderItem(models.Model):
    """Un punct al ordinului: un angajat (sau, la ordinele organizatorice, fără angajat) și parametrii efectului."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, null=True, blank=True, related_name="order_items")
    employment = models.ForeignKey(Employment, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items")
    params = models.JSONField("Parametrii", default=dict, blank=True)
    text = models.TextField("Textul punctului", blank=True)
    text_edited = models.BooleanField("Text scris manual", default=False)
    sort = models.IntegerField(default=0)
    acknowledged_on = models.DateField("Adus la cunoștință", null=True, blank=True)
    result = models.JSONField("Ce s-a schimbat la semnare (pentru anulare)", default=dict, blank=True)

    class Meta:
        ordering = ["sort", "id"]


class Sanction(models.Model):
    """Sancțiunea disciplinară (Codul muncii, art. 206); se stinge după un an dacă nu se ridică mai devreme."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="sanctions")
    kind = models.ForeignKey(DictItem, on_delete=models.PROTECT, limit_choices_to={"kind": "sanction"}, related_name="+",
                             verbose_name="Sancțiunea")
    date = models.DateField("Aplicată la")
    misconduct = models.TextField("Abaterea disciplinară", blank=True)
    valid_until = models.DateField("Se stinge la")
    lifted_on = models.DateField("Ridicată înainte de termen la", null=True, blank=True)
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="sanctions")

    class Meta:
        ordering = ["-date"]


class Incentive(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="incentives")
    kind = models.ForeignKey(DictItem, on_delete=models.PROTECT, limit_choices_to={"kind": "incentive"}, related_name="+",
                             null=True, blank=True, verbose_name="Tipul stimulării")
    date = models.DateField("Data")
    amount = models.DecimalField("Suma (lei)", max_digits=12, decimal_places=2, null=True, blank=True)
    percent = models.DecimalField("Procent din salariu", max_digits=6, decimal_places=2, null=True, blank=True)
    note = models.CharField("Pentru ce", max_length=300, blank=True)
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="incentives")

    class Meta:
        ordering = ["-date"]
