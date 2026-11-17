"""Tiparul graficului concediilor de odihnă anuale."""
from django.utils import timezone

from apps.printing.renderer import company_context
from apps.printing.views import print_document

from . import services
from .models import LeaveSchedule


def _d(value):
    return value.strftime("%d.%m.%Y") if value else ""


def schedule_context(request, schedule: LeaveSchedule, lang="ro") -> dict:
    report = services.schedule_report(schedule)
    rows = []
    for n, r in enumerate(report["rows"], start=1):
        actual = "; ".join(f"{_d(a['from'])}–{_d(a['to'])}" for a in r["actual"])
        rows.append({"no": n, "occupation": r["occupation"], "name": r["name"], "tab_number": r["tab_number"], "days": r["days"],
                     "planned": _d(r["date_from"]), "actual": actual, "moved": _d(r["moved_to"]), "note": r["note"]})
    return {
        "company": company_context(request, lang), "lang": lang, "options": {}, "rows": rows,
        "schedule": {"year": schedule.year, "subdivision": schedule.subdivision.name_ro, "status": schedule.get_status_display(),
                     "approved_by": schedule.approved_by, "head_name": schedule.subdivision.head_name},
        "today": _d(timezone.localdate()), "placeholders": {"an": schedule.year},
    }


def print_schedule(request, schedule: LeaveSchedule):
    lang = request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro"
    return print_document(request, "leave_schedule", schedule_context(request, schedule, lang),
                          template_id=request.query_params.get("template"),
                          title=f"Graficul concediilor {schedule.year} — {schedule.subdivision.name_ro}", lang=lang)


def sample(request, lang, options):
    schedule = LeaveSchedule.objects.first()
    if schedule is None:
        raise ValueError("Nu există încă grafice de concedii.")
    return schedule_context(request, schedule, lang)
