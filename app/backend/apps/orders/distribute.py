"""Împărțirea unei sume (prima colectivă) pe punctele ordinului de stimulare: egal, după salariul de funcție (pentru norma
raportului) sau după orele lucrate în luna dată (pontajul). Sumele se rotunjesc la bani, iar diferența de rotunjire merge la
partea cea mai mare, ca totalul să fie exact; nimic nu rămâne nerepartizat. Doar propunerea — sumele se pun în puncte din
ecran (se pot corecta)."""
from decimal import ROUND_HALF_UP, Decimal

from rest_framework.exceptions import ValidationError

CENT = Decimal("0.01")
METHODS = ("equal", "salary", "hours")


def split(total: Decimal, weights: list) -> list:
    whole = sum(weights, Decimal("0"))
    if whole <= 0:
        raise ValidationError({"detail": "Nu e după ce împărți: toate bazele sunt 0 (salariul / orele)."})
    parts = [(total * w / whole).quantize(CENT, rounding=ROUND_HALF_UP) for w in weights]
    rest = total - sum(parts, Decimal("0"))
    if rest:
        k = max(range(len(parts)), key=lambda i: (weights[i], -i))
        parts[k] += rest
    return parts


def hours(job, year: int, month: int) -> Decimal:
    from apps.worktime.models import TimesheetLine

    out = Decimal("0")
    for ln in TimesheetLine.objects.filter(employment=job, timesheet__year=year, timesheet__month=month,
                                           timesheet__deletion_mark=False):
        out += Decimal(str((ln.totals or {}).get("hours") or 0))
    return out


def distribute(order, total, method: str, year=None, month=None) -> dict:
    if order.order_type.effect != "incentive":
        raise ValidationError({"detail": "Suma se împarte doar în ordinul de stimulare (premiere)."})
    try:
        total = Decimal(str(total)).quantize(CENT)
    except Exception:  # noqa: BLE001
        raise ValidationError({"total": "Suma nu e un număr."}) from None
    if total <= 0:
        raise ValidationError({"total": "Suma de împărțit e mai mare decât 0."})
    if method not in METHODS:
        raise ValidationError({"method": "Felul: egal, după salariu sau după ore."})
    if method == "hours" and not (year and month):
        raise ValidationError({"month": "Alegeți luna orelor (pontajul)."})
    items = [it for it in order.items.select_related("employee", "employment").order_by("sort", "id") if it.employee_id]
    if not items:
        raise ValidationError({"detail": "Ordinul n-are angajați."})
    rows = []
    for it in items:
        job = it.employment or it.employee.main_employment()
        if method == "equal":
            basis = Decimal("1")
        elif method == "salary":
            basis = (job.base_salary * job.rate) if job else Decimal("0")
        else:
            basis = hours(job, int(year), int(month)) if job else Decimal("0")
        rows.append({"item": it.pk, "employee": it.employee_id, "name": it.employee.full_name(), "basis": basis})
    for row, amount in zip(rows, split(total, [r["basis"] for r in rows])):
        row["amount"] = amount
    return {"total": float(total), "method": method,
            "rows": [{**r, "basis": float(r["basis"]), "amount": float(r["amount"])} for r in rows]}
