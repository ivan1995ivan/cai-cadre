"""Îndreptarea spre plată (salariu sau avans): CNAM, scutirea și impozitul pe venit reținute la plată, achitarea, fișierul
pentru bancă, decontarea lunii pe angajat (fluturașul, cabinetul) și soldul salarial.

Calculul salariului (engine) dă pe fiecare angajat brutul lunii, baza impozitului, baza CNAM și celelalte rețineri.
Impozitele se socotesc aici, cumulat pe lună: la fiecare plată se ia tot venitul plătit în lună până atunci (inclusiv
avansul), se socotesc CNAM, scutirea lunii și impozitul pe el și se reține diferența față de ce s-a reținut deja.

Regimul IT Park (apps.payroll.it_park): salariul din CIM calculat într-o lună în regim e impozitat final — bazele lui sunt 0,
deci nu se reține nici CNAM, nici impozitul, iar scutirea nu se acordă; avansul unei luni în regim se plătește întreg. Partea
plătită din acest salariu se ține pe rând (`final_gross`): IPC21 (tabelul 1), IALS21 și anexa 8 o lasă deoparte, ISAPTI17 și
nota anuală o adună. Regimul e al lunii pentru care se plătește, nu al datei plății (CF art. 375).
"""
import csv
import io
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.http import HttpResponse
from rest_framework.exceptions import ValidationError

from apps.staff.models import Employee, Employment

from . import it_park
from .engine import MAIN_KINDS, Constants, month_bounds, q
from .models import Payment, PaymentLine, PayrollLine

ZERO = Decimal("0")
MONTHS = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie",
          "noiembrie", "decembrie"]


def _method(employee: Employee) -> str:
    return "card" if (employee.iban or "").strip() else "cash"


FIELDS = ("gross", "exemption", "cnam", "income_tax", "deductions", "amount", "final_gross")
TAXES = ("exemption", "cnam", "income_tax")


def _zero() -> dict:
    return {f: ZERO for f in FIELDS}


def _rates(c: Constants) -> tuple:
    return c("cnam_employee_pct", "9") / 100, c("income_tax_pct", "12") / 100


def accrued(year: int, month: int, payroll=None, employee_ids=None) -> dict:
    """Ce s-a calculat în lună pe angajat (calculele aprobate; cu `payroll` — doar acela): brutul, baza impozitului,
    baza CNAM și celelalte rețineri."""
    out = defaultdict(lambda: {"gross": ZERO, "taxable": ZERO, "cnam_base": ZERO, "deductions": ZERO, "final": ZERO})
    qs = PayrollLine.objects.filter(payroll__year=year, payroll__month=month, payroll__status="approved",
                                    payroll__deletion_mark=False)
    if payroll is not None:
        qs = qs.filter(payroll=payroll)
    if employee_ids is not None:
        qs = qs.filter(employee_id__in=employee_ids)
    for ln in qs:
        a = out[ln.employee_id]
        for f in ("gross", "taxable", "cnam_base", "deductions"):
            a[f] += getattr(ln, f)
        if ln.it_park:
            a["final"] += ln.gross  # salariul impozitat final (IT Park)
    return out


def _paid_before(year: int, month: int, exclude_payment=None, employee_ids=None) -> dict:
    """Ce s-a plătit (și reținut) deja pentru luna dată — avansuri și salariu, aprobate sau achitate — pe angajat."""
    out = defaultdict(_zero)
    qs = PaymentLine.objects.filter(payment__year=year, payment__month=month, payment__status__in=("approved", "paid"),
                                    payment__deletion_mark=False)
    if exclude_payment is not None and exclude_payment.pk:
        qs = qs.exclude(payment=exclude_payment)
    if employee_ids is not None:
        qs = qs.filter(employee_id__in=employee_ids)
    for ln in qs:
        for f in FIELDS:
            out[ln.employee_id][f] += getattr(ln, f)
    return out


