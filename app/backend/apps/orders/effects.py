"""Efectele ordinelor la semnare și întoarcerea lor la anulare.

Fiecare efect primește punctul ordinului (angajatul, raportul de muncă, parametrii) și întoarce `result` — ce a creat
sau schimbat, ca anularea ordinului să poată reveni exact la starea dinainte. Schimbările raportului de muncă trec prin
apps.staff.services (istoricul „din data” rămâne complet).
"""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.leave import balance
from apps.leave.models import (ORDER_ABSENCE, SUSPENDING, WITHOUT_HOLIDAYS, Absence, LeaveAdjustment, LeaveSchedule,
                               LeaveScheduleLine)
from apps.org import calendar
from apps.org.models import DictItem, Occupation, StaffList, Subdivision
from apps.staff import services as staff
from apps.staff.models import Employment, EmploymentHistory, FunctionCombination

from .models import Incentive, Sanction


class EffectError(ValidationError):
    pass


def _err(item, message):
    who = item.employee.full_name() if item.employee_id else f"punctul {item.sort or item.pk}"
    raise EffectError({"detail": f"{who}: {message}"})


def p_date(item, key, required=True):
    raw = (item.params or {}).get(key)
    if not raw:
        if required:
            _err(item, f"lipsește data „{key}”.")
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        _err(item, f"data „{raw}” nu este validă.")


def p_dec(item, key):
    raw = (item.params or {}).get(key)
    if raw in (None, ""):
        return None
    try:
        return Decimal(str(raw).replace(",", "."))
    except InvalidOperation:
        _err(item, f"„{raw}” nu este un număr.")


def p_obj(item, key, model, required=False, **filters):
    raw = (item.params or {}).get(key)
    if not raw:
        if required:
            _err(item, f"lipsește „{key}”.")
        return None
    obj = model.objects.filter(pk=raw, **filters).first()
    if obj is None:
        _err(item, f"„{key}” nu există.")
    return obj


def job_of(item) -> Employment:
    job = item.employment or (p_obj(item, "employment", Employment) if (item.params or {}).get("employment") else None)
    if job is None and item.employee_id:
        job = item.employee.main_employment()
    if job is None:
        _err(item, "angajatul nu are raport de muncă.")
    if job.employee_id != item.employee_id:
        _err(item, "raportul de muncă este al altui angajat.")
    return job


def _last_history(job):
    return job.history.order_by("-id").first()


# --- raporturile de muncă -------------------------------------------------------------------
def hire(item, order, user):
    if not item.employee_id:
        _err(item, "alegeți angajatul.")
    p = item.params or {}
    fields = {
        "kind": p.get("kind") or "main",
        "subdivision": p_obj(item, "subdivision", Subdivision, required=True),
        "occupation": p_obj(item, "occupation", Occupation, required=True),
        "rate": p_dec(item, "rate") or Decimal("1"),
        "base_salary": p_dec(item, "base_salary") or Decimal("0"),
        "allowance_pct": p_dec(item, "allowance_pct") or Decimal("0"),
        "pay_mode": p.get("pay_mode") or "salary",
        "hourly_rate": p_dec(item, "hourly_rate") or Decimal("0"),
        "date_from": p_date(item, "date_from"),
        "date_to": p_date(item, "date_to", required=False),
        "probation_until": p_date(item, "probation_until", required=False),
        "contract_number": p.get("contract_number", ""),
        "contract_date": p_date(item, "contract_date", required=False),
    }
    if p.get("substitutes"):
        fields["substitutes"] = p_obj(item, "substitutes", Employment)
    job = staff.hire(item.employee, user=user, order=order.reference(), **fields)
    item.employment = job
    return {"employment": job.id}


def undo_hire(item, result):
    job = Employment.objects.filter(pk=result.get("employment")).first()
    if job is None:
        return
    if job.history.exclude(event__in=("hire", "import")).exists():
        _err(item, "raportul de muncă are deja alte modificări; anulați întâi ordinele de după angajare.")
    if job.pay_items.exclude(order_item=item).exists():
        _err(item, "raportul de muncă are acumulări / rețineri puse după angajare (fila „Salariu”); scoateți-le sau anulați "
                   "întâi documentele lor.")
    if job.hour_rates.exclude(order_item=item).exists() or job.combinations.exclude(order_item=item).exists():
        _err(item, "raportul de muncă are tarife pe ore sau cumulări puse după angajare; scoateți-le sau anulați întâi ordinele lor.")
    employee = job.employee
    job.delete()
    staff.refresh_status(employee)


