"""Etapa 4 (partea 2): timpul de muncă — calendarul și norma, graficele de lucru, graficul de ture, pontajul, exportul."""
from datetime import date
from decimal import Decimal

import pytest

from apps.leave.models import Absence
from apps.org.models import Occupation, Subdivision
from apps.staff import services as staff
from apps.staff.models import Employee
from apps.worktime import services
from apps.worktime.models import JobSchedule, Roster, ShiftType, Timesheet, WorkSchedule
from .conftest import occupation


@pytest.fixture
def org(seeded):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1")
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția ATI")
    return {"tr1": tr1, "ati": ati,
            "doctor": occupation("Medic traumatolog-ortoped"),
            "anest": occupation("Medic anesteziolog-reanimatolog"),
            "nurse": occupation("Asistent medical de secție")}


def person(org, last="Popescu", first="Ion", sub="tr1", occ="doctor", rate="1", hired=date(2024, 3, 1), **extra):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first)
    job = staff.hire(e, kind=extra.pop("kind", "main"), subdivision=org[sub], occupation=org[occ], rate=Decimal(rate),
                     base_salary=Decimal("14000"), date_from=hired, **extra)
    return e, job


def schedule(code):
    return WorkSchedule.objects.get(code=code)


# --- calendarul și norma ----------------------------------------------------------------------------------------
def test_calendar_norms_with_holidays_and_transferred_day(admin_client, seeded):
    r = admin_client.get("/api/worktime/calendar/", {"year": 2026}).data
    march = r["months"][2]
    assert march["working_days"] == 22 and march["norm_40"] == 176 and march["norm_35"] == 154  # 8 martie e duminică
    may = r["months"][4]
    assert may["working_days"] == 20 and date(2026, 5, 1) in may["holidays"]  # 1, 9 mai; Paștele 12 aprilie
    admin_client.post("/api/worktime/calendar-days/", {"date": "2026-05-02", "working": True, "note": "HG: sâmbătă lucrătoare"},
                      format="json")
    admin_client.post("/api/worktime/calendar-days/", {"date": "2026-04-30", "working": True, "hours_less": "1"}, format="json")
    may = admin_client.get("/api/worktime/calendar/", {"year": 2026}).data["months"][4]
    assert may["working_days"] == 21 and may["norm_40"] == 168
    april = admin_client.get("/api/worktime/calendar/", {"year": 2026}).data["months"][3]
    assert april["norm_40"] == 20 * 8 - 1  # 22 zile − Paștele (13 aprilie) − Blajinii (20 aprilie), ziua scurtată cu o oră


# --- graficele de lucru -----------------------------------------------------------------------------------------
def test_planned_shifts_weekly_half_rate_and_cycle(org):
    _e, job = person(org, rate="0.5")
    JobSchedule.objects.create(employment=job, schedule=schedule("5x8"), date_from=date(2026, 1, 1))
    _n, nurse_job = person(org, "Rusu", "Ana", occ="nurse")
    JobSchedule.objects.create(employment=nurse_job, schedule=schedule("ZN"), date_from=date(2026, 3, 2), cycle_offset=1)
    ctx = services.Context(2026, 3)
    jobs = {jd.job.pk: jd for jd in ctx.jobs(org["tr1"])}
    half = jobs[job.pk]
    assert ctx.planned(half, date(2026, 3, 2)) == "4" and ctx.planned(half, date(2026, 3, 7)) == ""  # luni, sâmbătă
    assert ctx.planned(half, date(2026, 3, 9)) == "4"  # 8 martie e duminică; luni e lucrătoare
    assert ctx.norm(half) == Decimal("88")  # 22 zile × 8 × 0,5
    nurse = jobs[nurse_job.pk]
    # ciclul Z12, N12, liber, liber de la 2 martie, cu decalaj 1: 2 martie = N12
    assert [ctx.planned(nurse, date(2026, 3, d)) for d in (2, 3, 4, 5, 6)] == ["N12", "", "", "Z12", "N12"]
    assert ctx.norm(nurse) == Decimal("176")  # orele graficului (40 h): 22 zile × 8


