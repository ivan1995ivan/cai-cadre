"""Ordinele: crearea, numerotarea pe registre, textele, semnarea cu efecte și anularea prin alt ordin."""
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.deletion import ensure_not_marked
from apps.core.models import Company, SystemSetting
from apps.staff import services as staff_services

from . import effects, texts
from .models import Order, OrderItem

# Sufixele numerelor pe registre (ca în practica obișnuită: 125-p, 38-c); se pot schimba în setări („order_suffixes”)
DEFAULT_SUFFIXES = {"order_personnel": "-p", "order_leave": "-c", "order_travel": "-d", "order_general": ""}


# alte module (cabinetul angajatului) se abonează: funcția primește ordinul semnat, după salvarea în baza de date
AFTER_SIGN: list = []


def suffixes() -> dict:
    return {**DEFAULT_SUFFIXES, **(SystemSetting.read("order_suffixes", {}) or {})}


def next_seq(register: str, year: int) -> int:
    top = Order.objects.filter(register=register, year=year).aggregate(m=Max("seq"))["m"]
    return (top or 0) + 1


def format_number(seq: int, register: str) -> str:
    return f"{seq}{suffixes().get(register, '')}"


def new_order(order_type, *, user=None, date=None) -> Order:
    """Ordin nou (ciornă) cu valorile tipului: registrul, titlul, temeiurile legale, preambulul, semnatarul (numele și
    funcția conducătorului din Constante, în română — limba ordinelor)."""
    from apps.org.models import LegalBasis

    date = date or timezone.localdate()
    company = Company.get()
    bases = list(order_type.legal_bases.all())
    order = Order.objects.create(
        order_type=order_type, register=order_type.register, year=date.year, date=date,
        title=order_type.title_ro or order_type.name_ro, preamble=LegalBasis.preamble(bases),
        signer_name=company.director, signer_position=company.position("director"), created_by=user)
    order.legal_bases.set(bases)
    return order


def refresh_text(item: OrderItem, force=False):
    """Textul punctului din model (dacă utilizatorul nu l-a scris de mână)."""
    if item.text_edited and not force:
        return item.text
    item.text = texts.point_text(item)
    return item.text


def check_editable(order: Order):
    ensure_not_marked(order)
    if order.status != "draft":
        raise ValidationError({"detail": "Ordinul semnat nu se mai modifică. Pentru schimbări se emite un ordin de anulare / modificare."})


@transaction.atomic
def sign(order: Order, user=None) -> Order:
    """Semnarea: numărul în registru, apoi efectele fiecărui punct; o eroare anulează tot (nimic pe jumătate)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    check_editable(order)
    items = list(order.items.select_related("employee", "employment").order_by("sort", "id"))
    effect = order.order_type.effect
    code = order.order_type.code
    if not items and code != "cancel_order":
        raise ValidationError({"detail": "Ordinul nu are niciun punct."})
    if effect not in effects.NO_EMPLOYEE and code != "cancel_order":
        missing = [i for i in items if not i.employee_id]
        if missing:
            raise ValidationError({"detail": "Fiecare punct al ordinului trebuie să aibă angajatul."})
    if not order.order_type.collective and len(items) > 1:
        raise ValidationError({"detail": "Acest tip de ordin este pentru un singur angajat."})
    order.year = order.date.year
    if not order.seq:
        order.seq = next_seq(order.register, order.year)
    elif Order.objects.filter(register=order.register, year=order.year, seq=order.seq).exclude(pk=order.pk).exists():
        raise ValidationError({"number": f"Numărul {format_number(order.seq, order.register)} este deja folosit în registru."})
    order.number = format_number(order.seq, order.register)
    order.save(update_fields=["year", "seq", "number"])
    if code == "cancel_order":
        _cancel_targets(order, items, user)
    else:
        apply, _undo = effects.for_type(order.order_type)
        for item in items:
            item.result = apply(item, order, user) or {}
            refresh_text(item)
            item.save(update_fields=["result", "employment", "params", "text"])
    order.status, order.signed_at, order.signed_by = "signed", timezone.now(), user
    order.save(update_fields=["status", "signed_at", "signed_by"])
    for hook in AFTER_SIGN:
        transaction.on_commit(lambda hook=hook: hook(order))
    return order


def _cancel_targets(order, items, user):
    targets = [Order.objects.filter(pk=(i.params or {}).get("order")).first() for i in items]
    targets = [t for t in targets if t is not None]
    if not targets:
        raise ValidationError({"detail": "Alegeți ordinul care se anulează."})
    for target in targets:
        undo_order(target, cancelled_by=order)


@transaction.atomic
def undo_order(target: Order, cancelled_by: Order):
    if target.status != "signed":
        raise ValidationError({"detail": f"{target} nu este semnat (sau e deja anulat)."})
    if target.order_type.code == "cancel_order":
        raise ValidationError({"detail": "Un ordin de anulare nu se anulează; emiteți ordinul din nou."})
    _apply, undo = effects.for_type(target.order_type)
    for item in target.items.select_related("employee").order_by("-sort", "-id"):
        if undo:
            undo(item, item.result or {})
        item.result = {**(item.result or {}), "undone": True}
        item.save(update_fields=["result"])
    target.status, target.cancelled_by = "cancelled", cancelled_by
    target.save(update_fields=["status", "cancelled_by"])


def visible_orders(qs, user):
    """Șeful subdiviziunii vede ordinele cu angajații subdiviziunilor lui; ceilalți — după rol (toate)."""
    ids = staff_services.visible_subdivision_ids(user, "orders")
    if ids is None:
        return qs
    return qs.filter(items__employee__employments__subdivision_id__in=ids).distinct()


def register_report(register: str, year: int) -> dict:
    """Registrul ordinelor pe an: ordinele semnate în ordinea numerelor și numerele lipsă (găurile)."""
    rows = list(Order.objects.filter(register=register, year=year, seq__isnull=False).select_related("order_type")
                .prefetch_related("items__employee").order_by("seq"))
    seqs = [o.seq for o in rows]
    gaps = sorted(set(range(1, (max(seqs) if seqs else 0) + 1)) - set(seqs))
    return {"register": register, "year": year, "orders": rows, "gaps": [format_number(g, register) for g in gaps]}