def monthly_exemptions(year: int, month: int, c: Constants, month_taxable: dict) -> dict:
    """Scutirea lunii pe angajat (apps.payroll.exemptions): suma anuală a scutirilor valabile în lună / 12."""
    from .exemptions import month_parts

    return {emp: q(sum(parts.values(), ZERO) / 12) for emp, parts in month_parts(year, month, c, month_taxable).items()}


def month_taxes(acc: dict, paid_gross: Decimal, c: Constants, exemption: Decimal) -> dict:
    """CNAM, scutirea folosită și impozitul pe venitul plătit în lună până acum (`paid_gross`, inclusiv plata de față):
    bazele lunii se iau în proporția plătită din brut, scutirea lunii — o dată."""
    cnam_pct, tax_pct = _rates(c)
    share = min(paid_gross / acc["gross"], Decimal(1)) if acc["gross"] > 0 else ZERO
    tax_base, cnam_base = acc["taxable"] * share, acc["cnam_base"] * share
    cnam = q(cnam_base * cnam_pct)
    used = min(exemption, max(tax_base - cnam, ZERO))
    return {"exemption": q(used), "cnam": cnam, "income_tax": q(max(tax_base - cnam - exemption, ZERO) * tax_pct)}


def salary_due(payment: Payment) -> dict:
    """Restul de plată al lunii pe angajat: din calculul de bază (doar angajații lui, cel mult suma lui) sau pe sold (toate
    calculele aprobate ale lunii), minus ce s-a plătit deja în lună; impozitele — cumulat pe lună, minus cele reținute."""
    year, month = payment.year, payment.month
    totals = accrued(year, month)
    scope = accrued(year, month, payroll=payment.payroll) if payment.payroll_id else totals
    paid = _paid_before(year, month, exclude_payment=payment)
    c = Constants(payment.date)
    exemptions = monthly_exemptions(year, month, c, {e: a["taxable"] for e, a in totals.items()})
    due = {}
    for emp, s in scope.items():
        a, p = totals[emp], paid.get(emp) or _zero()
        gross = min(a["gross"] - p["gross"], s["gross"])
        if gross <= 0:
            continue
        deductions = max(min(a["deductions"] - p["deductions"], s["deductions"]), ZERO)
        cum = month_taxes(a, p["gross"] + gross, c, exemptions.get(emp, ZERO))
        row = {"gross": gross, "deductions": deductions, **{f: cum[f] - p[f] for f in TAXES}}
        row["final_gross"] = final_part(a, p["gross"] + gross, p["final_gross"], gross)
        row["amount"] = row["gross"] - row["cnam"] - row["income_tax"] - row["deductions"]
        if row["amount"] > 0:
            due[emp] = row
    return due


def final_part(a: dict, paid_total: Decimal, final_before: Decimal, gross: Decimal) -> Decimal:
    """Partea impozitată final (IT Park) din plata de față: în proporția salariului din regim în brutul lunii, cumulat pe lună,
    minus ce s-a plătit deja din el; cel mult plata."""
    if a["gross"] <= 0 or not a.get("final"):
        return ZERO
    cum = q(min(paid_total, a["gross"]) * a["final"] / a["gross"])
    return min(max(cum - final_before, ZERO), gross)


def advance_taxes(gross: Decimal, c: Constants, final: bool = False) -> dict:
    """Reținerea din avans: CNAM 9 % din sumă, impozitul 12 % din rest (scutirea lunii se ia la plata salariului). În luna
    în regim IT Park avansul (din salariul CIM) e impozitat final — se plătește întreg."""
    gross = q(gross)
    if final:
        return {"gross": gross, "exemption": ZERO, "cnam": ZERO, "income_tax": ZERO, "deductions": ZERO, "amount": gross,
                "final_gross": gross}
    cnam_pct, tax_pct = _rates(c)
    cnam = q(gross * cnam_pct)
    tax = q(max(gross - cnam, ZERO) * tax_pct)
    return {"gross": gross, "exemption": ZERO, "cnam": cnam, "income_tax": tax, "deductions": ZERO, "amount": gross - cnam - tax,
            "final_gross": ZERO}