def test_without_schedule_uses_occupation_hours_and_reduced_day(org):
    org["ati"].reduced_hours = Decimal("30")
    org["ati"].save()
    _e, job = person(org, sub="ati", occ="anest")
    ctx = services.Context(2026, 3)
    jd = ctx.jobs(org["ati"])[0]
    assert ctx.planned(jd, date(2026, 3, 2)) == "6" and ctx.norm(jd) == Decimal("132")


# --- graficul de ture ---------------------------------------------------------------------------------------
def test_roster_fill_warnings_and_approval(admin_client, org, make_user, client_for):
    a, job_a = person(org)
    b, job_b = person(org, "Rusu", "Ana")
    JobSchedule.objects.create(employment=job_b, schedule=schedule("ZN"), date_from=date(2026, 3, 1))
    Absence.objects.create(employee=a, kind="annual", date_from=date(2026, 3, 9), date_to=date(2026, 3, 15), days=7)
    r = admin_client.post("/api/worktime/rosters/", {"subdivision": org["tr1"].id, "year": 2026, "month": 3}, format="json")
    assert r.status_code == 201, r.data
    rid = r.data["id"]
    report = admin_client.get(f"/api/worktime/rosters/{rid}/report/").data
    rows = {row["name"]: row for row in report["rows"]}
    assert rows["Popescu Ion"]["days"]["2"] == "7" and rows["Popescu Ion"]["absences"]["9"] == "C"  # funcția: 35 h → 7 pe zi
    ana = rows["Rusu Ana"]
    assert (ana["days"]["1"], ana["days"]["2"], ana["days"]["5"]) == ("Z12", "N12", "Z12") and "3" not in ana["days"]
    assert ana["nights"] == 8 and ana["hours"] == 192 and ana["norm"] == 176
    assert any(w["kind"] == "norm" and w["name"] == "Rusu A." for w in report["warnings"])
    # ciclul zi – noapte – 2 libere respectă CM art. 101 (odihna = dublul turei): fără avertismente de odihnă
    assert not [w for w in report["warnings"] if w["name"] == "Rusu A." and w["kind"] in ("rest", "consecutive")]
    # noaptea pe 9, ziua pe 10 → două ture la rând; ziua de 7 ore pe 11 → 12 h de odihnă după tura de 12 h (trebuie 24);
    # tură într-o zi de concediu
    line = admin_client.get("/api/worktime/roster-lines/", {"roster": rid}).data
    ion = next(ln for ln in line if ln["employment"] == job_a.id)
    days = {**ion["days"], "9": "N12", "10": "Z12"}
    assert admin_client.patch(f"/api/worktime/roster-lines/{ion['id']}/", {"days": days}, format="json").status_code == 200
    warnings = admin_client.get(f"/api/worktime/rosters/{rid}/report/").data["warnings"]
    mine = {(w["kind"], w.get("day")): w for w in warnings if w["name"] == "Popescu I."}
    assert ("consecutive", 10) in mine and ("absence", 9) in mine
    assert mine[("rest", 11)]["rest"] == 12 and mine[("rest", 11)]["need"] == 24
    assert ("rest", 12) not in mine  # între două zile de 7 ore (cifre, nu ture) — doar minimul din setări (12 h)
    # prea multe ture de noapte (setarea; implicit fără limită)
    admin_client.put("/api/worktime/settings/", {"max_night_shifts": 4}, format="json")
    nights = [w for w in admin_client.get(f"/api/worktime/rosters/{rid}/report/").data["warnings"] if w["kind"] == "nights"]
    assert [(w["name"], w["nights"], w["max"]) for w in nights] == [("Rusu A.", 8, 4)]
    # șeful de secție: își vede graficul, îl transmite, apoi nu-l mai schimbă
    head = make_user("sef", ["department_head"])
    org["tr1"].users.add(head)
    api = client_for(head)
    assert api.get("/api/worktime/rosters/").data["count"] == 1
    assert api.post("/api/worktime/rosters/", {"subdivision": org["ati"].id, "year": 2026, "month": 3}, format="json").status_code == 403
    assert api.post(f"/api/worktime/rosters/{rid}/submit/").status_code == 200
    assert api.patch(f"/api/worktime/roster-lines/{ion['id']}/", {"note": "x"}, format="json").status_code == 400
    assert admin_client.post(f"/api/worktime/rosters/{rid}/approve/").data["status"] == "approved"
    html = admin_client.get(f"/api/worktime/rosters/{rid}/print/").content.decode()
    assert "GRAFICUL DE TURE" in html and "Rusu Ana" in html and "N12" in html and "Gărzi" not in html


