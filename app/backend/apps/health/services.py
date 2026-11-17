"""Termenele sănătății în muncă: cine trebuie trimis la examen, la instructaj, la vaccinare; ordinul de trimitere la examen."""
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import SystemSetting
from apps.staff.models import CIVIL_KINDS, Employment

from .models import MedicalExam, SafetyBriefing, Vaccination

SETTINGS_KEY = "health_settings"
DEFAULTS = {"exam_months": 12, "briefing_months": 6, "horizon_days": 30}
MEDICAL = {"physicians", "pharmacists", "nurses", "junior"}


def get_settings() -> dict:
    return {**DEFAULTS, **(SystemSetting.read(SETTINGS_KEY, {}) or {})}


def save_settings(data: dict) -> dict:
    cfg = get_settings()
    for k, lo, hi in (("exam_months", 1, 60), ("briefing_months", 1, 24), ("horizon_days", 0, 180)):
        if k in data:
            cfg[k] = max(lo, min(int(data[k] or 0), hi))
    SystemSetting.write(SETTINGS_KEY, cfg)
    return cfg


def add_months(day: date, months: int) -> date:
    y, m = divmod(day.month - 1 + months, 12)
    year, month = day.year + y, m + 1
    for d in (day.day, 30, 29, 28):
        try:
            return date(year, month, min(d, 31))
        except ValueError:
            continue
    return date(year, month, 28)


def fill_next_date(obj):
    """Termenul următor, dacă nu e scris: examenul și instructajul periodic din setări, vaccinul din clasificator."""
    if obj.next_date:
        return
    cfg = get_settings()
    if isinstance(obj, MedicalExam):
        obj.next_date = add_months(obj.date, cfg["exam_months"])
    elif isinstance(obj, SafetyBriefing) and obj.kind in ("introductory", "initial", "periodic"):
        obj.next_date = add_months(obj.date, cfg["briefing_months"])
    elif isinstance(obj, Vaccination) and not obj.refused:
        months = int((obj.vaccine.extra or {}).get("months") or 0)
        if months:
            obj.next_date = add_months(obj.date, months)


def staff_on(day, sub_ids=None):
    """Angajații în funcție la data dată: {employee_id: primul raport (cel de bază, dacă există)}."""
    qs = (Employment.objects.filter(date_from__lte=day).filter(Q(end_date__isnull=True) | Q(end_date__gte=day))
          .exclude(kind__in=CIVIL_KINDS).select_related("employee", "subdivision", "occupation"))
    if sub_ids is not None:
        qs = qs.filter(subdivision_id__in=sub_ids)
    out = {}
    for job in sorted(qs, key=lambda j: (j.kind not in ("main", "main_student", "resident"), j.date_from)):
        out.setdefault(job.employee_id, job)
    return out


def _row(job, what, label, last, due, day, lang, detail=""):
    if last is None:
        status = "missing"
    elif due and due < day:
        status = "overdue"
    else:
        status = "due"
    return {"employee": job.employee_id, "tab": job.employee.tab_number, "name": job.employee.full_name(),
            "subdivision_id": job.subdivision_id, "subdivision": job.subdivision.local_name(lang),
            "occupation": job.occupation.local_name(lang), "what": what, "label": label, "last": last, "due": due,
            "status": status, "detail": detail}


def due_rows(day=None, sub_ids=None, what=None, lang="ro", horizon=None) -> list:
    """Cine are termenul în următoarele zile (sau depășit, sau nu are deloc): examenul, instructajul, vaccinurile obligatorii."""
    from apps.org.models import DictItem

    day = day or timezone.localdate()
    cfg = get_settings()
    until = day + timedelta(days=cfg["horizon_days"] if horizon is None else horizon)
    jobs = staff_on(day, sub_ids)
    rows = []
    if what in (None, "exam"):
        latest = {}
        for ex in MedicalExam.objects.filter(employee_id__in=jobs, date__lte=day, deletion_mark=False).order_by("date", "id"):
            latest[ex.employee_id] = ex
        for emp_id, job in jobs.items():
            ex = latest.get(emp_id)
            due = ex.next_date if ex else None
            if ex is None or (due and due <= until) or ex.conclusion in ("temporary", "unfit"):
                detail = ex.get_conclusion_display() if ex and ex.conclusion != "fit" else ""
                rows.append(_row(job, "exam", "Examenul medical", ex.date if ex else None, due, day, lang, detail))
    if what in (None, "briefing"):
        latest = {}
        for b in SafetyBriefing.objects.filter(employee_id__in=jobs, date__lte=day, deletion_mark=False).order_by("date", "id"):
            if b.next_date or b.employee_id not in latest:
                latest[b.employee_id] = b
        for emp_id, job in jobs.items():
            b = latest.get(emp_id)
            due = b.next_date if b else None
            if b is None or (due and due <= until):
                rows.append(_row(job, "briefing", "Instructajul SSM", b.date if b else None, due, day, lang))
    if what in (None, "vaccine"):
        required = [v for v in DictItem.objects.filter(kind="vaccine", is_active=True) if (v.extra or {}).get("required")]
        doses = {}
        for v in Vaccination.objects.filter(employee_id__in=jobs, date__lte=day, deletion_mark=False).select_related("vaccine").order_by("date", "id"):
            doses[(v.employee_id, v.vaccine_id)] = v
        for emp_id, job in jobs.items():
            if job.occupation.category in MEDICAL:
                for vac in required:
                    if (emp_id, vac.pk) not in doses:
                        rows.append(_row(job, "vaccine", vac.local_name(lang), None, None, day, lang))
        for (emp_id, _vac), v in doses.items():
            if emp_id in jobs and not v.refused and v.next_date and v.next_date <= until:
                rows.append(_row(jobs[emp_id], "vaccine", v.vaccine.local_name(lang), v.date, v.next_date, day, lang,
                                 f"doza {v.dose}"))
    order = {"overdue": 0, "missing": 1, "due": 2}
    rows.sort(key=lambda r: (order[r["status"]], r["due"] or date.max, r["subdivision"], r["name"]))
    return rows


@transaction.atomic
def make_exam_order(employees: list, user=None, until=None):
    """Ordinul „Examenul medical periodic” pentru angajații aleși (un ordin colectiv)."""
    from apps.org.models import OrderType
    from apps.orders import services as order_services
    from apps.orders.models import OrderItem

    ot = OrderType.objects.filter(code="medical_exam", is_active=True).first()
    if ot is None:
        raise ValidationError({"detail": "Lipsește tipul de ordin „Examenul medical periodic”."})
    if not employees:
        raise ValidationError({"detail": "Alegeți angajații."})
    order = order_services.new_order(ot, user=user)
    for i, emp in enumerate(employees, start=1):
        until = until or timezone.localdate() + timedelta(days=30)
        item = OrderItem.objects.create(order=order, employee=emp, params={"date_to": until.isoformat()}, sort=i * 10)
        order_services.refresh_text(item)
        item.save(update_fields=["text"])
    return order
