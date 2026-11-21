"""Sănătatea și securitatea în muncă (examenele cu periodicitatea pe funcție / subdiviziune, instructajul SSM; fără vaccinări)
și evidența militară — modul opțional, oprit implicit."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.alerts import engine
from apps.core.models import Company
from apps.health import services as health
from apps.health.models import ExamRule, MedicalExam
from apps.org.models import DictItem, Occupation, Subdivision
from apps.staff import services as staff
from apps.staff.models import Employee, MilitaryRecord

TODAY = timezone.localdate()


@pytest.fixture
def org(seeded):
    prod = Subdivision.objects.create(code="PROD", name_ro="Secția producție")
    paint = Subdivision.objects.create(code="VOP", name_ro="Atelierul de vopsire", parent=prod)
    office = Subdivision.objects.create(code="ADM", name_ro="Administrația")
    operator = Occupation.objects.create(code="818901", name_ro="Operator la linia de producție")
    accountant = Occupation.objects.create(code="241103", name_ro="Contabil")
    return {"prod": prod, "paint": paint, "office": office, "operator": operator, "accountant": accountant}


def person(org, last, first, sub="prod", occ="operator", hired=None, **extra):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first, **extra)
    staff.hire(e, kind="main", subdivision=org[sub], occupation=org[occ], rate=Decimal("1"), base_salary=Decimal("9000"),
               date_from=hired or TODAY - timedelta(days=400))
    return e


def military(on: bool):
    c = Company.get()
    c.military_enabled = on
    c.save(update_fields=["military_enabled"])


def test_exam_next_date_and_due_list(org, admin_client):
    a = person(org, "Popescu", "Ion")
    b = person(org, "Rusu", "Ana")
    c = person(org, "Ceban", "Dan", sub="office", occ="accountant")
    r = admin_client.post("/api/health/exams/", {"employee": a.pk, "date": (TODAY - timedelta(days=350)).isoformat(),
                                                 "conclusion": "fit"}, format="json")
    assert r.status_code == 201, r.data
    exam = MedicalExam.objects.get(pk=r.data["id"])
    assert exam.next_date == health.add_months(exam.date, 12)  # fără regulă — periodicitatea implicită din setări
    MedicalExam.objects.create(employee=b, date=TODAY - timedelta(days=10), next_date=TODAY + timedelta(days=355))
    data = admin_client.get("/api/health/due/?what=exam").data
    assert {x["name"]: x["status"] for x in data["rows"]} == {"Popescu Ion": "due", "Ceban Dan": "missing"}
    made = admin_client.post("/api/health/due/", {"employees": [a.pk, c.pk]}, format="json")
    assert made.status_code == 200, made.data
    order = admin_client.get(f"/api/orders/orders/{made.data['order']}/").data
    assert len(order["items"]) == 2 and "examenul medical" in order["items"][0]["text"]
    html = admin_client.get("/api/health/due/?export=print").content.decode()
    assert "LISTA NOMINALĂ" in html and "Ceban Dan" in html and "vaccin" not in html.lower()
    assert admin_client.get("/api/health/due/?what=vaccine").status_code == 400
    assert admin_client.get("/api/health/vaccinations/").status_code == 404


def test_exam_periodicity_by_occupation_and_subdivision(org, admin_client):
    painter = person(org, "Popescu", "Ion", sub="paint")
    worker = person(org, "Rusu", "Ana")
    clerk = person(org, "Ceban", "Dan", sub="office", occ="accountant")
    paint_clerk = person(org, "Lungu", "Victor", sub="paint", occ="accountant")
    r = admin_client.post("/api/health/exam-rules/", {"subdivision": org["prod"].pk, "months": 24}, format="json")
    assert r.status_code == 201, r.data
    admin_client.post("/api/health/exam-rules/", {"subdivision": org["paint"].pk, "months": 6, "note": "solvenți organici"}, format="json")
    admin_client.post("/api/health/exam-rules/", {"occupation": org["accountant"].pk, "months": 0}, format="json")
    admin_client.post("/api/health/exam-rules/", {"occupation": org["accountant"].pk, "subdivision": org["paint"].pk, "months": 12},
                      format="json")
    assert admin_client.post("/api/health/exam-rules/", {"months": 12}, format="json").status_code == 400  # nici funcție, nici subdiviziune
    dup = admin_client.post("/api/health/exam-rules/", {"occupation": org["accountant"].pk, "months": 3}, format="json")
    assert dup.status_code == 400
    assert admin_client.post("/api/health/exam-rules/", {"subdivision": org["office"].pk, "months": 99}, format="json").status_code == 400
    assert len(admin_client.get("/api/health/exam-rules/").data) == 4
    day = TODAY - timedelta(days=30)
    months = {}
    for e in (painter, worker, clerk, paint_clerk):
        r = admin_client.post("/api/health/exams/", {"employee": e.pk, "date": day.isoformat()}, format="json")
        assert r.status_code == 201, r.data
        months[e.last_name] = r.data["next_date"]
    assert months == {"Popescu": health.add_months(day, 6).isoformat(),  # subdiviziunea cea mai apropiată
                      "Rusu": health.add_months(day, 24).isoformat(),  # subdiviziunea-părinte
                      "Ceban": None,  # funcția fără examen periodic
                      "Lungu": health.add_months(day, 12).isoformat()}  # funcția + subdiviziunea — cea mai precisă
    # cei fără examen periodic nu apar ca „lipsă”
    MedicalExam.objects.all().delete()
    rows = health.due_rows(TODAY, what="exam")
    assert {r["name"] for r in rows} == {"Popescu Ion", "Rusu Ana", "Lungu Victor"}
    # o concluzie „inapt temporar” apare oricum
    MedicalExam.objects.create(employee=clerk, date=day, conclusion="temporary")
    assert "Ceban Dan" in {r["name"] for r in health.due_rows(TODAY, what="exam")}
    assert ExamRule.objects.count() == 4


def test_briefings_alerts_and_report(org, admin_client):
    a = person(org, "Popescu", "Ion")
    MedicalExam.objects.create(employee=a, date=TODAY - timedelta(days=360), next_date=TODAY + timedelta(days=5))
    b = person(org, "Rusu", "Ana")
    br = admin_client.post("/api/health/briefings/", {"employee": b.pk, "kind": "periodic",
                                                      "date": (TODAY - timedelta(days=175)).isoformat()}, format="json").data
    assert br["next_date"] == health.add_months(TODAY - timedelta(days=175), 6).isoformat()
    assert "vaccination_due" not in engine.KINDS
    kinds = {(x.kind, x.employee) for x in engine.collect(TODAY, ["medical_exam_due", "briefing_due"])}
    assert kinds == {("medical_exam_due", a.pk), ("briefing_due", b.pk)}  # „lipsă” nu umple alertele
    rep = admin_client.get("/api/reports/health_due/").data
    assert {s["label"] for s in rep["summary"]} == {"Examenul medical", "Instructajul SSM"}


def test_health_needs_permission_and_scope(org, make_user, client_for):
    person(org, "Popescu", "Ion")
    head = make_user("sef", ["department_head"])
    assert client_for(head).get("/api/health/exams/").status_code == 403  # datele de sănătate nu sunt ale șefului
    assert client_for(head).get("/api/health/exam-rules/").status_code == 403


def test_military_module_off_by_default(org, admin_user, admin_client, make_user, client_for):
    a = person(org, "Popescu", "Ion", sex="M", birth_date=date(TODAY.year - 40, 3, 1))
    assert Company.get().military_enabled is False
    assert admin_client.get("/api/public/branding/").data["military_enabled"] is False
    assert admin_client.get(f"/api/staff/military/?employee={a.pk}").status_code == 404
    assert admin_client.post("/api/staff/military/", {"employee": a.pk, "status": "liable"}, format="json").status_code == 404
    assert admin_client.get("/api/reports/military_register/").status_code == 403
    catalog = admin_client.get("/api/reports/").data
    assert not [r for r in catalog if r["key"].startswith("military")]
    me = admin_client.get("/api/auth/me/").data
    assert not [p for p in me["permissions"] if p.startswith("military.")]
    html = admin_client.get(f"/api/staff/employees/{a.pk}/print/?doc=employee_card").content.decode()
    assert "Evidența militară" not in html
    # pornit din Constante → Module
    r = admin_client.patch("/api/company/", {"military_enabled": True}, format="json")
    assert r.status_code == 200 and r.data["military_enabled"] is True
    assert admin_client.post("/api/staff/military/", {"employee": a.pk, "status": "liable"}, format="json").status_code == 201
    admin = client_for(type(admin_user).objects.get(pk=admin_user.pk))  # drepturile se citesc din nou la cererea următoare
    assert "military.view" in admin.get("/api/auth/me/").data["permissions"]
    assert admin.get("/api/reports/military_register/").status_code == 200
    assert "Evidența militară" in admin_client.get(f"/api/staff/employees/{a.pk}/print/?doc=employee_card").content.decode()
    inspector = make_user("inspector", ["hr_inspector"])
    assert client_for(inspector).get("/api/reports/military_register/").status_code == 200


def test_military_register_missing_and_recruits(org, admin_client, make_user, client_for):
    military(True)
    center = DictItem.objects.create(kind="military_center", name_ro="Centrul militar Buiucani")
    a = person(org, "Popescu", "Ion", sex="M", birth_date=date(TODAY.year - 40, 3, 1))
    MilitaryRecord.objects.create(employee=a, status="liable", category="2", composition="soldiers", center=center)
    young = person(org, "Lungu", "Victor", sex="M", birth_date=date(TODAY.year - 20, 1, 1))
    MilitaryRecord.objects.create(employee=young, status="recruit", center=center)
    person(org, "Ceban", "Dan", sex="M", birth_date=date(TODAY.year - 35, 1, 1))  # fără fișă
    person(org, "Rusu", "Ana", sex="F", birth_date=date(TODAY.year - 30, 1, 1))  # femeie — fără regula „pregătire medicală”
    reg = admin_client.get("/api/reports/military_register/").data
    assert {r["name"] for r in reg["rows"]} == {"Popescu Ion", "Lungu Victor"}
    assert {s["label"]: s["value"] for s in reg["summary"]} == {"Rezerviști": 1, "Recruți": 1}
    missing = admin_client.get("/api/reports/military_missing/").data
    assert {r["name"] for r in missing["rows"]} == {"Ceban Dan"}
    rec = admin_client.get("/api/reports/military_recruits/").data
    assert [r["name"] for r in rec["rows"]] == ["Lungu Victor"]
    accountant = make_user("contabil", ["accountant"])
    assert client_for(accountant).get("/api/reports/military_register/").status_code == 403


def test_military_monthly_changes(org, admin_client):
    military(True)
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
