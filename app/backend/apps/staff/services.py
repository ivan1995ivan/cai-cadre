"""Dosarul angajatului: numerotarea, raporturile de muncă cu istoric, vechimea, vizibilitatea și ocuparea posturilor.

Toate schimbările raportului de muncă trec pe aici (și ordinele din Etapa 3 le vor chema), ca istoricul să rămână complet.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import CIVIL_KINDS, OCCUPYING_KINDS, Employee, Employment, EmploymentHistory, PriorExperience

SNAPSHOT = ("subdivision_id", "occupation_id", "rate", "base_salary", "allowance_pct", "combination_pct")
SNAPSHOT_FIELDS = ["subdivision", "occupation", "rate", "base_salary", "allowance_pct", "combination_pct"]


# --- numărul de tabel ---------------------------------------------------------------
def next_tab_number() -> str:
    """Următorul număr de tabel: cel mai mare număr întreg folosit + 1 (numerele cu litere se sar)."""
    best = 0
    for value in Employee.objects.values_list("tab_number", flat=True):
        if value and value.isdigit():
            best = max(best, int(value))
    return str(best + 1)


# --- vizibilitatea (șeful de secție vede doar subdiviziunile lui) ---------------------
def visible_subdivision_ids(user, module="employees"):
    """None = toate; altfel id-urile subdiviziunilor: „own” = ale lui, „team” = ale lui cu sub-subdiviziunile."""
    scope = user.data_scope(module)
    if scope == "all":
        return None
    ids = set()
    for sub in user.subdivisions.all():
        ids |= sub.descendant_ids() if scope == "team" else {sub.pk}
    return ids


def scope_employees(qs, user, module="employees"):
    ids = visible_subdivision_ids(user, module)
    if ids is None:
        return qs
    cond = Q(employments__subdivision_id__in=ids) & ~Q(employments__status="ended")
    own = Q(user=user)
    return qs.filter(cond | own).distinct()


def can_see(employee, user, module="employees") -> bool:
    ids = visible_subdivision_ids(user, module)
    if ids is None or employee.user_id == user.pk:
        return True
    return employee.employments.filter(subdivision_id__in=ids).exclude(status="ended").exists()


# --- raporturile de muncă ----------------------------------------------------------------
def _snapshot(emp: Employment, event: str, day, order="", note="", user=None) -> EmploymentHistory:
    return EmploymentHistory.objects.create(
        employment=emp, event=event, date=day, subdivision_id=emp.subdivision_id, occupation_id=emp.occupation_id,
        rate=emp.rate, base_salary=emp.base_salary, allowance_pct=emp.allowance_pct, combination_pct=emp.combination_pct,
        order=order, note=note,
        created_by=user)


def refresh_status(employee: Employee):
    states = set(employee.employments.values_list("status", flat=True))
    if "active" in states:
        status = "active"
    elif "suspended" in states:
        status = "suspended"
    elif states:
        status = "dismissed"
    else:
        status = employee.status if employee.status == "candidate" else "active"
    if status != employee.status:
        employee.status = status
        employee.save(update_fields=["status"])
    return status


def _check_rate(rate):
    if rate is None or Decimal(rate) <= 0 or Decimal(rate) > Decimal("1.5"):
        raise ValidationError({"rate": "Norma este între 0,01 și 1,5 unități."})


@transaction.atomic
def hire(employee: Employee, *, user=None, order="", event="hire", **fields) -> Employment:
    """Raport de muncă nou (angajare, cumul, suplinire) + prima înregistrare în istoric."""
    _check_rate(fields.get("rate", Decimal("1")))
    kind = fields.get("kind", "main")
    if kind in ("main", "main_student") and employee.employments.filter(kind__in=("main", "main_student")).exclude(
            status="ended").exists():
        raise ValidationError({"kind": "Angajatul are deja un raport de muncă de bază activ. Folosiți cumulul intern."})
    if fields.get("date_to") and fields["date_to"] < fields["date_from"]:
        raise ValidationError({"date_to": "Termenul contractului este înaintea datei angajării."})
    emp = Employment.objects.create(employee=employee, hire_order=order, **fields)
    _snapshot(emp, event, emp.date_from, order=order, user=user)
    refresh_status(employee)
    return emp


@transaction.atomic
def change(emp: Employment, day, *, user=None, order="", note="", event="change", **fields) -> Employment:
    """Modificarea raportului din data `day`: funcția, subdiviziunea, norma, salariul, sporurile.

    Schimbarea cu dată în viitor se scrie în istoric și intră în valorile curente la data ei (sarcina de noapte)."""
    if emp.status == "ended":
        raise ValidationError({"detail": "Raportul de muncă a încetat."})
    if day < emp.date_from:
        raise ValidationError({"date": "Data modificării este înaintea angajării."})
    allowed = {"subdivision", "subdivision_id", "occupation", "occupation_id", "rate", "base_salary", "allowance_pct",
               "combination_pct"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValidationError({"detail": f"Câmpuri necunoscute: {', '.join(sorted(unknown))}"})
    if "rate" in fields:
        _check_rate(fields["rate"])
    current = {f: getattr(emp, f) for f in SNAPSHOT}
    for key, value in fields.items():
        setattr(emp, key, value)
    _snapshot(emp, event, day, order=order, note=note, user=user)
    if day > timezone.localdate():  # viitor: valorile curente rămân până la data schimbării
        for key, value in current.items():
            setattr(emp, key, value)
    else:
        emp.save()
    return emp


def values_on(emp: Employment, day) -> dict:
    """Funcția, subdiviziunea, norma și salariul raportului la data dată (din istoric)."""
    rec = emp.history.filter(date__lte=day).order_by("-date", "-id").first()
    if rec is None:
        return {f: getattr(emp, f) for f in SNAPSHOT}
    return {f: getattr(rec, f) for f in SNAPSHOT}


def apply_due_changes(today=None) -> int:
    """Sarcina de noapte: schimbările cu dată în viitor ajunse la termen trec în valorile curente."""
    today = today or timezone.localdate()
    count = 0
    for emp in Employment.objects.exclude(status="ended").prefetch_related("history"):
        vals = values_on(emp, today)
        if any(getattr(emp, f) != v for f, v in vals.items()):
            for f, v in vals.items():
                setattr(emp, f, v)
            emp.save(update_fields=SNAPSHOT_FIELDS)
            count += 1
    return count


@transaction.atomic
def suspend(emp: Employment, day, reason="", *, user=None, order="") -> Employment:
    if emp.status != "active":
        raise ValidationError({"detail": "Doar raportul activ se suspendă."})
    emp.status, emp.suspended_from, emp.suspension_reason = "suspended", day, reason
    emp.save(update_fields=["status", "suspended_from", "suspension_reason"])
    _snapshot(emp, "suspend", day, order=order, note=reason, user=user)
    refresh_status(emp.employee)
    return emp


@transaction.atomic
def resume(emp: Employment, day, *, user=None, order="") -> Employment:
    if emp.status != "suspended":
        raise ValidationError({"detail": "Raportul nu este suspendat."})
    emp.status, emp.suspended_from, emp.suspension_reason = "active", None, ""
    emp.save(update_fields=["status", "suspended_from", "suspension_reason"])
    _snapshot(emp, "resume", day, order=order, user=user)
    refresh_status(emp.employee)
    return emp


@transaction.atomic
def terminate(emp: Employment, day, reason=None, *, user=None, order="", note="") -> Employment:
    if emp.status == "ended":
        raise ValidationError({"detail": "Raportul de muncă a încetat deja."})
    if day < emp.date_from:
        raise ValidationError({"end_date": "Data încetării este înaintea angajării."})
    emp.status, emp.end_date, emp.termination_reason, emp.end_order = "ended", day, reason, order
    emp.save(update_fields=["status", "end_date", "termination_reason", "end_order"])
    _snapshot(emp, "end", day, order=order, note=note, user=user)
    # suplinirile acestui raport încetează odată cu el
    for sub in emp.substituted_by.exclude(status="ended"):
        terminate(sub, day, user=user, order=order, note="Încetarea raportului suplinit")
    refresh_status(emp.employee)
    return emp


# --- vechimea în muncă ------------------------------------------------------------------
def _merge(intervals):
    out = []
    for start, end in sorted(i for i in intervals if i[0] <= i[1]):
        if out and start <= out[-1][1] + timedelta(days=1):
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def _ymd(start: date, end: date):
    """Durata unei perioade inclusiv capetele, în ani / luni / zile calendaristice (ca în carnetul de muncă)."""
    end = end + timedelta(days=1)
    years, months, days = end.year - start.year, end.month - start.month, end.day - start.day
    if days < 0:
        months -= 1
        prev_month_end = end.replace(day=1) - timedelta(days=1)
        days += prev_month_end.day
    if months < 0:
        years -= 1
        months += 12
    return years, months, days


def _sum(periods):
    y = m = d = 0
    for start, end in periods:
        py, pm, pd = _ymd(start, end)
        y, m, d = y + py, m + pm, d + pd
    m += d // 30
    d %= 30
    y += m // 12
    m %= 12
    return {"years": y, "months": m, "days": d, "total_days": sum((e - s).days + 1 for s, e in periods)}


def seniority(employee: Employee, on_date=None) -> dict:
    """Vechimea: totală, în specialitate și în întreprindere (perioadele suprapuse se numără o dată).

    În specialitate — stagiul anterior bifat „în specialitate” și raporturile de muncă de aici (fără prestări servicii)."""
    on_date = on_date or timezone.localdate()
    prior = [p for p in employee.experience.all() if p.date_from <= on_date]
    here = []
    for emp in employee.employments.all():
        if emp.date_from > on_date or emp.kind in CIVIL_KINDS:
            continue
        here.append((emp.date_from, min(emp.end_date or on_date, on_date)))

    def clip(p):
        return (p.date_from, min(p.date_to, on_date))

    total = _merge([clip(p) for p in prior] + here)
    specialty = _merge([clip(p) for p in prior if p.in_specialty] + here)
    return {"on_date": on_date, "total": _sum(total), "specialty": _sum(specialty), "institution": _sum(_merge(here))}


def seniority_text(s: dict, lang="ro") -> str:
    words = {"ro": ("ani", "luni", "zile"), "ru": ("лет", "мес.", "дн."), "en": ("years", "months", "days")}[lang if lang in ("ro", "ru", "en") else "ro"]
    return f"{s['years']} {words[0]} {s['months']} {words[1]} {s['days']} {words[2]}"


# --- ocuparea posturilor din statele de personal (furnizorul pentru apps.org) ------------------
def occupancy_provider(staff_list, on_date):
    out = {}
    qs = (Employment.objects.filter(kind__in=OCCUPYING_KINDS, date_from__lte=on_date)
          .filter(Q(end_date__isnull=True) | Q(end_date__gte=on_date))
          .select_related("employee").prefetch_related("history"))
    for emp in qs:
        vals = values_on(emp, on_date)
        key = (vals["subdivision_id"], vals["occupation_id"])
        cur = out.setdefault(key, {"occupied": Decimal("0"), "temporary": Decimal("0"), "holders": []})
        cur["occupied"] += vals["rate"]
        suspended = emp.status == "suspended" and emp.suspended_from and emp.suspended_from <= on_date
        if suspended:
            cur["temporary"] += vals["rate"]
        cur["holders"].append({"name": emp.employee.short_name(), "units": str(vals["rate"]),
                               "kind": "suspended" if suspended else emp.kind})
    return out