# --- tabela de pontaj -------------------------------------------------------------------------------------------
def test_timesheet_from_roster_absences_manual_cells_and_export(admin_client, org):
    a, job_a = person(org)
    b, job_b = person(org, "Rusu", "Ana", occ="nurse")
    JobSchedule.objects.create(employment=job_b, schedule=schedule("ZN"), date_from=date(2026, 3, 2))
    # Ion lucrează și prin cumul la ATI pe 0,25 normă: rând separat, în tabela ATI
    cumul = staff.hire(a, kind="internal", subdivision=org["ati"], occupation=org["anest"], rate=Decimal("0.25"),
                       date_from=date(2026, 1, 1))
    Absence.objects.create(employee=a, kind="sick", date_from=date(2026, 3, 16), date_to=date(2026, 3, 20), days=5)
    Absence.objects.create(employee=b, kind="annual", date_from=date(2026, 3, 23), date_to=date(2026, 3, 29), days=7)
    staff.suspend(job_b, date(2026, 3, 30), "Concediu parțial plătit pentru îngrijirea copilului")
    roster = Roster.objects.create(subdivision=org["tr1"], year=2026, month=3)
    services.fill_roster(roster)
    r = admin_client.post("/api/worktime/timesheets/", {"subdivision": org["tr1"].id, "year": 2026, "month": 3}, format="json")
    assert r.status_code == 201, r.data
    tid = r.data["id"]
    report = admin_client.get(f"/api/worktime/timesheets/{tid}/report/").data
    rows = {row["name"]: row for row in report["rows"]}
    ion, ana = rows["Popescu Ion"], rows["Rusu Ana"]
    assert len(report["rows"]) == 2 and ion["rate"] == 1.0  # cumulul de la ATI nu e aici
    assert ion["days"]["2"] == {"c": "7", "h": 7.0, "n": 0.0} and ion["days"]["16"] == {"c": "Cm"}
    assert ion["days"]["7"] == {"c": "R"} and ion["days"]["8"] == {"c": "Sn"}  # sâmbătă — repaus; 8 martie — sărbătoare
    assert ion["totals"]["days"] == 17 and ion["totals"]["hours"] == 119 and ion["totals"]["norm"] == 154
    assert ion["totals"]["missing"] == 35 and ion["totals"]["codes"] == {"Cm": 5, "R": 8, "Sn": 1}
    assert ana["days"]["3"] == {"c": "N12", "h": 12.0, "n": 8.0} and ana["days"]["23"] == {"c": "C"} and ana["days"]["30"] == {"c": "Sp"}
    assert ana["days"]["4"] == {"c": "R"}  # ziua liberă din ciclul de ture
    assert ana["totals"]["night"] == 8 * 5  # nopțile 3, 7, 11, 15, 19; cele din concediu și după suspendare nu
    # corectare de mână: 31 martie Ion a lipsit nemotivat; 2 martie a lucrat 10 ore
    r = admin_client.post(f"/api/worktime/timesheets/{tid}/set-cell/", {"line": ion["id"], "day": 31, "code": "A"}, format="json")
    assert r.status_code == 200 and r.data["days"]["31"] == {"c": "A", "m": 1}
    r = admin_client.post(f"/api/worktime/timesheets/{tid}/set-cell/", {"line": ion["id"], "day": 2, "hours": "10", "night": "2"},
                          format="json")
    # pe zi (CM art. 157): tura planificată 7 ore, lucrate 10 → 3 ore suplimentare: primele 2 și încă 1, chiar dacă luna e sub normă
    t = r.data["totals"]
    assert r.data["days"]["2"]["h"] == 10 and t["hours"] == 115 and t["overtime"] == 3
    assert (t["overtime_2"], t["overtime_over"], t["overtime_days"]) == (2, 1, {"2": [2, 1]}) and t["regular"] == 112
    admin_client.post(f"/api/worktime/timesheets/{tid}/fill/", format="json")  # recalcularea păstrează celulele de mână
    ion2 = {row["name"]: row for row in admin_client.get(f"/api/worktime/timesheets/{tid}/report/").data["rows"]}["Popescu Ion"]
    assert ion2["days"]["31"]["c"] == "A" and ion2["days"]["2"]["h"] == 10 and ion2["totals"]["codes"] == {"A": 1, "Cm": 5, "R": 8, "Sn": 1}
    # tabela ATI: cumulul lui Ion pe 0,25 (fără grafic lunar: din orele funcției, 35 h × 0,25)
    ati = admin_client.post("/api/worktime/timesheets/", {"subdivision": org["ati"].id, "year": 2026, "month": 3}, format="json").data
    row = admin_client.get(f"/api/worktime/timesheets/{ati['id']}/report/").data["rows"][0]
    assert row["employment"] == cumul.id and row["rate"] == 0.25 and row["days"]["2"]["h"] == 1.75 and row["totals"]["norm"] == 38.5
    # închidere, export
    assert admin_client.post(f"/api/worktime/timesheets/{tid}/close/").data["status"] == "closed"
    assert admin_client.post(f"/api/worktime/timesheets/{tid}/set-cell/", {"line": ion["id"], "day": 3, "code": "A"}, format="json").status_code == 400
    xlsx = admin_client.get("/api/worktime/timesheets/export/", {"year": 2026, "month": 3})
    assert xlsx.status_code == 200 and xlsx["Content-Disposition"].endswith('pontaj-2026-03.xlsx"')
    from io import BytesIO

    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(xlsx.content))
    ws = wb["Pontaj"]
    names = [ws.cell(row=i, column=2).value for i in range(2, ws.max_row + 1)]
    assert names == ["Popescu Ion", "Popescu Ion", "Rusu Ana"]  # întâi ATI (cumulul), apoi traumatologia
    assert wb["Zile"].cell(row=3, column=5 + 30).value == "A"  # ziua 31 a lui Ion la traumatologie
    html = admin_client.get(f"/api/worktime/timesheets/{tid}/print/").content.decode()
    assert "TABELA DE PONTAJ" in html and "Concediu medical" in html and "Rusu Ana" in html
    month = admin_client.get(f"/api/worktime/employee-month/{a.id}/", {"year": 2026, "month": 3}).data
    assert [r["rate"] for r in month["rows"]] == [1.0, 0.25]


