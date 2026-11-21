"""Tiparul documentului „Modificarea acumulărilor planificate” (forma simplă, cu antetul întreprinderii)."""
from django.utils import timezone

from apps.printing.renderer import company_context
from apps.printing.views import print_document

from .payment_printing import _d, _lang
from .printing import _money


def _num(value):
    if value is None:
        return ""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def change_context(request, doc, lang="ro") -> dict:
    rows = []
    for n, ln in enumerate(doc.lines.select_related("employee", "employment__occupation", "pay_type").order_by("sort", "id"), start=1):
        rows.append({"no": n, "name": ln.employee.full_name(), "tab_number": ln.employee.tab_number,
                     "employment": f"{ln.employment.get_kind_display()}, {ln.employment.occupation.name_ro}" if ln.employment_id else "",
                     "type": f"{ln.pay_type.code} — {ln.pay_type.name_ro}", "action": ln.get_action_display(),
                     "amount": _money(ln.amount) if ln.amount is not None else "", "percent": _num(ln.percent),
                     "quantity": _num(ln.quantity), "date_from": _d(ln.date_from or doc.date), "date_to": _d(ln.date_to),
                     "document": ln.document})
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "rows": rows,
            "doc": {"number": doc.number, "date": _d(doc.date), "status": doc.get_status_display(), "note": doc.note,
                    "approved": doc.status == "approved"},
            "today": _d(timezone.localdate()), "placeholders": {"număr": doc.number, "data": _d(doc.date)}}


def print_change(request, doc):
    lang = _lang(request)
    return print_document(request, "pay_item_change", change_context(request, doc, lang), template_id=request.query_params.get("template"),
                          title=f"Modificarea acumulărilor planificate nr. {doc.number}", lang=lang)


def sample_change(request, lang, options):
    from .models import PayItemChange

    doc = PayItemChange.objects.filter(lines__isnull=False).first()
    if doc is None:
        raise ValueError("Nu există încă documente „Modificarea acumulărilor planificate”.")
    return change_context(request, doc, lang)