def change(item, order, user):
    job = job_of(item)
    fields = {}
    for key, model in (("subdivision", Subdivision), ("occupation", Occupation)):
        obj = p_obj(item, key, model)
        if obj is not None and obj.pk != getattr(job, f"{key}_id"):
            fields[key] = obj
    for key in ("rate", "base_salary", "allowance_pct", "hourly_rate"):
        value = p_dec(item, key)
        if value is not None and value != getattr(job, key):
            fields[key] = value
    mode = (item.params or {}).get("pay_mode")
    if mode and mode != job.pay_mode:
        fields["pay_mode"] = mode
    code = order.order_type.code
    result = {"employment": job.id}
    if code == "extend_contract":
        new_to = p_date(item, "date_to")
        if job.date_to is None:
            _err(item, "contractul este pe durată nedeterminată; nu are ce se prelungi.")
        if new_to <= job.date_to:
            _err(item, "noul termen trebuie să fie după cel actual.")
        result["before_date_to"] = job.date_to.isoformat()
        job.date_to = new_to
        job.save(update_fields=["date_to"])
    elif not fields and code != "change_terms":
        if pay_rows(item, order) or rate_rows(item, order):  # doar acumulările / tarifele — raportul rămâne cum e
            item.employment = job
            return result
        _err(item, "nu se schimbă nimic (funcția, secția, norma și salariul sunt aceleași).")
    day = p_date(item, "date_from", required=code != "extend_contract") or order.date
    result["before"] = {f: str(getattr(job, f)) for f in staff.SNAPSHOT}
    event = "salary" if fields and set(fields) <= {"base_salary", "allowance_pct", "hourly_rate", "pay_mode"} else "change"
    if "pay_mode" in fields:  # tarifele oprite în același ordin se opresc înaintea schimbării modalității
        result["employment"] = job.id
        result["hour_rates"] = apply_hour_rates(item, order, result, actions={"stop"})
    note = (item.params or {}).get("text", "")[:300] if code in ("change_terms", "hours_change") else (
        f"Prelungit până la {job.date_to:%d.%m.%Y}" if code == "extend_contract" else "")
    staff.change(job, day, user=user, order=order.reference(), event=event, note=note, **fields)
    item.employment = job
    result["history"] = _last_history(job).id
    return result


def undo_change(item, result):
    job = Employment.objects.filter(pk=result.get("employment")).first()
    if job is None:
        return
    EmploymentHistory.objects.filter(pk=result.get("history")).delete()
    if result.get("before_date_to"):
        job.date_to = date.fromisoformat(result["before_date_to"])
        job.save(update_fields=["date_to"])
    vals = staff.values_on(job, date.today())
    for key, value in vals.items():
        setattr(job, key, value)
    job.save(update_fields=staff.SNAPSHOT_FIELDS)


COMBINATION_KINDS = {"substitution": "substitution", "combination": "combination", "acting": "acting"}
COMBINATION_PAY = {k for k, _ in FunctionCombination.PAY_MODES}


