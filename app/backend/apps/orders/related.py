"""Documentele legate de un ordin (fila „Documente legate” din ordin): rezultatele punctelor lui și sursele."""


def _d(day) -> str:
    return f"{day:%d.%m.%Y}" if day else ""


def _num(v) -> str:
    """Numărul fără zerouri în plus și fără notația științifică (1000, nu 1E+3)."""
    from decimal import Decimal

    return format(Decimal(v or 0).normalize(), "f").replace(".", ",")


def related(order, user) -> dict:
    from apps.leave.models import Absence, LeaveAdjustment, LeaveRequest
    from apps.payroll.models import EmployeePayItem
    from apps.staff.models import FunctionCombination
    from apps.training.models import TrainingRecord as Training
    from apps.worktime.models import JobHourRate

    from .models import Incentive, Order, Sanction

    can = user.has_crm_perm
    items = list(order.items.select_related("employee"))
    ids = [it.pk for it in items]
    made, sources = [], []

    def row(kind, label, employee, detail="", link=""):
        return {"kind": kind, "label": label, "employee": employee.full_name() if employee else "", "detail": detail, "link": link}

    for a in Absence.objects.filter(order_item_id__in=ids).select_related("employee"):
        if a.kind == "sick" and not can("sick_leave.view") or a.kind != "sick" and not can("leave.view"):
            continue
        made.append(row("absence", a.get_kind_display(), a.employee, f"{_d(a.date_from)} – {_d(a.date_to)}"))
    if can("leave.view"):
        for a in LeaveAdjustment.objects.filter(order_item_id__in=ids).select_related("employee"):
            made.append(row("leave_adjustment", f"Corectarea soldului concediilor: {_num(a.days)} zile", a.employee,
                            _d(a.date)))
        for r in LeaveRequest.objects.filter(order_item_id__in=ids).select_related("employee"):
            sources.append(row("leave_request", f"Cererea de concediu: {r.get_kind_display()}", r.employee,
                               f"{_d(r.date_from)} – {_d(r.date_to)}, {r.days} zile"))
    if can("payroll.view"):
        for p in EmployeePayItem.objects.filter(order_item_id__in=ids).select_related("employee", "pay_type"):
            value = f"{_num(p.amount)} lei" if p.amount else f"{_num(p.percent)} %" if p.percent else ""
            made.append(row("pay_item", f"Acumulare planificată: {p.pay_type.name_ro}", p.employee,
                            ", ".join(x for x in (value, f"de la {_d(p.date_from)}", f"până la {_d(p.date_to)}" if p.date_to else "")
                                      if x)))
        for r in JobHourRate.objects.filter(order_item_id__in=ids).select_related("employment__employee", "hour_type"):
            made.append(row("hour_rate", f"Tarif pe tip de ore: {r.hour_type.name_ro}", r.employment.employee,
                            f"{_num(r.rate)} lei / oră, de la {_d(r.date_from)}"))
    if can("employees.view"):
        for c in FunctionCombination.objects.filter(order_item_id__in=ids).select_related("employment__employee", "occupation"):
            made.append(row("combination", f"{c.get_kind_display()}: {c.occupation.name_ro if c.occupation_id else ''}".rstrip(": "),
                            c.employment.employee, f"de la {_d(c.date_from)}" + (f" până la {_d(c.date_to)}" if c.date_to else "")))
    if can("training.view"):
        for t in Training.objects.filter(order_item_id__in=ids).select_related("employee"):
            made.append(row("training", f"Formare: {t.title}", t.employee, _d(t.date_from)))
    for s in Sanction.objects.filter(order_item_id__in=ids).select_related("employee", "kind"):
        made.append(row("sanction", f"Sancțiune: {s.kind.name_ro if s.kind_id else ''}".rstrip(": "), s.employee, _d(s.date)))
    for s in Incentive.objects.filter(order_item_id__in=ids).select_related("employee", "kind"):
        made.append(row("incentive", f"Stimulare: {s.kind.name_ro if s.kind_id else ''}".rstrip(": "), s.employee, _d(s.date)))
    if order.cancelled_by_id:
        c = order.cancelled_by
        made.append(row("cancelled_by", f"Anulat prin ordinul nr. {c.number or '—'} din {_d(c.date)}", None, "", f"/orders/{c.pk}"))
    for o in Order.objects.filter(cancelled_by=order):
        sources.append(row("cancels", f"Anulează ordinul nr. {o.number or '—'} din {_d(o.date)}", None, o.order_type.name_ro,
                           f"/orders/{o.pk}"))
    return {"made": made, "sources": sources}
