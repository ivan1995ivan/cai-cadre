"""Concediile: graficul anual, cererile (→ ordin), foile de boală (→ absență), concediile sociale și revenirea automată."""
from collections import defaultdict
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.deletion import on_mark
from apps.org import calendar
from apps.staff import services as staff
from apps.staff.models import Employee, Employment, FamilyMember

from . import balance
from .models import (ABSENCE_ORDER, SUSPENDING, WITHOUT_HOLIDAYS, Absence, LeaveRequest, LeaveSchedule, LeaveScheduleLine,
                     SickLeave)

# Concediile sociale (Codul muncii, art. 124, 124¹, 126, 127)
MATERNITY_DAYS = 126  # 70 de zile înainte de naștere + 56 după (140 la complicații — se scrie data de sfârșit)
PATERNITY_DAYS = 14  # în primele 56 de zile după nașterea copilului
CHILDCARE_PAID_YEARS = 3  # concediul parțial plătit — până la vârsta de 3 ani a copilului
CHILDCARE_UNPAID_YEARS = 4  # concediul suplimentar neplătit — de la 3 până la 4 ani


# abonații la cererile de concediu (cabinetul angajatului): "created" / "decided" / "ordered" → [funcție(cerere)]
REQUEST_HOOKS: dict = {"created": [], "decided": [], "ordered": []}


def fire(event: str, req):
    for hook in REQUEST_HOOKS[event]:
        transaction.on_commit(lambda hook=hook: hook(req))


def period(kind: str, start: date, days=None, end=None):
    """(de la, până la, zile): concediile de odihnă — fără sărbători, celelalte — zile calendaristice."""
    skip = kind in WITHOUT_HOLIDAYS
    if end is None:
        if not days or int(days) <= 0:
            raise ValidationError({"days": "Dați data de sfârșit sau numărul de zile."})
        days = int(days)
        end = calendar.leave_end(start, days) if skip else start + timedelta(days=days - 1)
    if end < start:
        raise ValidationError({"date_to": "Sfârșitul este înaintea începutului."})
    return start, end, (calendar.leave_days(start, end) if skip else (end - start).days + 1)


def _years_later(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=28)


def social_dates(kind: str, start=None, child: FamilyMember | None = None) -> dict:
    """Datele concediilor sociale: maternitatea (126 de zile), paternal (14), îngrijirea copilului (până la 3 / 4 ani)."""
    if kind == "maternity":
        if start is None:
            raise ValidationError({"from": "Data din certificatul medical este obligatorie."})
        return {"from": start, "to": start + timedelta(days=MATERNITY_DAYS - 1), "days": MATERNITY_DAYS}
    if kind == "paternity":
        if start is None:
            raise ValidationError({"from": "Data de început este obligatorie."})
        return {"from": start, "to": start + timedelta(days=PATERNITY_DAYS - 1), "days": PATERNITY_DAYS}
    if kind in ("childcare", "childcare_unpaid"):
        if child is None or child.birth_date is None:
            raise ValidationError({"child": "Alegeți copilul (cu data nașterii) din fila „Familia”."})
        if kind == "childcare":
            begin = start or child.birth_date
            end = _years_later(child.birth_date, CHILDCARE_PAID_YEARS) - timedelta(days=1)
        else:
            begin = start or _years_later(child.birth_date, CHILDCARE_PAID_YEARS)
            end = _years_later(child.birth_date, CHILDCARE_UNPAID_YEARS) - timedelta(days=1)
        if end < begin:
            raise ValidationError({"child": "Copilul a depășit vârsta pentru acest concediu."})
        return {"from": begin, "to": end, "days": (end - begin).days + 1}
    raise ValidationError({"kind": "Calculul e doar pentru concediile sociale."})


def overlapping(employee, start, end, exclude_ids=()):
    """Absențele (fără deplasări și perfecționări) care se suprapun cu perioada."""
    return (Absence.objects.filter(employee=employee, date_from__lte=end, date_to__gte=start)
            .exclude(kind__in=("travel", "training")).exclude(pk__in=exclude_ids))


