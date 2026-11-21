"""Etapa 5 (partea 2): catalogul de rapoarte — datele, filtrele, vizibilitatea pe secții, Excel și tipar."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.leave.models import Absence
from apps.org.models import DictItem, Occupation, Subdivision
from apps.staff import services as staff
from apps.staff.models import Employee
from .conftest import occupation

TODAY = timezone.localdate()
MONTH_START = TODAY.replace(day=1)


@pytest.fixture
def org(seeded):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1")
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția ATI")
    return {"tr1": tr1, "ati": ati, "doctor": occupation("Medic traumatolog-ortoped")}


def person(org, last, first, sub="tr1", hired=None, kind="main", rate="1", **extra):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first,
                                **{k: extra.pop(k) for k in ("birth_date", "sex") if k in extra})
    job = staff.hire(e, kind=kind, subdivision=org[sub], occupation=org["doctor"], rate=Decimal(rate), base_salary=Decimal("14000"),
                     date_from=hired or TODAY - timedelta(days=400), **extra)
    return e, job


def rows_of(data):
    return [r for r in data["rows"] if "_section" not in r]


def test_catalog_lists_reports_and_links(org, admin_client, make_user, client_for):
    cat = admin_client.get("/api/reports/").data
    keys = {r["key"] for r in cat}
    assert {"movement", "structure", "seniority", "birthdays", "retirements", "vacancies", "leave_period",
            "timesheet_summary", "orders_payroll", "orders_by_type", "munca1"} <= keys
    assert next(r for r in cat if r["key"] == "occupancy")["link"] == "/staff-list/occupancy"
    ru = admin_client.get("/api/reports/?lang=ru").data
    assert next(r for r in ru if r["key"] == "movement")["title"] == "Движение кадров"
    nobody = client_for(make_user("fara", []))
    assert nobody.get("/api/reports/").data == []
    assert nobody.get("/api/reports/structure/").status_code == 403


def test_movement_and_turnover(org, admin_client):
    a, job_a = person(org, "Popescu", "Ion", hired=TODAY - timedelta(days=400))
    person(org, "Rusu", "Ana", sub="ati", hired=MONTH_START)
    c, job_c = person(org, "Ceban", "Dan", hired=TODAY - timedelta(days=900))
    staff.terminate(job_c, MONTH_START, DictItem.objects.filter(kind="termination").first(), order="Nr. 5-p")
    staff.change(job_a, MONTH_START, subdivision=org["ati"], order="Nr. 6-p")
    data = admin_client.get(f"/api/reports/movement/?date_from={MONTH_START}&date_to={TODAY}").data
    sections = [r["_section"] for r in data["rows"] if "_section" in r]
    assert sections == ["Angajați (1)", "Eliberați (1)", "Transferați (1)"]
    moved = next(r for r in rows_of(data) if r["name"] == a.full_name())
    assert "traumatologie" in moved["detail"] and moved["sub"] == "Secția ATI"
    summary = {s["label"]: s["value"] for s in data["summary"]}
    assert summary["Efectivul la începutul perioadei"] == 2 and summary["Efectivul la sfârșitul perioadei"] == 2
    assert summary["Rata fluctuației, %"] == 50.0
    # filtrul pe subdiviziune: în ATI la sfârșit sunt doi (Rusu și Popescu, transferat)
    ati = admin_client.get(f"/api/reports/movement/?date_from={MONTH_START}&date_to={TODAY}&subdivision={org['ati'].pk}").data
    assert {s["label"]: s["value"] for s in ati["summary"]}["Efectivul la sfârșitul perioadei"] == 2


def test_structure_by_sex_age_and_category(org, admin_client):
    a, _ = person(org, "Popescu", "Ion", sex="M", birth_date=date(TODAY.year - 45, 1, 1))
    b, _ = person(org, "Rusu", "Ana", sex="F", birth_date=date(TODAY.year - 28, 1, 1), rate="0.5")
    person(org, "Lungu", "Vera", sex="F", kind="external")  # cumulul extern nu intră în „de bază”
    data = admin_client.get("/api/reports/structure/").data
    by = {(r["label"]): r for r in rows_of(data)}
    assert by["Femei"]["total"] == 1 and by["Bărbați"]["total"] == 1
    assert by["< 30"]["total"] == 1 and by["40–49"]["total"] == 1
    assert by["Specialiști în diverse domenii de activitate"]["total"] == 2
    assert by["Specialiști în diverse domenii de activitate"]["women"] == 1
    assert "Pe categoria de calificare" not in {r["_section"] for r in data["rows"] if "_section" in r}
    assert by["Normă parțială"]["total"] == 1
    every = admin_client.get("/api/reports/structure/?kinds=all").data
    assert {s["label"]: s["value"] for s in every["summary"]}["Total persoane"] == 3
    assert any(r.get("label") == "Cumul extern" for r in rows_of(every))


def test_birthdays_retirements_seniority(org, admin_client):
    soon = TODAY + timedelta(days=3)
    person(org, "Popescu", "Ion", sex="M", birth_date=date(soon.year - 50, soon.month, soon.day))
    person(org, "Rusu", "Ana", sex="F", birth_date=date(TODAY.year + 1 - 63, 6, 1))
    b = admin_client.get(f"/api/reports/birthdays/?date_from={TODAY}&date_to={TODAY + timedelta(days=10)}").data
    assert [(r["name"], r["age"], r["jubilee"]) for r in b["rows"]] == [("Popescu Ion", 50, "Jubileu")]
    r = admin_client.get(f"/api/reports/retirements/?year={TODAY.year + 1}").data
    assert [x["name"] for x in r["rows"]] == ["Rusu Ana"]
    s = admin_client.get("/api/reports/seniority/").data
    assert len(s["rows"]) == 2 and s["rows"][0]["institution"].startswith("1 ani")
    assert "healthcare" not in {c["key"] for c in s["columns"]} and s["rows"][0]["years"] == 1


def test_vacancies(org, admin_client):
    from apps.org.models import StaffList, StaffListLine

    sl = StaffList.objects.create(number="1", effective_from=TODAY - timedelta(days=500), status="approved")
    StaffListLine.objects.create(staff_list=sl, subdivision=org["tr1"], occupation=org["doctor"], units=Decimal("3"))
    person(org, "Popescu", "Ion", sex="F")
    person(org, "Ceban", "Dan", kind="internal", rate="0.5")
    v = admin_client.get("/api/reports/vacancies/").data
    assert v["rows"][0]["vacant"] == 1.5 and v["totals"]["approved"] == 3.0
    assert admin_client.get("/api/reports/medical_staff/").status_code == 400  # raportul MS nr. 17 nu mai există


def test_leave_period_and_department_head_scope(org, admin_client, make_user, client_for):
    a, _ = person(org, "Popescu", "Ion")
    b, _ = person(org, "Rusu", "Ana", sub="ati")
    Absence.objects.create(employee=a, kind="annual", date_from=MONTH_START - timedelta(days=3), date_to=MONTH_START + timedelta(days=4),
                           days=8)
    Absence.objects.create(employee=b, kind="sick", date_from=MONTH_START, date_to=MONTH_START + timedelta(days=1), days=2)
    end = MONTH_START + timedelta(days=27)
    data = admin_client.get(f"/api/reports/leave_period/?date_from={MONTH_START}&date_to={end}").data
    assert {(r["name"], r["inside"]) for r in data["rows"]} == {("Popescu Ion", 5), ("Rusu Ana", 2)}
    assert data["totals"]["inside"] == 7
    only_sick = admin_client.get(f"/api/reports/leave_period/?date_from={MONTH_START}&date_to={end}&absence_kind=sick").data
    assert [r["name"] for r in only_sick["rows"]] == ["Rusu Ana"]
    head = make_user("sef", ["department_head"])
    org["ati"].users.add(head)
    mine = client_for(head).get(f"/api/reports/leave_period/?date_from={MONTH_START}&date_to={end}").data
    assert [r["name"] for r in mine["rows"]] == ["Rusu Ana"]


def test_orders_reports_and_munca1(org, admin_client):
    from .test_orders import make_order, set_params, sign

    a, _ = person(org, "Popescu", "Ion", sex="F", hired=TODAY - timedelta(days=400))
    order = make_order(admin_client, "bonus", [a], date_=MONTH_START.isoformat())
    set_params(admin_client, order, {"amount": "500"})
    sign(admin_client, order)
    pay = admin_client.get(f"/api/reports/orders_payroll/?date_from={MONTH_START}&date_to={TODAY}").data
    assert [r["name"] for r in pay["rows"]] == ["Popescu Ion"] and pay["rows"][0]["text"]
    types = admin_client.get(f"/api/reports/orders_by_type/?date_from={MONTH_START}&date_to={TODAY}").data
    assert types["totals"]["orders"] == 1
    m = admin_client.get(f"/api/reports/munca1/?year={TODAY.year}&month={TODAY.month}").data
    values = {r["code"]: r["value"] for r in m["rows"]}
    assert values["1"] == 1 and values["1.1"] == 1 and values["2"] == 1.0 and values["8"] == 0.0


def test_excel_and_print(org, admin_client, make_user, client_for):
    person(org, "Popescu", "Ion", sex="M")
    r = admin_client.get("/api/reports/structure/?export=xlsx")
    assert r.status_code == 200 and r["Content-Type"].startswith("application/vnd.openxmlformats")
    html = admin_client.get("/api/reports/structure/print/").content.decode()
    assert "Structura personalului" in html and "Pe sexe" in html and "Bărbați" in html
    viewer = make_user("vede", ["department_head"])  # rolul are doar „view” la rapoarte
    assert client_for(viewer).get("/api/reports/structure/?export=xlsx").status_code == 403
    assert admin_client.get("/api/reports/movement/?date_from=2026-05-10&date_to=2026-05-01").status_code == 400