def substitution(item, order, user):
    """Cumularea funcțiilor, suplinirea, interimatul (grupa „substitution”). Două feluri, după `params.mode`:

    - „on_base” (implicit) — în cadrul aceluiași contract, fără eliberare de la munca de bază (CM art. 156): înregistrarea
      „Cumularea funcțiilor / suplinirea” pe raportul de bază, cu modalitatea plății (% din salariul propriu / al funcției
      cumulate, sumă fixă, pe ore cu tarif), de la / până la; `params.action = "stop"` încheie mai devreme o înregistrare;
    - „separate” — raport de muncă separat (cumul intern sau suplinire cu CIM, normă, salariu, pontaj proprii), pe perioadă
      determinată."""
    if not item.employee_id:
        _err(item, "alegeți angajatul.")
    p = item.params or {}
    code = order.order_type.code
    if (p.get("mode") or "on_base") == "separate":
        return _separate_job(item, order, user)
    base = job_of(item)
    if p.get("action") == "stop":
        rec = p_obj(item, "combination", FunctionCombination, required=True, employment__employee=item.employee)
        end = p_date(item, "date_to")
        if end < rec.date_from:
            _err(item, "data încheierii este înaintea începutului cumulării.")
        if rec.date_to is not None and rec.date_to <= end:
            _err(item, f"cumularea se încheie deja la {rec.date_to:%d.%m.%Y}.")
        before = rec.date_to.isoformat() if rec.date_to else None
        rec.date_to = end
        rec.save(update_fields=["date_to"])
        item.employment = rec.employment
        return {"stopped": rec.pk, "before": before, "stopped_to": end.isoformat(), "employment": rec.employment_id}
    occ = p_obj(item, "occupation", Occupation)
    if occ is None:
        _err(item, "alegeți funcția cumulată / suplinită.")
    pay_mode = p.get("pay_mode") or "pct_own"
    if pay_mode not in COMBINATION_PAY:
        _err(item, f"modalitatea plății „{pay_mode}” nu există.")
    value = p_dec(item, "value")
    if value is None:
        value = p_dec(item, "percent")  # ordinele scrise înainte de S4b: „percent” = % din salariul propriu
    if value is None or value <= 0:
        _err(item, "dați valoarea plății (procentul, suma sau tariful pe oră).")
    if pay_mode in ("pct_own", "pct_other") and value > 200:
        _err(item, "procentul plății este cel mult 200 %.")
    start, end = p_date(item, "date_from"), p_date(item, "date_to", required=False)
    if end and end < start:
        _err(item, "sfârșitul este înaintea începutului.")
    if start < base.date_from or (base.end_date and start > base.end_date):
        _err(item, "cumularea începe în afara raportului de muncă de bază.")
    substitutes = p_obj(item, "substitutes", Employment) if p.get("substitutes") else None
    other = p_dec(item, "other_salary")
    if pay_mode == "pct_other" and other is None:
        other = substitutes.base_salary if substitutes is not None else None
        if not other:
            _err(item, "dați salariul funcției cumulate / suplinite (sau alegeți pe cine suplinește).")
    hour_type = None
    if pay_mode == "hourly":
        from apps.worktime.models import HourType

        hour_type = p_obj(item, "hour_type", HourType, required=True)
    rec = FunctionCombination.objects.create(
        employment=base, kind=COMBINATION_KINDS.get(code, "combination"), occupation=occ,
        subdivision=p_obj(item, "subdivision", Subdivision), substitutes=substitutes,
        substituted_name=str(p.get("substituted_name") or (substitutes.employee.full_name() if substitutes else ""))[:160],
        pay_mode=pay_mode, value=value, other_salary=other if pay_mode == "pct_other" else None, hour_type=hour_type,
        date_from=start, date_to=end, order=order.reference(), order_item=item)
    item.employment = base
    return {"combination": rec.pk, "combination_to": end.isoformat() if end else None, "employment": base.id}


def _separate_job(item, order, user):
    """Raportul de muncă separat (cumul intern / suplinire cu pontaj propriu), pe perioadă determinată."""
    p = item.params or {}
    code = order.order_type.code
    kind = p.get("kind") or ("internal" if code == "combination" else "substitute")
    if kind not in ("internal", "substitute"):
        _err(item, "raportul separat este cumul intern sau suplinire.")
    base = item.employee.main_employment()
    occ = p_obj(item, "occupation", Occupation) or (base.occupation if base else None)
    sub = p_obj(item, "subdivision", Subdivision) or (base.subdivision if base else None)
    if occ is None or sub is None:
        _err(item, "alegeți funcția și subdiviziunea.")
    fields = {"kind": kind, "subdivision": sub, "occupation": occ, "rate": p_dec(item, "rate") or Decimal("0.5"),
              "base_salary": p_dec(item, "base_salary") or (base.base_salary if base else Decimal("0")),
              "pay_mode": p.get("pay_mode") if p.get("pay_mode") in staff.MODES else "salary",
              "hourly_rate": p_dec(item, "hourly_rate") or Decimal("0"),
              "date_from": p_date(item, "date_from"), "date_to": p_date(item, "date_to", required=False)}
    if p.get("substitutes"):
        fields["substitutes"] = p_obj(item, "substitutes", Employment)
    job = staff.hire(item.employee, user=user, order=order.reference(), **fields)
    item.employment = job
    return {"employment": job.id, "separate": True}