# --- graficul anual ------------------------------------------------------------------------------------------
def schedule_people(schedule: LeaveSchedule):
    """Angajații subdiviziunii (cu sub-subdiviziunile) care lucrează în anul graficului (raport de bază)."""
    ids = schedule.subdivision.descendant_ids()
    first, last = date(schedule.year, 1, 1), date(schedule.year, 12, 31)
    jobs = (Employment.objects.filter(subdivision_id__in=ids, kind__in=balance.MAIN_KINDS, date_from__lte=last)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=first)).exclude(status="ended")
            .select_related("employee", "occupation__category").order_by("occupation__category__sort", "occupation__sort",
                                                                "employee__last_name", "employee__first_name"))
    seen, out = set(), []
    for job in jobs:
        if job.employee_id not in seen:
            seen.add(job.employee_id)
            out.append(job)
    return out


@transaction.atomic
def fill_schedule(schedule: LeaveSchedule) -> int:
    """Adaugă angajații care lipsesc din grafic, cu zilele cuvenite pe anul de muncă din mijlocul anului."""
    have = set(schedule.lines.values_list("employee_id", flat=True))
    calc = balance.Calculator()
    people = [j for j in schedule_people(schedule) if j.employee_id not in have]
    employees = {e.pk: e for e in balance.prefetch(Employee.objects.filter(pk__in=[j.employee_id for j in people]))}
    last = schedule.lines.order_by("-sort").first()
    sort = last.sort if last else 0
    for job in people:
        sort += 10
        days = calc.entitled_in(employees[job.employee_id], date(schedule.year, 7, 1))
        LeaveScheduleLine.objects.create(schedule=schedule, employee_id=job.employee_id, days=days, sort=sort)
    return len(people)


def line_end(line: LeaveScheduleLine):
    if line.date_from and line.days:
        return calendar.leave_end(line.date_from, line.days)
    return None


def _merge_days(days: list) -> list:
    """Zilele consecutive → perioade (de la, până la)."""
    out = []
    for d in sorted(days):
        if out and d == out[-1][1] + timedelta(days=1):
            out[-1] = (out[-1][0], d)
        else:
            out.append((d, d))
    return out


def schedule_report(schedule: LeaveSchedule) -> dict:
    """Rândurile cu funcția, soldul și concediul efectiv (plan / realizat) + avertismentele de suprapunere."""
    lines = list(schedule.lines.select_related("employee").order_by("sort", "id"))
    emp_ids = [ln.employee_id for ln in lines]
    employees = {e.pk: e for e in balance.prefetch(Employee.objects.filter(pk__in=emp_ids))}
    calc = balance.Calculator()
    first, last = date(schedule.year, 1, 1), date(schedule.year, 12, 31)
    actual = defaultdict(list)
    for a in Absence.objects.filter(employee_id__in=emp_ids, kind__in=("annual", "extra"), date_from__lte=last,
                                    date_to__gte=first).order_by("date_from"):
        actual[a.employee_id].append(a)
    today = timezone.localdate()
    rows = []
    for ln in lines:
        emp = employees[ln.employee_id]
        job = calc.job_of(emp)
        occ_id, sub_id = calc.values_on(job, today) if job else (None, None)
        occ = calc.occupations.get(occ_id)
        bal = calc.balance(emp)
        taken = actual.get(ln.employee_id, [])
        if taken:
            state = "taken"
        elif ln.moved_to:
            state = "moved"
        elif ln.date_from and ln.date_from < today:
            state = "missed"
        else:
            state = "planned"
        rows.append({
            "id": ln.id, "employee": ln.employee_id, "name": emp.full_name(), "short_name": emp.short_name(),
            "tab_number": emp.tab_number, "occupation": occ.name_ro if occ else "", "occupation_id": occ_id,
            "category": occ.category.code if occ and occ.category_id else "", "date_from": ln.date_from, "days": ln.days, "date_to": ln.date_to,
            "moved_to": ln.moved_to, "note": ln.note, "sort": ln.sort, "available": bal["available"],
            "remaining": bal["remaining"], "state": state,
            "actual": [{"id": a.id, "from": a.date_from, "to": a.date_to, "days": a.days} for a in taken],
            "other_jobs": [_job_label(j, calc) for j in emp.employments.all()
                           if j.status != "ended" and j.pk != (job.pk if job else None)],
        })
    guests = schedule_guests(schedule, emp_ids)
    return {"rows": rows, "guests": guests, "warnings": schedule_warnings(rows + guests)}


