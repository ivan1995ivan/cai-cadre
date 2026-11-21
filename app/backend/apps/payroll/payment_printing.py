"""Tiparul îndreptării spre plată (statul de plată), al listei pentru bancă și al fișei personale anuale (anexa 8)."""
from django.utils import timezone

from apps.printing.renderer import company_context
from apps.printing.views import print_document

from . import reports
from .models import Payment
from .payments import MONTHS
from .printing import _money


def _d(value):
    return value.strftime("%d.%m.%Y") if value else ""


def _lang(request):
    return request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro"


SUMS = ("gross", "exemption", "cnam", "income_tax", "deductions")


def payment_context(request, payment: Payment, lang="ro", only_card=False) -> dict:
    lines = payment.lines.select_related("employee").order_by("sort", "id")
    if only_card:
        lines = lines.filter(method="card")
    rows = [{"no": n, "name": ln.employee.full_name(), "tab_number": ln.employee.tab_number, "idnp": ln.employee.idnp,
             "iban": ln.iban, "method": ln.get_method_display(), "cash": ln.method == "cash", "amount": _money(ln.amount),
             **{f: _money(getattr(ln, f)) for f in SUMS}, "note": ln.note} for n, ln in enumerate(lines, start=1)]
    total = sum((ln.amount for ln in lines), 0)
    sums = {f: _money(sum((getattr(ln, f) for ln in lines), 0)) for f in SUMS}
    base = payment.payroll
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "rows": rows,
            "doc": {"number": payment.number, "date": _d(payment.date), "month": MONTHS[payment.month], "year": payment.year,
                    "kind": payment.get_kind_display(), "method": payment.get_method_display(), "total": _money(total),
                    "count": len(rows), "reference": payment.reference, "paid_on": _d(payment.paid_on), **sums,
                    "base": f"{base.number} din {_d(base.date)}" if base else ""},
            "today": _d(timezone.localdate()), "placeholders": {"luna": MONTHS[payment.month], "an": payment.year}}


def print_payment(request, payment: Payment):
    lang = _lang(request)
    return print_document(request, "payment_sheet", payment_context(request, payment, lang), template_id=request.query_params.get("template"),
                          title=f"Îndreptarea spre plată nr. {payment.number}", lang=lang)


def print_bank_list(request, payment: Payment):
    lang = _lang(request)
    return print_document(request, "bank_list", payment_context(request, payment, lang, only_card=True),
                          template_id=request.query_params.get("template"), title=f"Lista pentru bancă nr. {payment.number}", lang=lang)


def annual_context(request, employee, year: int, lang="ro") -> dict:
    data = reports.annual_card(employee, year)
    money = lambda v: _money(v)  # noqa: E731
    rows = [{**r, **{k: money(r[k]) for k in ("gross", "exemption", "cnam", "taxable", "tax", "tax_calc", "cum_gross", "cum_cnam",
                                               "cum_taxable", "cum_tax")}}
            for r in data["rows"]]
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "card": {**data, "rows": rows,
            "total": {k: money(v) for k, v in data["total"].items()}}, "today": _d(timezone.localdate()),
            "placeholders": {"an": year}}


def print_annual_card(request, employee, year: int):
    lang = _lang(request)
    return print_document(request, "annual_card", annual_context(request, employee, year, lang), template_id=request.query_params.get("template"),
                          title=f"Fișa personală {year} — {employee.full_name()}", lang=lang)


def sample_payment(request, lang, options):
    p = Payment.objects.filter(lines__isnull=False).first()
    if p is None:
        raise ValueError("Nu există încă plăți de salariu.")
    return payment_context(request, p, lang)


def sample_bank(request, lang, options):
    p = Payment.objects.filter(lines__method="card").first()
    if p is None:
        raise ValueError("Nu există încă plăți pe card.")
    return payment_context(request, p, lang, only_card=True)