def undo_substitution(item, result):
    if result.get("separate") or (result.get("employment") and not result.get("combination") and not result.get("stopped")):
        undo_hire(item, result)
        return
    if result.get("stopped"):
        rec = FunctionCombination.objects.filter(pk=result["stopped"]).first()
        if rec is not None:
            if (rec.date_to.isoformat() if rec.date_to else None) != result.get("stopped_to"):
                _err(item, "cumularea a fost schimbată după acest ordin; anulați întâi ordinul de după.")
            rec.date_to = date.fromisoformat(result["before"]) if result.get("before") else None
            rec.save(update_fields=["date_to"])
        return
    rec = FunctionCombination.objects.filter(pk=result.get("combination")).first()
    if rec is not None:
        if (rec.date_to.isoformat() if rec.date_to else None) != result.get("combination_to"):
            _err(item, f"cumularea a fost încheiată după acest ordin (la {rec.date_to:%d.%m.%Y}); anulați întâi ordinul de după.")
        rec.delete()


def suspend(item, order, user):
    job = job_of(item)
    p = item.params or {}
    reason = p.get("reason") or ""
    if str(reason).isdigit():
        reason = (DictItem.objects.filter(pk=reason).first() or "")
        reason = getattr(reason, "name_ro", "")
    staff.suspend(job, p_date(item, "date_from"), reason, user=user, order=order.reference())
    item.employment = job
    return {"employment": job.id, "history": _last_history(job).id}


def undo_suspend(item, result):
    job = Employment.objects.filter(pk=result.get("employment")).first()
    if job is None or job.status != "suspended":
        return
    job.status, job.suspended_from, job.suspension_reason = "active", None, ""
    job.save(update_fields=["status", "suspended_from", "suspension_reason"])
    EmploymentHistory.objects.filter(pk=result.get("history")).delete()
    staff.refresh_status(job.employee)


def resume(item, order, user):
    job = job_of(item)
    before = {"suspended_from": job.suspended_from.isoformat() if job.suspended_from else None,
              "suspension_reason": job.suspension_reason}
    staff.resume(job, p_date(item, "date_from"), user=user, order=order.reference())
    item.employment = job
    return {"employment": job.id, "history": _last_history(job).id, "before": before}


def undo_resume(item, result):
    job = Employment.objects.filter(pk=result.get("employment")).first()
    if job is None or job.status != "active":
        return
    before = result.get("before") or {}
    job.status = "suspended"
    job.suspended_from = date.fromisoformat(before["suspended_from"]) if before.get("suspended_from") else None
    job.suspension_reason = before.get("suspension_reason", "")
    job.save(update_fields=["status", "suspended_from", "suspension_reason"])
    EmploymentHistory.objects.filter(pk=result.get("history")).delete()
    staff.refresh_status(job.employee)


def terminate(item, order, user):
    job = job_of(item)
    reason = p_obj(item, "reason", DictItem, kind="termination")
    subs = list(job.substituted_by.exclude(status="ended").values_list("id", flat=True))
    day = p_date(item, "date_from")
    staff.terminate(job, day, reason, user=user, order=order.reference())
    item.employment = job
    ended = [job.id, *subs]
    history = list(EmploymentHistory.objects.filter(employment_id__in=ended, event="end").values_list("id", flat=True))
    result = {"employment": job.id, "ended": ended, "history": history, "combinations": job.closed_combinations}
    days = p_dec(item, "compensation_days")
    if days:  # zilele compensate în bani ies din soldul de concediu
        adj = LeaveAdjustment.objects.create(employee=item.employee, kind="compensated", date=day, days=-days,
                                             note=f"Compensare la eliberare, ordinul {order.reference()}", order_item=item,
                                             created_by=user)
        result["adjustment"] = adj.id
    return result


def undo_terminate(item, result):
    for job in Employment.objects.filter(pk__in=result.get("ended", [])):
        job.status, job.end_date, job.termination_reason, job.end_order = "active", None, None, ""
        job.save(update_fields=["status", "end_date", "termination_reason", "end_order"])
    EmploymentHistory.objects.filter(pk__in=result.get("history", [])).delete()
    staff.reopen_combinations(result.get("combinations"))
    LeaveAdjustment.objects.filter(pk=result.get("adjustment")).delete()
    if item.employee_id:
        staff.refresh_status(item.employee)


# --- concedii și deplasări ------------------------------------------------------------------------
def absence_dates(item, kind):
    """Perioada absenței: din „date_from” + „date_to” sau + „days” (zilele se socotesc fără sărbători la concedii)."""
    start = p_date(item, "date_from")
    end = p_date(item, "date_to", required=False)
    days = (item.params or {}).get("days")
    skip_holidays = kind in WITHOUT_HOLIDAYS
    if end is None:
        if not days:
            _err(item, "dați data de sfârșit sau numărul de zile.")
        days = int(days)
        end = calendar.leave_end(start, days) if skip_holidays else start + timedelta(days=days - 1)
    if end < start:
        _err(item, "sfârșitul este înaintea începutului.")
    count = calendar.leave_days(start, end) if skip_holidays else (end - start).days + 1
    return start, end, count


