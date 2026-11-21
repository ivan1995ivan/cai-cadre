"""Scutirile la impozitul pe venit din salariu (Codul fiscal, art. 33–35; Regulamentul aprobat prin HG 697/2014).

- Cererea angajatului e valabilă de la / până la (nu se reînnoiește anual) și se înlocuiește cu una nouă la schimbare;
  se aplică din luna următoare depunerii (`ExemptionRequest.date_from`).
- Pe lună: suma anuală a scutirilor valabile în lună / 12 — P sau M (până la luna renunțării inclusiv), Sm, câte N / H
  pentru fiecare întreținut al cărui drept e valabil în lună (din luna următoare apariției lui, art. 35 alin. (4)).
  Scutirea folosită nu trece de venitul lunii (payments.month_taxes).
- IT Park (CF art. 377 alin. (2); SFS 37.30, 37.42): în luna în care angajatul are salariu calculat în regim (impozitat
  final) scutirile nu se acordă deloc — nici pe venitul din regimul general al aceleiași luni; se acordă doar în lunile din
  regimul general.
- P și M nu se acordă dacă venitul anual impozabil trece de plafon (art. 33 alin. (1), 360 000 lei): angajatul depune
  cererea de renunțare (din luna următoare ei, fără recalcularea lunilor trecute); la angajator, când venitul anului de aici
  trece de plafon, P / M se opresc singure din luna aceea. Alerta „se apropie de plafon” — de la % din constante.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal

from .models import ExemptionRequest, PayrollLine

ZERO = Decimal("0")
CODES = ("P", "M", "Sm", "N", "H")


def requests_in(first: date, employee_ids=None) -> dict:
    """Cererea în vigoare în luna care începe la `first`, pe angajat (cea depusă ultima, dacă se suprapun)."""
    qs = ExemptionRequest.objects.filter(is_active=True).exclude(date_to__lt=first).prefetch_related("dependents")
    if employee_ids is not None:
        qs = qs.filter(employee_id__in=list(employee_ids))
    out = {}
    for r in qs.order_by("date_from", "date", "id"):
        if r.valid_in(first):
            out[r.employee_id] = r
    return out


def annual_parts(req: ExemptionRequest | None, first: date, c, personal_allowed=True) -> dict:
    """Sumele anuale ale scutirilor din cerere valabile în lună, pe coduri (P, M, Sm, N, H)."""
    parts = {k: ZERO for k in CODES}
    if req is None:
        return parts
    personal = req.personal_in(first) if personal_allowed else ""
    if personal == "P":
        parts["P"] = c("exemption_personal")
    elif personal == "M":
        parts["M"] = c("exemption_major")
    if req.spouse_major:
        parts["Sm"] = c("exemption_spouse")
    for d in req.dependents_in(first):
        if d.code == "H":
            parts["H"] += c("exemption_dependent_disabled")
        else:
            parts["N"] += c("exemption_dependent")
    return parts


def income_before(year: int, month: int, employee_ids) -> dict:
    """Venitul impozabil al anului la angajator din lunile aprobate de dinainte, pe angajat."""
    out = defaultdict(lambda: ZERO)
    for ln in PayrollLine.objects.filter(employee_id__in=list(employee_ids), payroll__year=year, payroll__month__lt=month,
                                         payroll__status="approved", payroll__deletion_mark=False):
        out[ln.employee_id] += ln.taxable
    return out


def it_park_employees(year: int, month: int, employee_ids) -> set:
    """Angajații cu salariu calculat în regimul IT Park în lună (calculele aprobate)."""
    return set(PayrollLine.objects.filter(employee_id__in=list(employee_ids), payroll__year=year, payroll__month=month,
                                          payroll__status="approved", payroll__deletion_mark=False, it_park=True)
               .values_list("employee_id", flat=True))


def month_parts(year: int, month: int, c, month_taxable: dict) -> dict:
    """Pe angajat: {cod: suma anuală} valabile în lună; P / M cad dacă venitul anului de aici (cu luna) trece de plafon."""
    first = date(year, month, 1)
    requests = requests_in(first, month_taxable)
    before = income_before(year, month, requests)
    limit = c("exemption_income_limit", "360000")
    final = it_park_employees(year, month, requests)
    out = {}
    for emp, req in requests.items():
        if emp in final:  # salariu impozitat final în lună: fără scutiri
            out[emp] = {k: ZERO for k in CODES}
            continue
        # dreptul la P / M e doar pentru venitul anual impozabil MAI MIC decât plafonul: la exact 360 000 — fără scutire
        over = bool(limit) and before[emp] + month_taxable.get(emp, ZERO) >= limit
        out[emp] = annual_parts(req, first, c, personal_allowed=not over)
    return out
