"""Calendarul de personal pe lună și planul concediilor pe pagina de start."""
from datetime import date

from apps.leave.models import Absence, LeaveSchedule, LeaveScheduleLine

from .test_staff import hire, make_emp, org  # noqa: F401 — fixtura și ajutoarele comune


def test_month_calendar(admin_client, make_user, client_for, org):  # noqa: F811
    a = make_emp("Albu", "Ana", birth_date=date(1990, 3, 14))
    hire(a, org, probation_until=date(2026, 3, 20), date_to=date(2026, 3, 31))
    Absence.objects.create(employee=a, kind="annual", date_from=date(2026, 2, 25), date_to=date(2026, 3, 5), days=9)
    Absence.objects.create(employee=a, kind="sick", date_from=date(2026, 3, 10), date_to=date(2026, 3, 12), days=3)
    r = admin_client.get("/api/alerts/calendar/", {"month": "2026-03"})
    assert r.status_code == 200, r.data
    by = {e["kind"]: e for e in r.json()["events"]}
    assert by["leave"]["from"] == "2026-03-01" and by["leave"]["to"] == "2026-03-05"  # tăiat la marginea lunii
    assert by["sick"]["from"] == "2026-03-10" and by["birthday"]["from"] == "2026-03-14" and by["birthday"]["title"] == "36 ani"
    assert by["probation"]["from"] == "2026-03-20" and by["contract"]["from"] == "2026-03-31"
    assert {h["date"] for h in r.json()["holidays"]} == {"2026-03-08"}
    assert admin_client.get("/api/alerts/calendar/", {"month": "2026-13"}).status_code == 400
    # fără drepturi — calendar gol (doar sărbătorile)
    nobody = client_for(make_user("nimeni", []))
    got = nobody.get("/api/alerts/calendar/", {"month": "2026-03"}).json()
    assert got["events"] == [] and got["holidays"]


def test_leave_plan_on_dashboard(admin_client, org):  # noqa: F811
    from django.utils import timezone

    today = timezone.localdate()
    a = make_emp("Albu", "Ana")
    hire(a, org)
    sched = LeaveSchedule.objects.create(year=today.year, subdivision=org["tr1"], status="approved")
    LeaveScheduleLine.objects.create(schedule=sched, employee=a, date_from=date(today.year, 1, 10), days=14,
                                     date_to=date(today.year, 1, 23))
    LeaveScheduleLine.objects.create(schedule=sched, employee=a, date_from=date(today.year, 12, 28), days=14,
                                     date_to=date(today.year + 1, 1, 10))
    Absence.objects.create(employee=a, kind="annual", date_from=date(today.year, 1, 10), date_to=date(today.year, 1, 19), days=10)
    plan = admin_client.get("/api/alerts/dashboard/").json()["leave_plan"]
    assert plan["planned"] == 28 and plan["taken"] == 10
    assert plan["planned_to_date"] == (28 if today >= date(today.year, 12, 28) else 14)