def leave(item, order, user):
    code = order.order_type.code
    kind = ORDER_ABSENCE.get(code)
    if kind is None:
        return {}
    job = job_of(item)
    start, end, days = absence_dates(item, kind)
    overlap = Absence.objects.filter(employee=item.employee, date_from__lte=end, date_to__gte=start).exclude(
        kind__in=("travel", "training")).exclude(order_item=item)
    if kind not in ("travel", "training") and overlap.exists():
        other = overlap.first()
        _err(item, f"perioada se suprapune cu {other.get_kind_display().lower()} {other.date_from:%d.%m.%Y}–{other.date_to:%d.%m.%Y}.")
    p = item.params or {}
    wy_from, wy_to = p_date(item, "work_year_from", required=False), p_date(item, "work_year_to", required=False)
    if kind == "annual" and wy_from is None:  # anul de muncă: cel mai vechi cu zile rămase
        wy_from, wy_to = balance.Calculator(start).suggest_work_year(item.employee)
    absence = Absence.objects.create(
        employee=item.employee, employment=job, kind=kind, date_from=start, date_to=end, days=days,
        work_year_from=wy_from, work_year_to=wy_to,
        destination=p.get("destination", ""), note=p.get("note", "")[:300], order_item=item)
    # textul punctului arată perioada, zilele calculate și anul de muncă
    item.params = {**p, "date_to": end.isoformat(), "days": days}
    if wy_from:
        item.params.update({"work_year_from": wy_from.isoformat(), "work_year_to": (wy_to or wy_from).isoformat()})
    result = {"absence": absence.id}
    if kind in SUSPENDING and job.status == "active":
        staff.suspend(job, start, absence.get_kind_display(), user=user, order=order.reference())
        result["suspend_history"] = _last_history(job).id
        result["employment"] = job.id
    item.employment = job
    return result


def undo_leave(item, result):
    Absence.objects.filter(pk=result.get("absence")).delete()
    if result.get("suspend_history"):
        undo_suspend(item, {"employment": result.get("employment"), "history": result["suspend_history"]})


def leave_recall(item, order, user):
    absence = p_obj(item, "absence", Absence, required=True, employee=item.employee)
    back = p_date(item, "date_from")
    if not absence.date_from < back <= absence.date_to:
        _err(item, "data rechemării trebuie să fie în interiorul concediului.")
    before = {"date_to": absence.date_to.isoformat(), "days": absence.days}
    new_end = back - timedelta(days=1)
    new_days = (calendar.leave_days(absence.date_from, new_end) if absence.kind in WITHOUT_HOLIDAYS
                else (new_end - absence.date_from).days + 1)
    absence.days_returned = absence.days - new_days
    absence.date_to, absence.days, absence.recalled_on = new_end, new_days, back
    absence.save(update_fields=["date_to", "days", "recalled_on", "days_returned"])
    item.params = {**(item.params or {}), "days": absence.days_returned}
    return {"absence": absence.id, "before": before}


def undo_leave_recall(item, result):
    absence = Absence.objects.filter(pk=result.get("absence")).first()
    if absence is None:
        return
    before = result.get("before") or {}
    absence.date_to = date.fromisoformat(before["date_to"])
    absence.days, absence.recalled_on, absence.days_returned = before.get("days", absence.days), None, 0
    absence.save(update_fields=["date_to", "days", "recalled_on", "days_returned"])