def _job_label(job, calc) -> str:
    occ, sub = calc.occupations.get(job.occupation_id), calc.subdivisions.get(job.subdivision_id)
    rate = f"{(job.rate * 100).normalize():f}%"
    return f"{job.get_kind_display()}: {occ.name_ro if occ else ''}, {sub.name_ro if sub else ''} ({rate})"


def schedule_guests(schedule: LeaveSchedule, have: list) -> list:
    """Cei care lucrează în secție prin cumul / suplinire, cu concediul planificat în graficul secției de bază:
    intră în verificarea suprapunerilor (secția rămâne și fără ei)."""
    ids = schedule.subdivision.descendant_ids()
    first, last = date(schedule.year, 1, 1), date(schedule.year, 12, 31)
    jobs = (Employment.objects.filter(subdivision_id__in=ids, date_from__lte=last)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=first)).exclude(status="ended")
            .exclude(kind__in=(*balance.MAIN_KINDS, "contractor")).exclude(employee_id__in=have)
            .select_related("employee", "occupation__category", "subdivision"))
    plans = defaultdict(list)
    for ln in LeaveScheduleLine.objects.filter(schedule__year=schedule.year, employee_id__in=[j.employee_id for j in jobs])             .exclude(schedule=schedule).select_related("schedule__subdivision"):
        plans[ln.employee_id].append(ln)
    out = []
    for job in jobs:
        for ln in plans.get(job.employee_id, []):
            out.append({"id": f"g{job.pk}-{ln.pk}", "employee": job.employee_id, "name": job.employee.full_name(),
                        "kind": job.get_kind_display(), "rate": float(job.rate), "occupation": job.occupation.name_ro,
                        "occupation_id": job.occupation_id,
                        "category": job.occupation.category.code if job.occupation.category_id else "",
                        "home": ln.schedule.subdivision.name_ro, "date_from": ln.date_from, "days": ln.days,
                        "date_to": ln.date_to, "moved_to": ln.moved_to, "available": ln.days})
    return out


def schedule_warnings(rows: list) -> list:
    """Suprapunerile care lasă secția fără oameni: toți medicii plecați deodată, toți de aceeași funcție (≥ 2)."""
    warnings = []
    absent = defaultdict(set)  # ziua → angajații plecați
    for r in rows:
        start = r["moved_to"] or r["date_from"]
        if not start or not r["days"]:
            continue
        end = r["date_to"] if not r["moved_to"] else calendar.leave_end(start, r["days"])
        day = start
        while end and day <= end:
            absent[day].add(r["employee"])
            day += timedelta(days=1)
        if r["days"] > max(r["available"], 0) + 0.001:
            warnings.append({"kind": "balance", "employee": r["employee"], "name": r["name"], "days": r["days"],
                             "available": r["available"]})
    groups = defaultdict(set)
    for r in rows:
        if r["occupation_id"]:
            groups[("occupation", r["occupation"])].add(r["employee"])
        if r["category"] == "2":  # „specialiștii” (CORM grupa 2), unde au trecut medicii la conversia categoriilor
            groups[("physicians", "")].add(r["employee"])
    doctors = groups.get(("physicians", ""), set())
    for (kind, label), people in groups.items():
        if len(people) < 2 or (kind == "occupation" and people == doctors):
            continue  # toți medicii au aceeași funcție: ajunge avertismentul despre medici
        days = [d for d, who in absent.items() if people <= who]
        for start, end in _merge_days(days):
            warnings.append({"kind": kind, "label": label, "count": len(people), "from": start, "to": end})
    return warnings