def advance_due(payment: Payment) -> dict:
    """Avansul lunii: procentul din constante × salariul de funcție × norma raportului de bază (brut, rotunjit la leu),
    cu impozitul reținut din el."""
    year, month = payment.year, payment.month
    first, _last = month_bounds(year, month)
    c = Constants(payment.date)
    pct = c("advance_pct", "40")
    already = defaultdict(lambda: ZERO)
    qs = PaymentLine.objects.filter(payment__year=year, payment__month=month, payment__kind="advance",
                                    payment__status__in=("approved", "paid"), payment__deletion_mark=False)
    if payment.pk:
        qs = qs.exclude(payment=payment)
    for ln in qs:
        already[ln.employee_id] += ln.gross
    due = {}
    final = it_park.is_it_park(year, month)
    jobs = Employment.objects.filter(kind__in=MAIN_KINDS, status="active", date_from__lte=first).select_related("employee")
    for job in jobs:
        gross = (job.base_salary * job.rate * pct / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP) - already[job.employee_id]
        if gross > 0:
            due[job.employee_id] = advance_taxes(gross, c, final=final)
    return due


def check_base(payment: Payment):
    """Calculul de bază: doar la salariu, aprobat, nemarcat pentru ștergere."""
    base = payment.payroll
    if base is None:
        return
    if payment.kind != "salary":
        raise ValidationError({"payroll": "Avansul nu se face în baza unui calcul."})
    if base.status != "approved" or base.deletion_mark:
        raise ValidationError({"payroll": "Îndreptarea spre plată se face în baza unui calcul aprobat."})


@transaction.atomic
def fill(payment: Payment) -> int:
    """Completează îndreptarea cu sumele datorate (rândurile existente se înlocuiesc; ciorna se poate corecta apoi)."""
    if payment.status != "draft":
        raise ValidationError({"detail": "Se completează doar ciorna."})
    check_base(payment)
    due = (salary_due if payment.kind == "salary" else advance_due)(payment)
    employees = {e.pk: e for e in Employee.objects.filter(pk__in=due)}
    payment.lines.all().delete()
    rows = sorted(employees.values(), key=lambda e: (e.last_name, e.first_name, e.pk))
    n = 0
    for e in rows:
        method = _method(e)
        if payment.method != "all" and method != payment.method:
            continue
        n += 1
        d = {f: q(v) for f, v in due[e.pk].items()}
        PaymentLine.objects.create(payment=payment, employee=e, method=method, iban=e.iban if method == "card" else "",
                                   basis={f: str(v) for f, v in d.items()}, sort=n * 10, **d)
    return n