def leave_postpone(item, order, user):
    """Amânarea: concediul emis și neînceput se mută la noua dată; în graficul anual rândul se marchează „amânat”."""
    new_start = p_date(item, "date_from")
    result = {}
    absence = p_obj(item, "absence", Absence, employee=item.employee)
    old_start = None
    if absence is not None:
        if absence.date_from <= order.date:
            _err(item, "concediul a început deja; folosiți rechemarea din concediu.")
        old_start = absence.date_from
        days = int(p_dec(item, "days") or absence.days)
        end = calendar.leave_end(new_start, days) if absence.kind in WITHOUT_HOLIDAYS else new_start + timedelta(days=days - 1)
        clash = Absence.objects.filter(employee=item.employee, date_from__lte=end, date_to__gte=new_start).exclude(
            kind__in=("travel", "training")).exclude(pk=absence.pk)
        if clash.exists():
            other = clash.first()
            _err(item, f"noua perioadă se suprapune cu {other.get_kind_display().lower()} "
                       f"{other.date_from:%d.%m.%Y}–{other.date_to:%d.%m.%Y}.")
        result.update({"absence": absence.id, "before": {"date_from": absence.date_from.isoformat(),
                                                         "date_to": absence.date_to.isoformat(), "days": absence.days}})
        absence.date_from, absence.date_to, absence.days = new_start, end, days
        absence.save(update_fields=["date_from", "date_to", "days"])
        item.params = {**(item.params or {}), "date_to": end.isoformat(), "days": days}
    line = (LeaveScheduleLine.objects.filter(employee=item.employee, schedule__year=(old_start or new_start).year,
                                             moved_to__isnull=True)
            .filter(**({"date_from": old_start} if old_start else {})).order_by("date_from").first())
    if line is not None:
        line.moved_to = new_start
        line.save(update_fields=["moved_to"])
        result["line"] = line.id
        old_start = old_start or line.date_from
    if old_start:
        item.params = {**(item.params or {}), "planned_from": old_start.isoformat()}
    return result


def undo_leave_postpone(item, result):
    absence = Absence.objects.filter(pk=result.get("absence")).first()
    before = result.get("before") or {}
    if absence is not None and before:
        absence.date_from, absence.date_to = date.fromisoformat(before["date_from"]), date.fromisoformat(before["date_to"])
        absence.days = before.get("days", absence.days)
        absence.save(update_fields=["date_from", "date_to", "days"])
    LeaveScheduleLine.objects.filter(pk=result.get("line")).update(moved_to=None)


def leave_compensation(item, order, user):
    """Compensarea în bani a concediului nefolosit: zilele ies din sold (pe anul de muncă ales sau pe cel mai vechi)."""
    days = p_dec(item, "days")
    if not days or days <= 0:
        _err(item, "dați numărul de zile compensate.")
    wy_from = p_date(item, "work_year_from", required=False)
    adj = LeaveAdjustment.objects.create(employee=item.employee, kind="compensated", date=order.date, work_year_from=wy_from,
                                         days=-days, note=f"Ordinul {order.reference()}", order_item=item, created_by=user)
    return {"adjustment": adj.id}


def undo_leave_compensation(item, result):
    LeaveAdjustment.objects.filter(pk=result.get("adjustment")).delete()


def leave_schedule(item, order, user):
    """Aprobarea graficului concediilor: graficele alese (sau toate cele ale anului, transmise) devin „aprobate”."""
    p = item.params or {}
    ids = p.get("schedules") or ([p["schedule"]] if p.get("schedule") else [])
    qs = LeaveSchedule.objects.filter(pk__in=ids) if ids else LeaveSchedule.objects.filter(
        year=p.get("year") or order.date.year + (1 if order.date.month >= 10 else 0), status="submitted")
    changed = []
    for sch in qs.exclude(status="approved"):
        changed.append({"id": sch.id, "status": sch.status, "approved_by": sch.approved_by})
        sch.status, sch.approved_by, sch.approved_at = "approved", f"Ordinul nr. {order.reference()}", timezone.now()
        sch.save(update_fields=["status", "approved_by", "approved_at"])
    if not changed:
        _err(item, "nu există grafice de aprobat (transmise de secții).")
    return {"schedules": changed}


def undo_leave_schedule(item, result):
    for prev in result.get("schedules", []):
        LeaveSchedule.objects.filter(pk=prev["id"]).update(status=prev["status"], approved_by=prev["approved_by"],
                                                           approved_at=None)


# --- stimulări, sancțiuni, calificare, state ---------------------------------------------------------
def incentive(item, order, user):
    if not item.employee_id:
        _err(item, "alegeți angajatul.")
    amount, percent = p_dec(item, "amount"), p_dec(item, "percent")
    if amount is None and percent is None:
        _err(item, "dați suma sau procentul.")
    kind_code = "aid" if order.order_type.code == "material_aid" else "bonus"
    obj = Incentive.objects.create(employee=item.employee, kind=DictItem.objects.filter(kind="incentive", code=kind_code).first(),
                                   date=p_date(item, "date_from", required=False) or order.date, amount=amount,
                                   percent=percent, note=(item.params or {}).get("note", "")[:300], order_item=item)
    return {"incentive": obj.id}


