"""Creditele EMC pe perioada de atestare, calendarul atestării, planul anual și ordinul de conferire a categoriei."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import SystemSetting
from apps.org.models import STAFF_CATEGORY, DictItem
from apps.staff.models import Employment, Qualification

from .models import Attestation, TrainingPlan, TrainingPlanLine, TrainingRecord

SETTINGS_KEY = "training_settings"
MAIN_KINDS = ("main", "main_student", "resident")
# Creditele cerute pe perioada de atestare, pe categorii de personal — după codul din clasificatorul „Categoriile de
# personal” (grupa CORM: 2 — specialiști, 3 — tehnicieni); se schimbă din setări.
DEFAULTS = {"period_years": 5, "warn_months": 12, "credits": {"2": 250, "3": 150}}


def _category_code(occupation) -> str:
    return occupation.category.code if occupation.category_id else ""


def get_settings() -> dict:
    saved = SystemSetting.read(SETTINGS_KEY, {}) or {}
    return {**DEFAULTS, **saved, "credits": {**DEFAULTS["credits"], **(saved.get("credits") or {})}}


def save_settings(data: dict) -> dict:
    cfg = get_settings()
    if "period_years" in data:
        cfg["period_years"] = max(1, min(int(data["period_years"] or 5), 10))
    if "warn_months" in data:
        cfg["warn_months"] = max(1, min(int(data["warn_months"] or 12), 36))
    for k, v in (data.get("credits") or {}).items():
        if DictItem.objects.filter(kind=STAFF_CATEGORY, code=k).exists():
            cfg["credits"][k] = max(0, min(int(v or 0), 2000))
    SystemSetting.write(SETTINGS_KEY, cfg)
    return cfg


def _years_later(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=28)


def current_qualification(quals, day):
    """Categoria în vigoare la data dată: cea mai recentă conferită (fără categoria „none”)."""
    valid = [q for q in quals if q.category_id and q.category.code != "none" and (q.awarded_on is None or q.awarded_on <= day)]
    return max(valid, key=lambda q: (q.awarded_on or date.min, q.id)) if valid else None


def expiry_of(q, period_years: int):
    if q is None:
        return None
    if q.valid_until:
        return q.valid_until
    return _years_later(q.awarded_on, period_years) - timedelta(days=1) if q.awarded_on else None


def staff_on(day, sub_ids=None, category=""):
    """Angajații cu raport de bază în vigoare: {employee_id: raportul}."""
    qs = (Employment.objects.filter(kind__in=MAIN_KINDS, date_from__lte=day)
          .filter(Q(end_date__isnull=True) | Q(end_date__gte=day))
          .select_related("employee", "subdivision", "occupation__category"))
    if sub_ids is not None:
        qs = qs.filter(subdivision_id__in=sub_ids)
    if category and str(category).isdigit():
        qs = qs.filter(occupation__category_id=category)
    out = {}
    for job in qs.order_by("date_from"):
        out.setdefault(job.employee_id, job)
    return out


def credits_rows(day=None, sub_ids=None, category="", lang="ro", with_zero=False) -> list:
    """Creditele EMC acumulate în perioada de atestare curentă, față de cele cerute, pe fiecare angajat."""
    day = day or timezone.localdate()
    cfg = get_settings()
    years = cfg["period_years"]
    jobs = staff_on(day, sub_ids, category)
    quals = defaultdict(list)
    for q in Qualification.objects.filter(employee_id__in=jobs).select_related("category", "specialty"):
        quals[q.employee_id].append(q)
    records = defaultdict(list)
    for r in TrainingRecord.objects.filter(employee_id__in=jobs, date_from__lte=day, deletion_mark=False):
        records[r.employee_id].append(r)
    warn = day + timedelta(days=30 * cfg["warn_months"])
    rows = []
    for emp_id, job in jobs.items():
        cat = _category_code(job.occupation)
        required = Decimal(cfg["credits"].get(cat, 0))
        if not required and not with_zero:
            continue
        q = current_qualification(quals[emp_id], day)
        expiry = expiry_of(q, years)
        start = q.awarded_on if q and q.awarded_on else _years_later(day, -years) + timedelta(days=1)
        start = max(start, _years_later(day, -years) + timedelta(days=1))
        got = sum((r.credits for r in records[emp_id] if (r.date_to or r.date_from) >= start), Decimal("0"))
        elapsed = Decimal((day - start).days + 1) / Decimal(365.25 * years)
        expected = (required * min(elapsed, Decimal(1))).quantize(Decimal("0.1"))
        if required and got >= required:
            status = "done"
        elif expiry and expiry <= warn and got < required:
            status = "risk"
        elif got < expected:
            status = "behind"
        else:
            status = "ok"
        rows.append({
            "employee": emp_id, "tab": job.employee.tab_number, "name": job.employee.full_name(),
            "subdivision_id": job.subdivision_id, "subdivision": job.subdivision.local_name(lang),
            "occupation": job.occupation.local_name(lang), "staff_category": cat,
            "category": q.category.local_name(lang) if q else "", "category_code": q.category.code if q else "",
            "specialty": q.specialty.local_name(lang) if q and q.specialty_id else "", "specialty_id": q.specialty_id if q else None,
            "awarded_on": q.awarded_on if q else None, "expiry": expiry, "period_from": start,
            "credits": float(got), "required": float(required), "expected": float(expected),
            "missing": float(max(required - got, Decimal("0"))), "pct": round(float(got / required * 100), 1) if required else 100.0,
            "status": status,
        })
    rows.sort(key=lambda r: (r["subdivision"], r["name"]))
    return rows


def attestation_due(day=None, months=12, sub_ids=None, category="", lang="ro") -> list:
    """Calendarul atestării: categoriile care expiră în următoarele luni (și cele expirate), cu creditele."""
    day = day or timezone.localdate()
    until = day + timedelta(days=round(30.4 * months))
    open_att = set(Attestation.objects.filter(status__in=("planned", "submitted", "postponed"), deletion_mark=False).values_list("employee_id", flat=True))
    rows = []
    for r in credits_rows(day, sub_ids, category, lang, with_zero=True):
        if r["expiry"] and r["expiry"] <= until:
            rows.append({**r, "expired": r["expiry"] < day, "in_list": r["employee"] in open_att})
    rows.sort(key=lambda r: r["expiry"])
    return rows


@transaction.atomic
def plan_attestations(employee_ids: list, session_date=None) -> list:
    """Pune angajații aleși în lista pentru atestare (confirmarea categoriei actuale, implicit)."""
    from apps.org.models import DictItem

    day = timezone.localdate()
    years = get_settings()["period_years"]
    created = []
    fallback = DictItem.objects.filter(kind="qualification", code="second").first()
    for emp_id in employee_ids:
        if Attestation.objects.filter(employee_id=emp_id, status__in=("planned", "submitted", "postponed"), deletion_mark=False).exists():
            continue
        quals = list(Qualification.objects.filter(employee_id=emp_id).select_related("category"))
        q = current_qualification(quals, day)
        requested = q.category if q else fallback
        if requested is None:
            raise ValidationError({"detail": "Lipsesc categoriile de calificare din clasificator."})
        created.append(Attestation.objects.create(
            employee_id=emp_id, specialty_id=q.specialty_id if q else None, current_category=q.category if q else None,
            due_date=expiry_of(q, years), requested_category=requested, session_date=session_date))
    return created


@transaction.atomic
def make_award_orders(attestations: list, user=None) -> list:
    """Ordinul de conferire / confirmare a categoriei pentru atestările cu rezultat pozitiv (un ordin colectiv)."""
    from apps.org.models import OrderType
    from apps.orders import services as order_services
    from apps.orders.models import OrderItem

    ot = OrderType.objects.filter(code="category_award", is_active=True).first()
    if ot is None:
        raise ValidationError({"detail": "Lipsește tipul de ordin „Conferirea categoriei de calificare”."})
    todo = []
    for att in attestations:
        if att.status not in Attestation.POSITIVE or not att.result_category_id or not att.result_date:
            raise ValidationError({"detail": f"{att.employee.full_name()}: lipsește rezultatul pozitiv (categoria și data)."})
        if att.order_item_id:
            raise ValidationError({"detail": f"{att.employee.full_name()}: ordinul este deja făcut."})
        todo.append(att)
    batches = [todo] if ot.collective else [[a] for a in todo]
    orders = []
    years = get_settings()["period_years"]
    for batch in batches:
        if not batch:
            continue
        order = order_services.new_order(ot, user=user)
        order.basis = "Decizia comisiei de atestare" + (f" nr. {batch[0].decision}" if len(batch) == 1 and batch[0].decision else "")
        order.save(update_fields=["basis"])
        for i, att in enumerate(batch, start=1):
            params = {"category": att.result_category_id, "date_from": att.result_date.isoformat(),
                      "date_to": (_years_later(att.result_date, years) - timedelta(days=1)).isoformat()}
            if att.specialty_id:
                params["specialty"] = att.specialty_id
            item = OrderItem.objects.create(order=order, employee=att.employee, params=params, sort=i * 10)
            order_services.refresh_text(item)
            item.save(update_fields=["text"])
            att.order_item = item
            att.save(update_fields=["order_item"])
        orders.append(order)
    return orders


# --- planul anual -----------------------------------------------------------------------------------------------------
@transaction.atomic
def fill_plan(plan: TrainingPlan, only_behind=True) -> int:
    """Propune câte un rând pe angajat: creditele unui an (cerute / perioadă) sau cele lipsă, dacă atestarea e în anul planului."""
    if plan.status == "approved":
        raise ValidationError({"detail": "Planul este aprobat."})
    cfg = get_settings()
    day = date(plan.year, 1, 1) if plan.year > timezone.localdate().year else timezone.localdate()
    have = set(plan.lines.values_list("employee_id", flat=True))
    year_end = date(plan.year, 12, 31)
    added, sort = 0, (plan.lines.count() + 1) * 10
    for r in credits_rows(day):
        if r["employee"] in have or not r["required"]:
            continue
        if only_behind and r["status"] in ("ok", "done"):
            continue
        yearly = Decimal(str(r["required"])) / cfg["period_years"]
        due_this_year = r["expiry"] and r["expiry"] <= year_end
        credits = Decimal(str(r["missing"])) if due_this_year else min(Decimal(str(r["missing"])), yearly)
        if credits <= 0:
            continue
        TrainingPlanLine.objects.create(plan=plan, employee_id=r["employee"], title="Curs de perfecționare (EMC)",
                                        credits=credits.quantize(Decimal("0.1")), sort=sort,
                                        note="Atestarea în anul planului" if due_this_year else "")
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


# --- ordinul de trimitere la perfecționare --------------------------------------------------------------------------------
def training_effect(item, order, user):
    """Ordinul „trimitere la perfecționare”: absența de tip „perfecționare” (ca până acum) + activitatea în registrul EMC."""
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