def test_shift_and_schedule_dictionaries_validate(admin_client, seeded):
    assert set(ShiftType.objects.values_list("code", flat=True)) == {"8", "7", "6", "Z12", "N12"}  # fără gărzi
    assert not WorkSchedule.objects.filter(code="G24").exists()
    bad = admin_client.post("/api/worktime/shifts/", {"code": "X", "name": "x", "hours": "8", "night_hours": "9"}, format="json")
    assert bad.status_code == 400
    bad = admin_client.post("/api/worktime/schedules/", {"name": "g", "kind": "week", "weekly_hours": "40", "week": ["8", "8"]},
                            format="json")
    assert bad.status_code == 400
    ok = admin_client.post("/api/worktime/schedules/", {"name": "4 zile", "kind": "week", "weekly_hours": "40",
                                                        "week": ["10", "10", "10", "10", "", "", ""]}, format="json")
    assert ok.status_code == 201
    saved = admin_client.put("/api/worktime/settings/", {"min_rest_hours": 11, "max_night_shifts": 8}, format="json").data
    assert saved["max_night_shifts"] == 8 and saved["min_rest_hours"] == 11 and "max_duties" not in saved
    codes = services.CODE_LABELS  # notațiile Convenției colective nr. 17/2020
    assert {"R", "Sn", "Ls", "C", "Cn", "Cs", "Cm", "Cc", "D", "Sp", "Șt", "St", "Dt", "A"} <= set(codes)