def undo_incentive(item, result):
    Incentive.objects.filter(pk=result.get("incentive")).delete()


def sanction(item, order, user):
    if order.order_type.code == "sanction_lift":
        obj = p_obj(item, "sanction_record", Sanction, required=True, employee=item.employee)
        if obj.lifted_on:
            _err(item, "sancțiunea este deja ridicată.")
        obj.lifted_on = p_date(item, "date_from", required=False) or order.date
        obj.save(update_fields=["lifted_on"])
        return {"lifted": obj.id}
    kind = p_obj(item, "sanction", DictItem, required=True, kind="sanction")
    day = p_date(item, "date_from", required=False) or order.date
    obj = Sanction.objects.create(employee=item.employee, kind=kind, date=day, valid_until=day + timedelta(days=365),
                                  misconduct=(item.params or {}).get("misconduct", ""), order_item=item)
    return {"sanction": obj.id}


def undo_sanction(item, result):
    if result.get("lifted"):
        Sanction.objects.filter(pk=result["lifted"]).update(lifted_on=None)
    Sanction.objects.filter(pk=result.get("sanction")).delete()


def qualification(item, order, user):
    """Grupa „formare”: trimiterea la perfecționare → absență de tip „perfecționare”; celelalte — doar în ordin."""
    if order.order_type.code == "training":
        return leave(item, order, user)
    return {}


def undo_qualification(item, result):
    undo_leave(item, result)


def staff_list(item, order, user):
    from apps.org import services as org_services

    sl = p_obj(item, "staff_list", StaffList, required=True)
    if not sl.approved_by:
        sl.approved_by = f"Ordinul nr. {order.reference()}"
        sl.save(update_fields=["approved_by"])
    org_services.approve(sl, user)
    item.params = {**(item.params or {}), "date_from": sl.effective_from.isoformat()}
    return {"staff_list": sl.id}


def undo_staff_list(item, result):
    sl = StaffList.objects.filter(pk=result.get("staff_list")).first()
    if sl and sl.status == "approved":
        sl.status, sl.approved_at = "draft", None
        sl.save(update_fields=["status", "approved_at"])


def nothing(item, order, user):
    return {}


def undo_nothing(item, result):
    return None


EFFECTS = {
    "hire": (hire, undo_hire),
    "change": (change, undo_change),
    "salary": (change, undo_change),
    "substitution": (substitution, undo_substitution),
    "suspend": (suspend, undo_suspend),
    "resume": (resume, undo_resume),
    "terminate": (terminate, undo_terminate),
    "leave": (leave, undo_leave),
    "travel": (leave, undo_leave),
    "leave_recall": (leave_recall, undo_leave_recall),
    "incentive": (incentive, undo_incentive),
    "sanction": (sanction, undo_sanction),
    "qualification": (qualification, undo_qualification),
    "staff_list": (staff_list, undo_staff_list),
    "worktime": (nothing, undo_nothing),
    "none": (nothing, undo_nothing),
}

# tipurile de ordin cu efect propriu, peste efectul grupei (merg și pe bazele create înainte de Etapa 4)
CODE_EFFECTS = {
    "leave_postpone": (leave_postpone, undo_leave_postpone),
    "leave_compensation": (leave_compensation, undo_leave_compensation),
    "leave_schedule": (leave_schedule, undo_leave_schedule),
}


def for_type(order_type):
    return CODE_EFFECTS.get(order_type.code) or EFFECTS.get(order_type.effect, EFFECTS["none"])


# tipurile care nu cer angajat (organizatorice)
NO_EMPLOYEE = {"staff_list", "none", "worktime"}


# --- tabelul „Acumulări și rețineri” (apps.payroll.planned) ---------------------------------------------------------
PAY_ITEM_EFFECTS = {"hire", "change", "salary", "substitution"}  # angajarea, transferul, condițiile, salariul, sporurile, cumulul
PAY_ITEM_CODES = {"deduction"}  # reținerea din salariu (CM art. 148): rândul reținerii


def has_pay_items(order_type) -> bool:
    return order_type.effect in PAY_ITEM_EFFECTS or order_type.code in PAY_ITEM_CODES