def _dec(value, field: str) -> Decimal:
    try:
        v = Decimal(str(value).replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValidationError({field: "Nu este un număr."}) from None
    if v < 0:
        raise ValidationError({field: "Suma nu poate fi negativă."})
    return q(v)


def update_line(line: PaymentLine, data: dict) -> PaymentLine:
    """Corectarea de mână a unui rând din ciornă:
    - brutul → impozitele se refac (la salariu în aceeași proporție ca la completare, cu scutirea; la avans — 9 % și 12 %);
    - suma de plată (netul) → se află brutul care dă exact acest net;
    - CNAM, impozitul, scutirea sau reținerile scrise direct → rămân cum sunt scrise, se reface doar netul."""
    payment = line.payment
    if payment.status != "draft":
        raise ValidationError({"detail": "Se schimbă doar ciorna."})
    basis = {k: Decimal(str(v)) for k, v in (line.basis or {}).items() if k in FIELDS}
    proportional = payment.kind == "salary" and basis.get("gross", ZERO) > 0
    c = Constants(payment.date)
    cnam_pct, tax_pct = _rates(c)
    final_advance = payment.kind == "advance" and it_park.is_it_park(payment.year, payment.month)

    def taxes_for(gross: Decimal) -> dict:
        if proportional:
            k = gross / basis["gross"]
            return {"exemption": q(basis.get("exemption", ZERO) * k), "cnam": q(basis.get("cnam", ZERO) * k),
                    "income_tax": q(basis.get("income_tax", ZERO) * k), "final_gross": min(q(basis.get("final_gross", ZERO) * k), gross)}
        t = advance_taxes(gross, c, final=final_advance)
        return {"exemption": ZERO, "cnam": t["cnam"], "income_tax": t["income_tax"], "final_gross": t["final_gross"]}

    if "method" in data:
        if data["method"] not in ("card", "cash"):
            raise ValidationError({"method": "Card sau numerar."})
        line.method = data["method"]
    if "iban" in data:
        line.iban = str(data["iban"] or "").replace(" ", "")[:34]
    if "note" in data:
        line.note = str(data["note"] or "")[:300]
    if "deductions" in data:
        line.deductions = _dec(data["deductions"], "deductions")
    if "gross" in data:
        line.gross = _dec(data["gross"], "gross")
        for f, v in taxes_for(line.gross).items():
            setattr(line, f, v)
    elif "amount" in data:
        net = _dec(data["amount"], "amount")
        if proportional:
            base_net = basis["gross"] - basis.get("cnam", ZERO) - basis.get("income_tax", ZERO)
            gross = basis["gross"] * net / base_net if base_net > 0 else net
        elif final_advance:
            gross = net
        else:
            gross = net / ((1 - cnam_pct) * (1 - tax_pct))
        for f, v in taxes_for(q(gross)).items():
            setattr(line, f, v)
        line.gross = net + line.deductions + line.cnam + line.income_tax  # netul rămâne exact cel scris
    manual_taxes = [f for f in ("exemption", "cnam", "income_tax") if f in data]
    for f in manual_taxes:
        setattr(line, f, _dec(data[f], f))
    if manual_taxes or any(f in data for f in ("gross", "amount", "deductions")):
        line.manual = True
    line.final_gross = min(line.final_gross, line.gross)
    line.amount = line.gross - line.cnam - line.income_tax - line.deductions
    if line.amount < 0:
        raise ValidationError({"amount": "Reținerile depășesc suma brută."})
    line.save()
    return line


def totals(payment: Payment) -> dict:
    out = {"card": ZERO, "cash": ZERO, "gross": ZERO, "exemption": ZERO, "cnam": ZERO, "income_tax": ZERO, "deductions": ZERO}
    count = 0
    for ln in payment.lines.all():
        count += 1
        out[ln.method] = out.get(ln.method, ZERO) + ln.amount
        for f in ("gross", "exemption", "cnam", "income_tax", "deductions"):
            out[f] += getattr(ln, f)
    return {"card": float(out["card"]), "cash": float(out["cash"]), "total": float(out["card"] + out["cash"]),
            **{f: float(out[f]) for f in ("gross", "exemption", "cnam", "income_tax", "deductions")}, "count": count}


def settlement(year: int, month: int, employee_ids=None) -> dict:
    """Decontarea lunii pe angajat (fluturașul, cabinetul): calculat, celelalte rețineri, CNAM, scutirea și impozitul,
    netul lunii, ce s-a achitat (avans, salariu) și restul. Cât luna nu e plătită toată, impozitele sunt cele pe tot venitul
    lunii (cât se va reține până la urmă, cu cotele de la sfârșitul lunii); plătită toată — cele reținute efectiv."""
    acc = accrued(year, month, employee_ids=employee_ids)
    paid = _paid_before(year, month, employee_ids=employee_ids)
    by_kind = defaultdict(lambda: {"advance": ZERO, "salary": ZERO})
    for ln in PaymentLine.objects.filter(payment__year=year, payment__month=month, payment__status__in=("approved", "paid"),
                                         payment__deletion_mark=False, employee_id__in=list(acc)).select_related("payment"):
        by_kind[ln.employee_id][ln.payment.kind] += ln.amount
    c = Constants(month_bounds(year, month)[1])
    exemptions = monthly_exemptions(year, month, c, {e: a["taxable"] for e, a in acc.items()})
    out = {}
    for emp, a in acc.items():
        p = paid.get(emp) or _zero()
        final = a["gross"] - p["gross"] <= 0
        taxes = {f: p[f] for f in TAXES} if final else month_taxes(a, a["gross"], c, exemptions.get(emp, ZERO))
        net = a["gross"] - a["deductions"] - taxes["cnam"] - taxes["income_tax"]
        out[emp] = {"gross": a["gross"], "taxable": a["taxable"], "deductions": a["deductions"], **taxes, "net": net,
                    "paid_advance": by_kind[emp]["advance"], "paid_salary": by_kind[emp]["salary"],
                    "rest": net - p["amount"], "final": final,
                    # IT Park: salariul impozitat final (tot sau o parte — cu un contract de prestări servicii alături)
                    "it_park": a["final"] > 0, "it_park_only": a["final"] > 0 and a["final"] >= a["gross"]}
    return out


def debts(year: int, month: int, employee_ids=None) -> list:
    """Soldul salarial pe angajat până la sfârșitul lunii date: brutul calculelor aprobate minus celelalte rețineri, minus
    brutul achitat (salariu și avans, cu impozitele reținute din el) fără reținerile făcute la plată. E înainte de impozit:
    impozitul și CNAM se rețin din el la îndreptarea spre plată. Negativ — plătit în plus."""
    owed, paid = defaultdict(lambda: ZERO), defaultdict(lambda: ZERO)
    limit = year * 100 + month
    for ln in PayrollLine.objects.filter(payroll__status="approved", payroll__deletion_mark=False).select_related("payroll"):
        if ln.payroll.year * 100 + ln.payroll.month <= limit:
            owed[ln.employee_id] += ln.gross - ln.deductions
    for pl in PaymentLine.objects.filter(payment__status="paid", payment__deletion_mark=False).select_related("payment"):
        if pl.payment.year * 100 + pl.payment.month <= limit:
            paid[pl.employee_id] += pl.gross - pl.deductions
    ids = set(owed) | set(paid)
    if employee_ids is not None:
        ids &= set(employee_ids)
    people = {e.pk: e for e in Employee.objects.filter(pk__in=ids)}
    rows = []
    for pk in ids:
        debt = owed[pk] - paid[pk]
        if debt == 0:
            continue
        e = people[pk]
        rows.append({"employee": pk, "name": e.full_name(), "tab_number": e.tab_number, "owed": float(owed[pk]),
                     "paid": float(paid[pk]), "debt": float(debt)})
    return sorted(rows, key=lambda r: r["name"])


def bank_file(payment: Payment) -> HttpResponse:
    """Fișierul pentru bancă (CSV, „;”, UTF-8): IBAN, numele, IDNP, suma, destinația. Formatul exact al băncii se reglează
    la instalare (MAIB / Victoriabank / Moldindconbank primesc de regulă un tabel cu aceste coloane)."""
    rows = list(payment.lines.filter(method="card").select_related("employee").order_by("sort", "id"))
    missing = [ln.employee.full_name() for ln in rows if not ln.iban]
    if missing:
        raise ValidationError({"detail": f"Fără IBAN: {', '.join(missing[:5])}" + ("..." if len(missing) > 5 else "")})
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    purpose = f"{payment.get_kind_display()} pentru luna {MONTHS[payment.month]} {payment.year}"
    w.writerow(["Nr", "IBAN", "Numele, prenumele", "IDNP", "Suma", "Destinația plății"])
    for n, ln in enumerate(rows, start=1):
        w.writerow([n, ln.iban, ln.employee.full_name(), ln.employee.idnp, f"{ln.amount:.2f}", purpose])
    w.writerow(["", "", "Total", "", f"{sum((ln.amount for ln in rows), ZERO):.2f}", ""])
    response = HttpResponse("﻿" + buf.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="banca-{payment.year}-{payment.month:02d}-{payment.number or payment.pk}.csv"'
    return response
