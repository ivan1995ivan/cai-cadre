"""Termenele sănătății și securității în muncă: cine trebuie trimis la examenul medical periodic (periodicitatea pe funcție /
subdiviziune, HG 1025/2016), cine are instructajul SSM periodic scadent (Legea 186/2008, HG 95/2009); ordinul de trimitere
la examen."""
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import SystemSetting
from apps.staff.models import CIVIL_KINDS, MAIN_KINDS, Employment

from .models import ExamRule, MedicalExam, SafetyBriefing

SETTINGS_KEY = "health_settings"
# exam_months — periodicitatea implicită a examenului periodic, când funcția / subdiviziunea n-are regula ei (ExamRule)
DEFAULTS = {"exam_months": 12, "briefing_months": 6, "horizon_days": 30}


def get_settings() -> dict:
    saved = SystemSetting.read(SETTINGS_KEY, {}) or {}
    return {k: saved.get(k, v) for k, v in DEFAULTS.items()}


def save_settings(data: dict) -> dict:
    cfg = get_settings()
    for k, lo, hi in (("exam_months", 1, 60), ("briefing_months", 1, 24), ("horizon_days", 0, 180)):
        if k in data:
            try:
                cfg[k] = max(lo, min(int(data[k] or 0), hi))
            except (TypeError, ValueError) as exc:
                raise ValidationError({k: "Un număr întreg."}) from exc
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


class ExamPeriods:
    """Periodicitatea examenului periodic pentru un raport de muncă: regulile citite o singură dată."""

    def __init__(self):
        self.default = get_settings()["exam_months"]
        self.rules = list(ExamRule.objects.select_related("subdivision"))
        self._paths = {}

    def _depth(self, subdivision, rule_sub_id):
        """Cât de sus în arbore e subdiviziunea regulii (0 = chiar subdiviziunea raportului); None — nu e strămoș."""
        if subdivision.pk not in self._paths:
            self._paths[subdivision.pk] = [s.pk for s in reversed(subdivision.path())]
        path = self._paths[subdivision.pk]
        return path.index(rule_sub_id) if rule_sub_id in path else None

    def months_for(self, job) -> int:
        best, best_key = None, None
        for r in self.rules:
            if r.occupation_id and r.occupation_id != job.occupation_id:
                continue
            depth = 0
            if r.subdivision_id:
                depth = self._depth(job.subdivision, r.subdivision_id)
                if depth is None:
                    continue
            key = (bool(r.occupation_id), bool(r.subdivision_id), -depth)
            if best_key is None or key > best_key:
                best, best_key = r, key
        return best.months if best else self.default


def main_job_on(employee_id, day):
    """Raportul de muncă al angajatului la data dată (cel de bază, dacă există)."""
    jobs = (Employment.objects.filter(employee_id=employee_id, date_from__lte=day).filter(Q(end_date__isnull=True) | Q(end_date__gte=day))
            .exclude(kind__in=CIVIL_KINDS).select_related("occupation", "subdivision"))
    return min(jobs, key=lambda j: (j.kind not in MAIN_KINDS, j.date_from), default=None)


def fill_next_date(obj):
    """Termenul următor, dacă nu e scris: examenul după periodicitatea funcției / subdiviziunii (0 luni — fără termen),
    instructajul periodic după setări."""
    if obj.next_date:
        return
    if isinstance(obj, MedicalExam):
        job = main_job_on(obj.employee_id, obj.date)
        months = ExamPeriods().months_for(job) if job else get_settings()["exam_months"]
        if months:
            obj.next_date = add_months(obj.date, months)
    elif isinstance(obj, SafetyBriefing) and obj.kind in ("introductory", "initial", "periodic"):
        obj.next_date = add_months(obj.date, get_settings()["briefing_months"])


def staff_on(day, sub_ids=None):
    """Angajații în funcție la data dată: {employee_id: primul raport (cel de bază, dacă există)}."""
    qs = (Employment.objects.filter(date_from__lte=day).filter(Q(end_date__isnull=True) | Q(end_date__gte=day))
          .exclude(kind__in=CIVIL_KINDS).select_related("employee", "subdivision", "occupation__category"))
    if sub_ids is not None:
        qs = qs.filter(subdivision_id__in=sub_ids)
    out = {}
    for job in sorted(qs, key=lambda j: (j.kind not in MAIN_KINDS, j.date_from)):
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
    """Cine are termenul în următoarele zile (sau depășit, sau nu are deloc): examenul medical și instructajul SSM.

    Funcțiile cu periodicitatea 0 (fără examen periodic) nu apar ca „lipsă”; concluzia „inapt temporar / inapt” apare
    mereu, ca angajatul să fie trimis din nou."""
    day = day or timezone.localdate()
    cfg = get_settings()
    until = day + timedelta(days=cfg["horizon_days"] if horizon is None else horizon)
    jobs = staff_on(day, sub_ids)
    rows = []
    if what in (None, "exam"):
        periods = ExamPeriods()
        latest = {}
        for ex in MedicalExam.objects.filter(employee_id__in=jobs, date__lte=day, deletion_mark=False).order_by("date", "id"):
            latest[ex.employee_id] = ex
        for emp_id, job in jobs.items():
            ex = latest.get(emp_id)
            due = ex.next_date if ex else None
            unfit = ex is not None and ex.conclusion in ("temporary", "unfit")
            if ex is None and not periods.months_for(job):
                continue
            if ex is None or (due and due <= until) or unfit:
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
    until = until or timezone.localdate() + timedelta(days=30)
    for i, emp in enumerate(employees, start=1):
        item = OrderItem.objects.create(order=order, employee=emp, params={"date_to": until.isoformat()}, sort=i * 10)
        order_services.refresh_text(item)
        item.save(update_fields=["text"])
    return order