def pay_rows(item, order) -> list:
    """Rândurile tabelului din punct (`params.pay_items`); la angajare, dacă tabelul n-a fost atins deloc, — acumulările-tip
    ale funcției."""
    from apps.payroll import planned

    if not has_pay_items(order.order_type):
        return []
    p = item.params or {}
    if "pay_items" in p:
        rows = p.get("pay_items") or []
    elif order.order_type.effect == "hire":
        rows = planned.occupation_defaults(Occupation.objects.filter(pk=p.get("occupation")).first() if p.get("occupation") else None)
    else:
        rows = []
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        _err(item, "tabelul „Acumulări și rețineri” nu este o listă de rânduri.")
    return rows


def apply_pay_items(item, order, result) -> list:
    """La semnare: rândurile tabelului intră în fila „Salariu”, pe raportul de muncă al ordinului (cel nou la angajare / cumul)."""
    from apps.payroll import planned

    rows = pay_rows(item, order)
    if not rows:
        return []
    job = Employment.objects.filter(pk=result.get("employment")).first() if result.get("employment") else None
    job = job or item.employment or job_of(item)
    day = p_date(item, "date_from", required=False) or order.date
    who = item.employee.full_name() if item.employee_id else f"punctul {item.sort}"
    out = [planned.apply(row, employee=item.employee, employment=job, default_from=day, reference=f"Ordinul nr. {order.reference()}",
                         who=f"{who}, rândul {n} din „Acumulări și rețineri”", source={"order_item": item})
           for n, row in enumerate(rows, start=1)]
    if "pay_items" not in (item.params or {}):  # completat din funcție: ordinul păstrează ce s-a aplicat
        item.params = {**(item.params or {}), "pay_items": rows}
    return out


def undo_pay_items(item, result):
    from apps.payroll import planned

    who = item.employee.full_name() if item.employee_id else f"punctul {item.sort}"
    planned.undo(result.get("pay_items"), who)


# --- tabelul „Tarife pe tipuri de ore” (apps.worktime.rates) ----------------------------------------------------------------
HOUR_RATE_EFFECTS = {"hire", "change", "salary", "substitution"}


def has_hour_rates(order_type) -> bool:
    return order_type.effect in HOUR_RATE_EFFECTS


def rate_rows(item, order) -> list:
    """Rândurile tabelului din punct (`params.hour_rates`); la angajare, dacă tabelul n-a fost atins, — tarifele-tip ale
    funcției. La cumulare / suplinire pe același contract nu se pun (plata e în înregistrarea cumulării)."""
    from apps.worktime import rates

    if not has_hour_rates(order.order_type):
        return []
    p = item.params or {}
    if order.order_type.effect == "substitution" and (p.get("mode") or "on_base") != "separate":
        return []
    if "hour_rates" in p:
        rows = p.get("hour_rates") or []
    elif order.order_type.effect == "hire":
        rows = rates.occupation_defaults(Occupation.objects.filter(pk=p.get("occupation")).first() if p.get("occupation") else None)
    else:
        rows = []
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        _err(item, "tabelul „Tarife pe tipuri de ore” nu este o listă de rânduri.")
    return rows


def apply_hour_rates(item, order, result, actions=None) -> list:
    """La semnare: rândurile tabelului intră pe raportul de muncă al ordinului (cel nou la angajare / cumul separat). `actions`
    — doar acțiunile date (oprirea, înaintea schimbării modalității); rândurile aplicate deja nu se aplică a doua oară."""
    from apps.worktime import rates

    rows = rate_rows(item, order)
    if not rows:
        return []
    job = Employment.objects.filter(pk=result.get("employment")).first() if result.get("employment") else None
    job = job or item.employment or job_of(item)
    day = p_date(item, "date_from", required=False) or order.date
    who = item.employee.full_name() if item.employee_id else f"punctul {item.sort}"
    done = set(result.get("hour_rates_done") or [])
    out = []
    for n, row in enumerate(rows, start=1):
        if n in done or (actions is not None and (row.get("action") or "add") not in actions):
            continue
        out.append(rates.apply(row, job=job, default_from=day, reference=f"Ordinul nr. {order.reference()}",
                               who=f"{who}, rândul {n} din „Tarife pe tipuri de ore”", order_item=item))
        done.add(n)
    result["hour_rates_done"] = sorted(done)
    if "hour_rates" not in (item.params or {}):  # completat din funcție: ordinul păstrează ce s-a aplicat
        item.params = {**(item.params or {}), "hour_rates": rows}
    return out


def undo_hour_rates(item, result):
    from apps.worktime import rates

    who = item.employee.full_name() if item.employee_id else f"punctul {item.sort}"
    rates.undo(result.get("hour_rates"), who)
