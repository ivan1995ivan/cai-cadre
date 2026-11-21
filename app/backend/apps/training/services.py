"""Formarea profesională: certificatele care expiră, planul anual (propus din certificatele care expiră în anul lui)
și ordinul de trimitere la perfecționare."""
from datetime import date, timedelta

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import TrainingPlan, TrainingPlanLine, TrainingRecord


def _same_course(a: TrainingRecord, b: TrainingRecord) -> bool:
    return a.employee_id == b.employee_id and a.title.strip().lower() == b.title.strip().lower()


def expiring(day_from: date, day_to: date, employee_ids=None) -> list:
    """Certificatele cu termenul de valabilitate între cele două date (inclusiv), fără un curs reînnoit după ele:
    același angajat și aceeași denumire, început după data certificatului vechi."""
    qs = TrainingRecord.objects.filter(valid_until__range=(day_from, day_to), deletion_mark=False,
                                       employee__status__in=("active", "suspended")).select_related("employee")
    if employee_ids is not None:
        qs = qs.filter(employee_id__in=employee_ids)
    rows = list(qs.order_by("valid_until", "id"))
    if not rows:
        return []
    later = list(TrainingRecord.objects.filter(employee_id__in={r.employee_id for r in rows}, deletion_mark=False))
    return [r for r in rows if not any(_same_course(r, x) and x.pk != r.pk and x.date_from > r.date_from for x in later)]


# --- planul anual -----------------------------------------------------------------------------------------------------
@transaction.atomic
def fill_plan(plan: TrainingPlan) -> int:
    """Propune câte un rând pentru fiecare certificat care expiră în anul planului (reînnoirea lui), în luna expirării;
    angajații care au deja în plan același curs se sar."""
    if plan.status == "approved":
        raise ValidationError({"detail": "Planul este aprobat."})
    have = {(ln.employee_id, ln.title.strip().lower()) for ln in plan.lines.all()}
    added, sort = 0, (plan.lines.count() + 1) * 10
    for r in expiring(date(plan.year, 1, 1), date(plan.year, 12, 31)):
        key = (r.employee_id, r.title.strip().lower())
        if key in have:
            continue
        have.add(key)
        TrainingPlanLine.objects.create(plan=plan, employee_id=r.employee_id, kind=r.kind, title=r.title, provider=r.provider,
                                        month=r.valid_until.month, hours=r.hours, sort=sort,
                                        note=f"Certificatul expiră la {r.valid_until:%d.%m.%Y}"[:300])
        added += 1
        sort += 10
    return added


def link_record(record: TrainingRecord):
    """Activitatea de formare închide primul rând deschis al angajatului din planul anului ei."""
    line = (TrainingPlanLine.objects.filter(plan__year=record.date_from.year, employee_id=record.employee_id, record__isnull=True)
            .order_by("month", "sort", "id").first())
    if line:
        line.record = record
        line.save(update_fields=["record"])
    return line


def expiry_alerts(today, days, cfg):
    """Alerta „expiră certificatul de formare”: termenul în următoarele zile (sau trecut de cel mult 30 de zile)."""
    from apps.alerts.engine import Alert, _d, _subs

    out = []
    for r in expiring(today - timedelta(days=30), today + timedelta(days=days)):
        emp = r.employee
        expired = r.valid_until < today
        out.append(Alert("training_expiry", f"training:{r.pk}:{r.valid_until}",
                         "A expirat certificatul de formare" if expired else "Expiră certificatul de formare",
                         f"{emp.full_name()} — {r.title}" + (f", certificatul {r.certificate_number}" if r.certificate_number else "")
                         + f", valabil până la {_d(r.valid_until)}", r.valid_until, "warning" if expired else "info",
                         emp.pk, emp.full_name(), _subs(emp), f"/employees/{emp.pk}?tab=education"))
    return out


# --- ordinul de trimitere la perfecționare --------------------------------------------------------------------------------
def training_effect(item, order, user):
    """Ordinul „trimitere la perfecționare”: absența de tip „perfecționare” + activitatea în registrul formării."""
    from apps.orders import effects

    result = effects.qualification(item, order, user)
    p = item.params or {}
    start = effects.p_date(item, "date_from", required=False) or order.date
    end = effects.p_date(item, "date_to", required=False)
    rec = TrainingRecord.objects.create(
        employee=item.employee, kind="course", title=(p.get("purpose") or order.title or "Curs de perfecționare")[:300],
        provider=(p.get("destination") or "")[:250], date_from=start, date_to=end, order_item=item)
    link_record(rec)
    return {**(result or {}), "training_record": rec.id}


def undo_training_effect(item, result):
    from apps.orders import effects

    TrainingRecord.objects.filter(pk=(result or {}).get("training_record")).delete()
    effects.undo_qualification(item, result or {})
