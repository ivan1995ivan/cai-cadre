"""Recalcularea cu comparație (calculul salariului): ce s-ar schimba dacă luna s-ar calcula din nou acum — pe angajat, vechi față
de nou (brutul, reținerile, CAS, de plată și rândurile pe tipuri care diferă) — și aplicarea doar pentru angajații aleși.

Încercarea rulează calculul întreg într-un punct de salvare al tranzacției și îl anulează: nimic nu se scrie. Aplicarea
recalculează doar angajații aleși (engine.calculate cu employee_id), ceilalți rămân cum erau."""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from . import engine

FIELDS = ("gross", "deductions", "cas", "net")
CENT = Decimal("0.01")


def snapshot(payroll) -> dict:
    out = defaultdict(lambda: {"name": "", "tab": "", **{f: Decimal("0") for f in FIELDS}, "items": defaultdict(Decimal)})
    for ln in payroll.lines.select_related("employee").prefetch_related("items__pay_type"):
        row = out[ln.employee_id]
        row["name"], row["tab"] = ln.employee.full_name(), ln.employee.tab_number
        for f in FIELDS:
            row[f] += getattr(ln, f)
        for it in ln.items.all():
            row["items"][it.pay_type.code] += it.amount
    return out


def preview(payroll, visible_ids=None) -> list:
    before = snapshot(payroll)
    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            engine.calculate(payroll)
            after = snapshot(payroll)
        finally:
            transaction.savepoint_rollback(sid)
    payroll.refresh_from_db()
    rows = []
    for emp in set(before) | set(after):
        if visible_ids is not None and emp not in visible_ids:
            continue
        old, new = before.get(emp), after.get(emp)
        changed = []
        codes = set(old["items"] if old else ()) | set(new["items"] if new else ())
        for code in sorted(codes):
            a = (old["items"].get(code) if old else None) or Decimal("0")
            b = (new["items"].get(code) if new else None) or Decimal("0")
            if (a - b).quantize(CENT) != 0:
                changed.append({"code": code, "old": float(a), "new": float(b)})
        diff = any(((old or {}).get(f, Decimal("0")) - (new or {}).get(f, Decimal("0"))).quantize(CENT) != 0 for f in FIELDS)
        if not changed and not diff and old is not None and new is not None:
            continue
        status = "new" if old is None else "removed" if new is None else "changed"
        ref = new or old
        rows.append({"employee": emp, "name": ref["name"], "tab_number": ref["tab"], "status": status,
                     **{f"old_{f}": float(old[f]) if old else None for f in FIELDS},
                     **{f"new_{f}": float(new[f]) if new else None for f in FIELDS},
                     "diff_net": float((new["net"] if new else 0) - (old["net"] if old else 0)), "items": changed})
    return sorted(rows, key=lambda r: r["name"])


@transaction.atomic
def apply(payroll, employee_ids) -> dict:
    for emp in employee_ids:
        engine.calculate(payroll, employee_id=emp)
    return payroll.totals