def sample_annual(request, lang, options):
    from .models import PayrollLine

    ln = PayrollLine.objects.filter(payroll__status="approved").select_related("employee", "payroll").first()
    if ln is None:
        raise ValueError("Nu există încă calcule aprobate.")
    return annual_context(request, ln.employee, ln.payroll.year, lang)


# --- cererea de scutire (anexa 6 la Regulamentul aprobat prin HG 697/2014) ---------------------------------------------
def exemption_context(request, req, lang="ro") -> dict:
    from apps.printing.words import amount_in_words

    from .engine import Constants
    from .exemptions import annual_parts

    start = req.date_from or req.date
    first = start.replace(day=1)
    c = Constants(first)
    parts = annual_parts(req, first, c)
    # suma cerută pe an: P / M și Sm din cerere, N / H pentru toate persoanele cu venitul declarat sub plafon
    deps = list(req.dependents.all())
    counted = [d for d in deps if d.income_ok]
    parts["N"] = c("exemption_dependent") * sum(1 for d in counted if d.code == "N")
    parts["H"] = c("exemption_dependent_disabled") * sum(1 for d in counted if d.code == "H")
    labels = {"P": "Scutirea personală (P)", "M": "Scutirea personală majorată (M)", "Sm": "Scutirea pentru soț / soție (Sm)",
              "N": "Persoanele întreținute (N)", "H": "Persoanele întreținute cu dizabilitate (H)"}
    total = sum(parts.values(), 0)
    docs = []
    if req.kind == "major" and req.major_document:
        docs.append({"title": req.major_document, "for": f"M — {req.get_major_category_display()}"})
    if req.spouse_major and req.spouse_document:
        docs.append({"title": req.spouse_document, "for": f"Sm — {req.spouse_name}"})
    docs += [{"title": d.document, "for": f"{d.code} — {d.name}"} for d in deps if d.document]
    if req.documents:
        docs.append({"title": req.documents, "for": ""})
    e = req.employee
    data = {"year": start.year, "number": req.number, "date": _d(req.date), "date_from": _d(req.date_from), "date_to": _d(req.date_to),
            "employee": {"name": e.full_name(), "idnp": e.idnp, "address": e.address},
            "place": req.get_place_display(), "place_main": req.place == "main",
            "P": req.kind == "personal", "M": req.kind == "major",
            "major_category": req.get_major_category_display() if req.kind == "major" and req.major_category else "",
            "Sm": req.spouse_major, "spouse": {"name": req.spouse_name, "idnp": req.spouse_idnp,
                                                "category": req.get_spouse_category_display() if req.spouse_category else ""},
            "N": sum(1 for d in counted if d.code == "N"), "H": sum(1 for d in counted if d.code == "H"),
            "dependents": [{"name": d.name, "idnp": d.idnp, "birth_date": _d(d.birth_date), "relation": d.get_relation_display(),
                            "code": d.code if d.income_ok else "—", "date_from": _d(d.date_from), "date_to": _d(d.date_to)} for d in deps],
            "documents": docs, "sums": [{"label": labels[k], "amount": _money(v)} for k, v in parts.items() if v],
            "total": _money(total) or "0,00", "total_words": amount_in_words(total, "MDL", "ru" if lang == "ru" else "ro"),
            "code": req.code()}
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "req": data, "today": _d(timezone.localdate()),
            "placeholders": {"an": start.year}}


def print_exemption_request(request, req):
    lang = _lang(request)
    return print_document(request, "exemption_request", exemption_context(request, req, lang),
                          template_id=request.query_params.get("template"),
                          title=f"Cererea de scutire — {req.employee.full_name()}", lang=lang)


def sample_exemption(request, lang, options):
    from .models import ExemptionRequest

    req = ExemptionRequest.objects.select_related("employee").first()
    if req is None:
        raise ValueError("Nu există încă cereri de scutire.")
    return exemption_context(request, req, lang)
