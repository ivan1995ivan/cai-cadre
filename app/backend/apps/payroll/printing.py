"""Tiparul statului de calcul (toate rândurile lunii) și al fișelor de calcul (fluturașul fiecărui angajat pe lună:
raporturile lui de muncă din calculele aprobate ale lunii și decontarea — CNAM, scutirea și impozitul reținute la plată,
avansul, ce s-a achitat, restul). Fluturașii se fac din îndreptarea spre plată pe salariu, pentru angajații ei, și din
cabinetul angajatului."""
from django.utils import timezone

from apps.printing.renderer import company_context
from apps.printing.views import print_document

from .models import Payment, Payroll, PayrollLine, PayType

MONTHS = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie",
          "noiembrie", "decembrie"]


def _d(value):
    return value.strftime("%d.%m.%Y") if value else ""


def _money(value) -> str:
    try:
        text = f"{float(value):,.2f}".replace(",", " ").replace(".", ",")
    except (TypeError, ValueError):
        return ""
    return "" if text in ("0,00", "-0,00") else text


def _lang(request):
    return request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro"


def _doc(payroll: Payroll) -> dict:
    from .it_park import FINAL_NOTE, is_it_park

    final = list(payroll.lines.values_list("it_park", flat=True))
    return {"number": payroll.number, "date": _d(payroll.date), "month": MONTHS[payroll.month], "year": payroll.year,
            "subdivision": payroll.subdivision.name_ro if payroll.subdivision_id else "toată întreprinderea",
            "status": payroll.get_status_display(), "totals": {k: _money(v) for k, v in (payroll.totals or {}).items()},
            # IT Park: salariul din CIM e impozitat final — fără coloanele de impozit, dacă nu e nimic în regimul general
            "it_park": is_it_park(payroll.year, payroll.month), "all_final": bool(final) and all(final), "final_note": FINAL_NOTE}


def _line(ln: PayrollLine) -> dict:
    info = ln.info or {}
    items = list(ln.items.select_related("pay_type").order_by("sort", "id"))
    acc = [{"name": i.pay_type.name_ro, "qty": f"{float(i.quantity):g}" if i.quantity else "", "pct": f"{float(i.percent):g}%" if i.percent else "",
            "amount": _money(i.amount), "note": i.note} for i in items if i.pay_type.category == "accrual" and i.pay_type.on_payslip]
    ded = [{"name": i.pay_type.name_ro, "amount": _money(i.amount), "note": i.note} for i in items
           if i.pay_type.category == "deduction" and i.pay_type.on_payslip]
    ts = info.get("timesheet") or {}
    return {"name": info.get("name") or ln.employee.full_name(), "tab_number": info.get("tab_number", ""), "occupation": info.get("occupation", ""),
            "subdivision": info.get("subdivision", ""), "kind": info.get("kind_label", "") if info.get("kind") != "main" else "",
            "rate": f"{float(info.get('rate', 1)) * 100:g}%", "salary": _money(info.get("base_salary")), "days": ts.get("days", ""),
            "hours": f"{ts.get('hours', 0):g}" if ts.get("hours") else "", "gross": _money(ln.gross), "taxable": _money(ln.taxable),
            "cnam_base": _money(ln.cnam_base), "cas": _money(ln.cas), "deductions": _money(ln.deductions), "net": _money(ln.net),
            "accruals": acc, "deductions_list": ded, "iban": ln.employee.iban, "it_park": ln.it_park}


def _settle(s: dict) -> dict:
    """Decontarea lunii a angajatului (payments.settlement), cu sumele scrise pentru tipar."""
    from .it_park import FINAL_NOTE

    return {**{k: _money(s[k]) for k in ("gross", "deductions", "exemption", "cnam", "income_tax", "net", "paid_advance",
                                          "paid_salary", "rest")}, "final": s["final"],
            "it_park": s.get("it_park", False), "it_park_only": s.get("it_park_only", False), "final_note": FINAL_NOTE}


def month_lines(year: int, month: int, employee_ids) -> list:
    """Raporturile de muncă ale angajaților din calculele aprobate ale lunii — rândurile fluturașului."""
    return list(PayrollLine.objects.filter(payroll__year=year, payroll__month=month, payroll__status="approved",
                                           payroll__deletion_mark=False, employee_id__in=list(employee_ids))
                .select_related("employee").order_by("employee__last_name", "employee__first_name", "employee_id", "sort", "id"))


def payment_slip_lines(payment: Payment, employee_ids=None) -> list:
    """Rândurile fluturașilor îndreptării pe salariu: angajații ei (sau doar cei dați), cu toată luna lor."""
    ids = set(payment.lines.values_list("employee_id", flat=True))
    if employee_ids is not None:
        ids &= set(employee_ids)
    return month_lines(payment.year, payment.month, ids)


def slips_of(year: int, month: int, lines) -> list:
    """Fluturașii: câte unul pe angajat, cu raporturile lui de muncă din calcule și decontarea lunii."""
    from .payments import settlement

    by_emp: dict = {}
    for ln in lines:
        by_emp.setdefault(ln.employee_id, []).append(ln)
    settle = settlement(year, month, employee_ids=list(by_emp))
    out = []
    for emp, emp_lines in by_emp.items():
        jobs = [_line(ln) for ln in emp_lines]
        out.append({"name": jobs[0]["name"], "tab_number": jobs[0]["tab_number"], "jobs": jobs,
                    "settle": _settle(settle[emp]) if emp in settle else None})
    return out


def sheet_context(request, payroll: Payroll, lang="ro") -> dict:
    lines = payroll.lines.select_related("employee").order_by("sort", "id")
    rows = [{"no": n, **_line(ln)} for n, ln in enumerate(lines, start=1)]
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "doc": _doc(payroll), "rows": rows,
            "today": _d(timezone.localdate()), "placeholders": {"luna": MONTHS[payroll.month], "an": payroll.year, "număr": payroll.number}}


def payslip_context(request, year: int, month: int, lines, lang="ro") -> dict:
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "doc": {"month": MONTHS[month], "year": year},
            "slips": slips_of(year, month, lines), "today": _d(timezone.localdate()),
            "placeholders": {"luna": MONTHS[month], "an": year}}


def print_sheet(request, payroll: Payroll):
    lang = _lang(request)
    return print_document(request, "payroll_sheet", sheet_context(request, payroll, lang), template_id=request.query_params.get("template"),
                          title=f"Stat de calcul {payroll.month:02d}.{payroll.year}", lang=lang)


def print_payslips(request, year: int, month: int, lines):
    lang = _lang(request)
    return print_document(request, "payslip", payslip_context(request, year, month, lines, lang), template_id=request.query_params.get("template"),
                          title=f"Fișa de calcul {month:02d}.{year}", lang=lang)


def sample_sheet(request, lang, options):
    doc = Payroll.objects.filter(lines__isnull=False).first()
    if doc is None:
        raise ValueError("Nu există încă un calcul al salariului.")
    return sheet_context(request, doc, lang)


def sample_payslip(request, lang, options):
    first = PayrollLine.objects.filter(payroll__status="approved").select_related("payroll").order_by("-payroll__year", "-payroll__month").first()
    if first is None:
        raise ValueError("Nu există încă un calcul aprobat al salariului.")
    year, month = first.payroll.year, first.payroll.month
    return payslip_context(request, year, month, month_lines(year, month, [first.employee_id]), lang)
