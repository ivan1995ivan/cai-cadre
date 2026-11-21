"""Avertismentele și alertele salarizării: salariul de funcție sub salariul minim (la angajare, la ordinul de salariu și
în lista „Termene și alerte”), venitul anual care se apropie de plafonul scutirii P / M (Codul fiscal, art. 33 alin. (1))."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from apps.alerts import engine as alerts

ZERO = Decimal("0")


def min_wage_warning(base_salary, kind: str = "main", on_date: date | None = None) -> str:
    """Salariul de funcție (pentru norma întreagă) sub salariul minim pe țară: textul avertismentului sau „”. La calcul se
    adaugă singură „Completarea până la salariul minim” (pro-rata la timpul lucrat)."""
    from django.utils import timezone

    from .engine import Constants, num

    if kind == "contractor" or base_salary in (None, ""):
        return ""
    try:
        salary = Decimal(str(base_salary))
    except (InvalidOperation, ValueError):
        return ""
    minimum = Constants(on_date or timezone.localdate())("min_salary")
    if not minimum or salary >= minimum:
        return ""
    return (f"Salariul de funcție {num(salary)} lei pentru norma întreagă este sub salariul minim pe țară ({num(minimum)} lei). "
            "La calcul se adaugă completarea până la salariul minim (Codul muncii, art. 131).")


def _min_wage(today, days, cfg):
    from apps.staff.models import Employment

    from .engine import Constants, num

    minimum = Constants(today)("min_salary")
    out = []
    if not minimum:
        return out
    for j in (Employment.objects.exclude(status="ended").exclude(kind="contractor").filter(base_salary__lt=minimum)
              .select_related("employee", "occupation")):
        out.append(alerts.Alert("min_wage", f"minwage:{j.pk}:{j.base_salary}:{minimum}", "Salariul sub salariul minim",
                                f"{j.employee.full_name()} ({j.occupation.name_ro}) — {num(j.base_salary)} lei < {num(minimum)} lei",
                                today, "warning", j.employee_id, j.employee.full_name(), {j.subdivision_id},
                                f"/employees/{j.employee_id}?tab=jobs"))
    return out


def _exemption_limit(today, days, cfg):
    """Angajații cu P / M al căror venit impozabil al anului (calculele aprobate) a atins pragul alertei din plafon."""
    from .engine import Constants
    from .exemptions import requests_in
    from .models import PayrollLine

    c = Constants(today)
    limit, pct = c("exemption_income_limit", "360000"), c("exemption_limit_alert_pct", "90")
    if not limit or not pct:
        return []
    first = today.replace(day=1)
    requests = {e: r for e, r in requests_in(first).items() if r.personal_in(first)}
    income = defaultdict(lambda: ZERO)
    for ln in PayrollLine.objects.filter(employee_id__in=list(requests), payroll__year=today.year, payroll__status="approved",
                                         payroll__deletion_mark=False):
        income[ln.employee_id] += ln.taxable
    out = []
    for emp, req in requests.items():
        if income[emp] < limit * pct / 100:
            continue
        e = req.employee
        out.append(alerts.Alert("exemption_limit", f"exlimit:{emp}:{today.year}", "Venitul anual se apropie de plafonul scutirii",
                                f"{e.full_name()} — venitul impozabil {income[emp]:,.0f} lei din {limit:,.0f} ({req.code()}): cererea "
                                "de renunțare la P / M se aplică din luna următoare".replace(",", " "),
                                today, "warning", emp, e.full_name(), alerts._subs(e), f"/employees/{emp}?tab=pay"))
    return out


alerts.register("min_wage", True, 0, ("hr", "accounting"), _min_wage)
alerts.register("exemption_limit", True, 0, ("accounting",), _exemption_limit)
