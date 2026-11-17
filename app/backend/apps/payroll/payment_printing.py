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
