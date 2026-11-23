"""Tiparul raportului de producție (forma simplă, cu antetul întreprinderii): lucrările cu cantitățile, rebutul, tariful și
suma; la raportul pe brigadă — și membrii cu orele, coeficientul și partea lor."""
from django.utils import timezone

from apps.payroll.payment_printing import _d, _lang
from apps.payroll.printing import _money
from apps.printing.renderer import company_context
from apps.printing.views import print_document

from .services import fmt


def _n(value):
    return fmt(value) if value else ""


def report_context(request, doc, lang="ro") -> dict:
    lines = []
    for n, ln in enumerate(doc.lines.select_related("employment__employee", "employment__occupation", "operation").order_by("sort", "id"),
                           start=1):
        lines.append({"no": n, "name": ln.employment.employee.full_name() if ln.employment_id else "",
                      "tab_number": ln.employment.employee.tab_number if ln.employment_id else "",
                      "operation": f"{ln.operation.code} — {ln.operation.name_ro}", "unit": ln.operation.get_unit_display(),
                      "quantity": _n(ln.quantity), "defect_nofault": _n(ln.defect_nofault), "defect_partial": _n(ln.defect_partial),
                      "defect_partial_pct": _n(ln.defect_partial_pct), "defect_worker": _n(ln.defect_worker), "hours": _n(ln.hours),
                      "rate": fmt(ln.rate) if ln.rate is not None else "", "normed_hours": _n(ln.normed_hours), "amount": _money(ln.amount)})
    members = []
    for n, m in enumerate(doc.members.select_related("employment__employee", "employment__occupation").order_by("sort", "id"), start=1):
        members.append({"no": n, "name": m.employment.employee.full_name(), "tab_number": m.employment.employee.tab_number,
                        "occupation": m.employment.occupation.name_ro, "hours": _n(m.hours), "coefficient": fmt(m.coefficient),
                        "hourly": fmt(m.hourly) if m.hourly else "", "normed_hours": _n(m.normed_hours), "amount": _money(m.amount)})
    total = sum((ln.amount for ln in doc.lines.all()), 0)
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "lines": lines, "members": members,
            "doc": {"number": doc.number, "date": _d(doc.date), "status": doc.get_status_display(), "note": doc.note,
                    "approved": doc.status == "approved", "kind": doc.kind, "kind_label": doc.get_kind_display(),
                    "brigade": doc.brigade.name if doc.brigade_id else "", "subdivision": doc.subdivision.name_ro if doc.subdivision_id else "",
                    "distribution": doc.brigade.get_distribution_display() if doc.brigade_id else "", "total": _money(total)},
            "today": _d(timezone.localdate()), "placeholders": {"număr": doc.number, "data": _d(doc.date)}}


def print_report(request, doc):
    lang = _lang(request)
    return print_document(request, "production_report", report_context(request, doc, lang), template_id=request.query_params.get("template"),
                          title=f"Raportul de producție nr. {doc.number}", lang=lang)


def sample_report(request, lang, options):
    from .models import ProductionReport

    doc = ProductionReport.objects.filter(lines__isnull=False).first()
    if doc is None:
        raise ValueError("Nu există încă rapoarte de producție.")
    return report_context(request, doc, lang)