@transaction.atomic
def make_schedule_orders(schedule: LeaveSchedule, month: int, user=None):
    """Ciorna ordinului colectiv de concediu pentru cei planificați să plece în luna dată (fără concediu emis încă)."""
    from apps.org.models import OrderType
    from apps.orders import services as order_services
    from apps.orders.models import OrderItem

    ot = OrderType.objects.filter(code="leave_annual", is_active=True).first()
    if ot is None:
        raise ValidationError({"detail": "Tipul de ordin „Concediu de odihnă anual” lipsește din clasificator."})
    calc = balance.Calculator()
    lines = [ln for ln in schedule.lines.select_related("employee").order_by("date_from", "sort")
             if (ln.moved_to or ln.date_from) and (ln.moved_to or ln.date_from).month == month and ln.days]
    taken = set(Absence.objects.filter(employee_id__in=[ln.employee_id for ln in lines], kind="annual",
                                       date_from__year=schedule.year, date_from__month=month)
                .values_list("employee_id", flat=True))
    lines = [ln for ln in lines if ln.employee_id not in taken]
    if not lines:
        raise ValidationError({"detail": "În luna aleasă nu e nimeni de trimis în concediu (sau ordinele sunt deja emise)."})
    order = order_services.new_order(ot, user=user)
    order.basis = f"Graficul concediilor pe anul {schedule.year} ({schedule.subdivision.name_ro})"
    order.save(update_fields=["basis"])
    employees = {e.pk: e for e in balance.prefetch(Employee.objects.filter(pk__in=[ln.employee_id for ln in lines]))}
    for i, ln in enumerate(lines, start=1):
        wy_from, wy_to = calc.suggest_work_year(employees[ln.employee_id])
        params = {"date_from": (ln.moved_to or ln.date_from).isoformat(), "days": ln.days}
        if wy_from:
            params.update({"work_year_from": wy_from.isoformat(), "work_year_to": wy_to.isoformat()})
        item = OrderItem.objects.create(order=order, employee_id=ln.employee_id, params=params, sort=i * 10)
        order_services.refresh_text(item)
        item.save(update_fields=["text"])
    return order


# --- cererile de concediu --------------------------------------------------------------------------------
@transaction.atomic
def make_request_orders(requests: list, user=None) -> list:
    """Ordinele din cererile aprobate: un ordin colectiv pe tip (dacă tipul permite), altfel câte unul."""
    from apps.org.models import OrderType
    from apps.orders import services as order_services
    from apps.orders.models import OrderItem

    by_kind = defaultdict(list)
    for req in requests:
        if req.status not in ("approved", "ordered") or (req.status == "ordered" and req.order_item_id):
            raise ValidationError({"detail": f"Cererea lui {req.employee.short_name()} nu este aprobată."})
        by_kind[req.kind].append(req)
    orders = []
    for kind, group in by_kind.items():
        ot = OrderType.objects.filter(code=ABSENCE_ORDER.get(kind), is_active=True).first()
        if ot is None:
            raise ValidationError({"detail": f"Lipsește tipul de ordin pentru „{group[0].get_kind_display()}”."})
        batches = [group] if ot.collective else [[r] for r in group]
        for batch in batches:
            order = order_services.new_order(ot, user=user)
            order.basis = "Cererile salariaților" if len(batch) > 1 else (
                f"Cererea salariatului din {timezone.localtime(batch[0].created_at):%d.%m.%Y}")
            order.save(update_fields=["basis"])
            for i, req in enumerate(batch, start=1):
                params = {"date_from": req.date_from.isoformat(), "date_to": req.date_to.isoformat(), "days": req.days,
                          "request": req.pk}
                if req.work_year_from:
                    params.update({"work_year_from": req.work_year_from.isoformat(),
                                   "work_year_to": (req.work_year_to or req.work_year_from).isoformat()})
                if req.reason:
                    params["note"] = req.reason
                item = OrderItem.objects.create(order=order, employee=req.employee, params=params, sort=i * 10)
                order_services.refresh_text(item)
                item.save(update_fields=["text"])
                req.status, req.order_item = "ordered", item
                req.save(update_fields=["status", "order_item"])
                fire("ordered", req)
            orders.append(order)
    return orders


