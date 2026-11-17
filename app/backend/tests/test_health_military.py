"""Etapa 6 (partea 2): sănătatea în muncă (examene, vaccinări, instructaj SSM) și evidența militară."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.alerts import engine
from apps.health.models import MedicalExam, Vaccination
from apps.org.models import DictItem, Occupation, Subdivision
from apps.staff import services as staff
from apps.staff.models import Employee, MilitaryRecord

TODAY = timezone.localdate()


@pytest.fixture
def org(seeded):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1")
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția ATI")
    return {"tr1": tr1, "ati": ati, "doctor": Occupation.objects.get(name_ro="Medic traumatolog-ortoped")}


def person(org, last, first, sub="tr1", hired=None, **extra):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first, **extra)
    staff.hire(e, kind="main", subdivision=org[sub], occupation=org["doctor"], rate=Decimal("1"), base_salary=Decimal("14000"),
               date_from=hired or TODAY - timedelta(days=400))
    return e


def test_exam_next_date_and_due_list(org, admin_client):
    a = person(org, "Popescu", "Ion")
    b = person(org, "Rusu", "Ana")
    c = person(org, "Ceban", "Dan", sub="ati")
    r = admin_client.post("/api/health/exams/", {"employee": a.pk, "date": (TODAY - timedelta(days=350)).isoformat(),
                                                 "conclusion": "fit"}, format="json")
    assert r.status_code == 201, r.data
    exam = MedicalExam.objects.get(pk=r.data["id"])
    assert exam.next_date == date(TODAY.year, TODAY.month, TODAY.day) - timedelta(days=350) + (exam.next_date - exam.date)
    assert (exam.next_date - exam.date).days in (365, 366)
    MedicalExam.objects.create(employee=b, date=TODAY - timedelta(days=10), next_date=TODAY + timedelta(days=355))
    data = admin_client.get("/api/health/due/?what=exam").data
    by = {x["name"]: x["status"] for x in data["rows"]}
    assert by == {"Popescu Ion": "due", "Ceban Dan": "missing"}
    # ordinul de trimitere la examen pentru cei aleși
    made = admin_client.post("/api/health/due/", {"employees": [a.pk, c.pk]}, format="json")
    assert made.status_code == 200, made.data
    order = admin_client.get(f"/api/orders/orders/{made.data['order']}/").data
    assert len(order["items"]) == 2 and "examenul medical" in order["items"][0]["text"]
    html = admin_client.get("/api/health/due/?export=print").content.decode()
    assert "LISTA NOMINALĂ" in html and "Ceban Dan" in html


def test_vaccines_briefings_and_alerts(org, admin_client):
    a = person(org, "Popescu", "Ion")
    hep = DictItem.objects.get(kind="vaccine", code="hepatitis_b")
    flu = DictItem.objects.get(kind="vaccine", code="influenza")
    admin_client.post("/api/health/vaccinations/", {"employee": a.pk, "vaccine": hep.pk, "dose": 3,
                                                    "date": (TODAY - timedelta(days=900)).isoformat()}, format="json")
    r = admin_client.post("/api/health/vaccinations/", {"employee": a.pk, "vaccine": flu.pk,
                                                        "date": (TODAY - timedelta(days=350)).isoformat()}, format="json")
    assert Vaccination.objects.get(pk=r.data["id"]).next_date is not None  # gripa — anual
    b = person(org, "Rusu", "Ana")
    rows = admin_client.get("/api/health/due/?what=vaccine").data["rows"]
    assert {(x["name"], x["label"], x["status"]) for x in rows} == {("Popescu Ion", "Gripa sezonieră", "due"),
                                                                     ("Rusu Ana", "Hepatita virală B", "missing")}
    br = admin_client.post("/api/health/briefings/", {"employee": b.pk, "kind": "periodic",
                                                      "date": (TODAY - timedelta(days=175)).isoformat()}, format="json").data
    assert br["next_date"]
    kinds = {x.kind for x in engine.collect(TODAY, ["medical_exam_due", "briefing_due", "vaccination_due"])}
    assert kinds == {"briefing_due", "vaccination_due"}  # „lipsă” nu umple alertele
    rep = admin_client.get("/api/reports/health_due/").data
    assert {s["label"]: s["value"] for s in rep["summary"]}["Vaccinarea"] == 2


def test_health_needs_permission_and_scope(org, make_user, client_for):
    person(org, "Popescu", "Ion")
    head = make_user("sef", ["department_head"])
    assert client_for(head).get("/api/health/exams/").status_code == 403  # datele de sănătate nu sunt ale șefului


def test_military_register_missing_and_recruits(org, admin_client, make_user, client_for):
    center = DictItem.objects.create(kind="military_center", name_ro="Centrul militar Buiucani")
    a = person(org, "Popescu", "Ion", sex="M", birth_date=date(TODAY.year - 40, 3, 1))
    MilitaryRecord.objects.create(employee=a, status="liable", category="2", composition="medical", center=center)
    young = person(org, "Lungu", "Victor", sex="M", birth_date=date(TODAY.year - 20, 1, 1))
    MilitaryRecord.objects.create(employee=young, status="recruit", center=center)
    person(org, "Ceban", "Dan", sex="M", birth_date=date(TODAY.year - 35, 1, 1))  # fără fișă
    person(org, "Rusu", "Ana", sex="F", birth_date=date(TODAY.year - 30, 1, 1))  # medic, femeie — tot la evidență
    reg = admin_client.get("/api/reports/military_register/").data
    assert {r["name"] for r in reg["rows"]} == {"Popescu Ion", "Lungu Victor"}
    assert {s["label"]: s["value"] for s in reg["summary"]} == {"Rezerviști": 1, "Recruți": 1}
    missing = admin_client.get("/api/reports/military_missing/").data
    assert {r["name"] for r in missing["rows"]} == {"Ceban Dan", "Rusu Ana"}
    rec = admin_client.get("/api/reports/military_recruits/").data
    assert [r["name"] for r in rec["rows"]] == ["Lungu Victor"]
    accountant = make_user("contabil", ["accountant"])
    assert client_for(accountant).get("/api/reports/military_register/").status_code == 403


def test_military_monthly_changes(org, admin_client):
    first = TODAY.replace(day=1)
    a = person(org, "Popescu", "Ion", sex="M", birth_date=date(TODAY.year - 40, 3, 1), hired=first)
    MilitaryRecord.objects.create(employee=a, status="liable")
    b = person(org, "Ceban", "Dan", sex="M", birth_date=date(TODAY.year - 35, 1, 1), hired=TODAY - timedelta(days=900))
    MilitaryRecord.objects.create(employee=b, status="liable")
    person(org, "Rusu", "Ana", hired=first)  # fără evidență militară — nu apare
    r = admin_client.patch(f"/api/staff/employees/{b.pk}/", {"address": "mun. Chișinău, str. Nouă 5"}, format="json")
    assert r.status_code == 200, r.data
    data = admin_client.get(f"/api/reports/military_changes/?year={TODAY.year}&month={TODAY.month}").data
    got = {(x["name"], x["what"]) for x in data["rows"]}
    assert got == {("Popescu Ion", "angajat"), ("Ceban Dan", "schimbarea datelor")}
    assert next(x for x in data["rows"] if x["name"] == "Ceban Dan")["detail"] == "domiciliul"
