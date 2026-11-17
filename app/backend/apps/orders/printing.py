"""Tiparul ordinului (întreg sau extras pentru un angajat) și al registrului ordinelor."""
from django.utils import timezone

from apps.org.models import ORDER_REGISTERS
from apps.printing.renderer import company_context
from apps.printing.views import print_document

from .models import Order


def _d(value):
    return value.strftime("%d.%m.%Y") if value else ""


def order_context(request, order: Order, lang="ro", item_id=None) -> dict:
    items = list(order.items.select_related("employee", "employment__occupation", "employment__subdivision").order_by("sort", "id"))
    extract = None
    if item_id:
        items = [i for i in items if str(i.id) == str(item_id)]
        extract = items[0] if items else None
    company = company_context(request, lang)
    return {
        "company": company, "lang": lang, "extract": bool(extract), "options": {},
        "order": {"number": order.number or "____", "date": _d(order.date), "title": order.title, "preamble": order.preamble,
                  "basis": order.basis, "footer": order.footer, "signer_name": order.signer_name,
                  "signer_position": order.signer_position, "approvals": order.approvals or [],
                  "status": order.status, "cancelled": order.status == "cancelled",
                  "cancelled_by": str(order.cancelled_by) if order.cancelled_by_id else ""},
        "points": [{"no": n, "text": i.text, "employee": i.employee.full_name() if i.employee_id else "",
                    "position": (i.employment.occupation.name_ro if i.employment_id else ""),
                    "acknowledged": _d(i.acknowledged_on)} for n, i in enumerate(items, start=1)],
        "acquaint": [{"name": i.employee.full_name(), "acknowledged": _d(i.acknowledged_on)} for i in items if i.employee_id],
        "today": _d(timezone.localdate()),
        "placeholders": {"număr": order.number, "data": _d(order.date)},
    }


def print_order(request, order: Order, item_id=None):
    lang = request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro"
    ctx = order_context(request, order, lang, item_id)
    title = f"{'Extras din ordinul' if item_id else 'Ordinul'} nr. {order.number or 'ciornă'}"
    return print_document(request, "order_extract" if item_id else "order", ctx, template_id=request.query_params.get("template"),
                          title=title, lang=lang)


def print_register(request, report):
    lang = request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro"
    rows = [{"number": o.number, "date": _d(o.date), "type": o.order_type.name_ro, "title": o.title,
             "employees": ", ".join(i.employee.short_name() for i in o.items.all() if i.employee_id),
             "status": o.get_status_display(), "signer": o.signer_name} for o in report["orders"]]
    ctx = {"company": company_context(request, lang), "lang": lang, "options": {}, "rows": rows, "gaps": report["gaps"],
           "register": dict(ORDER_REGISTERS).get(report["register"], report["register"]), "year": report["year"],
           "today": _d(timezone.localdate()), "placeholders": {"an": report["year"]}}
    return print_document(request, "orders_register", ctx, template_id=request.query_params.get("template"),
                          title=f"Registrul ordinelor {report['year']}", lang=lang)


def sample(request, lang, options):
    order = Order.objects.filter(status="signed").first() or Order.objects.first()
    if order is None:
        raise ValueError("Nu există încă ordine.")
    return order_context(request, order, lang)


def sample_extract(request, lang, options):
    order = Order.objects.filter(status="signed", items__isnull=False).first()
    if order is None:
        raise ValueError("Nu există încă ordine semnate.")
    return order_context(request, order, lang, order.items.first().id)


def sample_register(request, lang, options):
    from . import services

    year = timezone.localdate().year
    report = services.register_report("order_personnel", year)
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "rows": [
        {"number": o.number, "date": _d(o.date), "type": o.order_type.name_ro, "title": o.title, "employees": "",
         "status": o.get_status_display(), "signer": o.signer_name} for o in report["orders"]],
        "gaps": report["gaps"], "register": "Ordine privind personalul", "year": year, "today": _d(timezone.localdate())}