# --- foile de boală --------------------------------------------------------------------------------------
@transaction.atomic
def save_sick_leave(sick: SickLeave) -> list:
    """Salvează certificatul și absența lui; întoarce avertismentele (concediul de odihnă se prelungește / amână)."""
    if sick.date_to < sick.date_from:
        raise ValidationError({"date_to": "Sfârșitul este înaintea începutului."})
    sick.days = (sick.date_to - sick.date_from).days + 1
    own = [sick.absence_id] if sick.absence_id else []
    clash = overlapping(sick.employee, sick.date_from, sick.date_to, exclude_ids=own)
    warnings = []
    for other in clash:
        if other.kind == "sick":
            raise ValidationError({"date_from": f"Se suprapune cu alt certificat ({other.date_from:%d.%m.%Y}–{other.date_to:%d.%m.%Y})."})
        if other.kind in ("annual", "extra"):
            warnings.append(f"Angajatul este în concediu de odihnă {other.date_from:%d.%m.%Y}–{other.date_to:%d.%m.%Y}: "
                            "concediul se prelungește sau se amână (Codul muncii, art. 116) — emiteți ordinul de amânare.")
        else:
            warnings.append(f"Perioada se suprapune cu {other.get_kind_display().lower()} "
                            f"{other.date_from:%d.%m.%Y}–{other.date_to:%d.%m.%Y}.")
    if sick.kind == "pregnancy":
        # maternitatea intră în dosar prin ordinul de concediu de maternitate (cu certificatul ca temei)
        if sick.absence_id:
            old = sick.absence
            sick.absence = None
            sick.save()
            old.delete()
        else:
            sick.save()
        return warnings
    job = sick.employee.main_employment()
    absence = sick.absence or Absence(employee=sick.employee, kind="sick")
    absence.employment = job
    absence.date_from, absence.date_to, absence.days = sick.date_from, sick.date_to, sick.days
    absence.note = f"Certificatul {sick.series} {sick.number} — {sick.get_kind_display().lower()}".replace("  ", " ")[:300]
    absence.save()
    sick.absence = absence
    sick.save()
    return warnings


@transaction.atomic
@on_mark(SickLeave)
def _sick_leave_marked(sick: SickLeave, marked: bool):
    if marked:
        absence, sick.absence = sick.absence, None
        sick.save(update_fields=["absence"])
        if absence is not None:
            absence.delete()
    else:
        save_sick_leave(sick)


def delete_sick_leave(sick: SickLeave):
    absence = sick.absence
    sick.delete()
    if absence is not None:
        absence.delete()


# --- revenirea după concediul pentru îngrijirea copilului (sarcina de noapte) -----------------------------
def resume_after_childcare(today=None) -> int:
    """Raporturile suspendate de concediul pentru îngrijirea copilului se reiau a doua zi după sfârșitul lui."""
    today = today or timezone.localdate()
    count = 0
    labels = dict(Absence._meta.get_field("kind").choices)
    for job in Employment.objects.filter(status="suspended").select_related("employee"):
        absences = list(job.absences.filter(kind__in=SUSPENDING).order_by("date_from"))
        if not absences or job.suspension_reason not in {labels[k] for k in SUSPENDING}:
            continue  # suspendat din alt motiv: se reia prin ordin
        last = max(a.date_to for a in absences)  # concediile la rând (parțial plătit, apoi neplătit) — până la ultimul
        if last >= today:
            continue
        staff.resume(job, last + timedelta(days=1), order="", user=None)
        count += 1
    return count
