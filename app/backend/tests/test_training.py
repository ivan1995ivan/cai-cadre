"""Formarea profesională: registrul cursurilor cu certificatul și termenul lui, alerta și raportul certificatelor care
expiră, planul anual propus din ele, ordinul de trimitere la perfecționare; fără EMC și fără atestare."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.alerts import engine
from apps.leave.models import Absence
from apps.org.models import Occupation, Subdivision
from apps.staff import services as staff
from apps.staff.models import Employee
from apps.training import services
from apps.training.models import KINDS, TrainingRecord

TODAY = timezone.localdate()


@pytest.fixture
def org(seeded):
    prod = Subdivision.objects.create(code="PROD", name_ro="Secția producție")
    it = Subdivision.objects.create(code="IT", name_ro="Departamentul IT")
    operator = Occupation.objects.create(code="818901", name_ro="Operator la linia de producție")
    return {"prod": prod, "it": it, "operator": operator}


def person(org, last, first, sub="prod"):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first)
    staff.hire(e, kind="main", subdivision=org[sub], occupation=org["operator"], rate=Decimal("1"), base_salary=Decimal("9000"),
               date_from=TODAY - timedelta(days=3000))
    return e


def test_record_without_credits_with_validity(org, admin_client):
    a = person(org, "Popescu", "Ion")
    body = {"employee": a.pk, "title": "Operarea stivuitorului", "kind": "course", "date_from": (TODAY - timedelta(days=100)).isoformat(),
            "hours": 24, "certificate_number": "S-17", "valid_until": (TODAY + timedelta(days=20)).isoformat()}
    r = admin_client.post("/api/training/records/", body, format="json")
    assert r.status_code == 201, r.data
    assert "credits" not in r.data and r.data["valid_until"] == body["valid_until"]
    bad = admin_client.post("/api/training/records/", {**body, "valid_until": (TODAY - timedelta(days=200)).isoformat()}, format="json")
    assert bad.status_code == 400 and "valid_until" in bad.data
    assert "publication" not in dict(KINDS) and "internal" in dict(KINDS)
    summary = admin_client.get("/api/training/records/summary/").data
    assert summary == {"hours": 24.0, "people": 1}
    # EMC și atestarea nu mai există
    for url in ("/api/training/credits/", "/api/training/attestation-due/", "/api/training/attestations/", "/api/training/settings/"):
        assert admin_client.get(url).status_code == 404, url
    assert admin_client.get("/api/reports/emc_credits/").status_code == 400
    assert "credits_missing" not in engine.KINDS


def test_expiring_certificates_alert_and_report(org, admin_client):
    a = person(org, "Popescu", "Ion")
    b = person(org, "Rusu", "Ana", sub="it")
    c = person(org, "Ceban", "Dan")
    TrainingRecord.objects.create(employee=a, title="Lucrul la înălțime", date_from=TODAY - timedelta(days=700),
                                  valid_until=TODAY + timedelta(days=10), certificate_number="H-1")
    old = TrainingRecord.objects.create(employee=b, title="Lucrul la înălțime", date_from=TODAY - timedelta(days=700),
                                        valid_until=TODAY + timedelta(days=15))
    TrainingRecord.objects.create(employee=b, title="lucrul la înălțime ", date_from=TODAY - timedelta(days=5),
                                  valid_until=TODAY + timedelta(days=700))  # reînnoit: cel vechi nu mai alertează
    TrainingRecord.objects.create(employee=c, title="Prim ajutor", date_from=TODAY - timedelta(days=400),
                                  valid_until=TODAY + timedelta(days=200))  # departe
    TrainingRecord.objects.create(employee=c, title="Curs fără termen", date_from=TODAY - timedelta(days=40))
    alerts = engine.collect(TODAY, ["training_expiry"])
    assert [(x.employee, x.due) for x in alerts] == [(a.pk, TODAY + timedelta(days=10))]
    assert "H-1" in alerts[0].text and alerts[0].level == "info"
    expired = engine.collect(TODAY + timedelta(days=12), ["training_expiry"])
    assert expired[0].level == "warning" and expired[0].title.startswith("A expirat")
    rep = admin_client.get(f"/api/reports/training_expiry/?date_from={TODAY}&date_to={TODAY + timedelta(days=60)}").data
    assert [r["name"] for r in rep["rows"]] == ["Popescu Ion"]
    assert old.pk not in [r.pk for r in services.expiring(TODAY, TODAY + timedelta(days=60))]
    listed = admin_client.get(f"/api/training/records/?valid_until={TODAY + timedelta(days=30)}").data["results"]
    assert {r["employee_name"] for r in listed} == {"Popescu Ion", "Rusu Ana"}


def test_plan_from_expiring_and_training_order(org, admin_client):
    from .test_orders import cancel, make_order, set_params, sign

    a = person(org, "Popescu", "Ion")
    year = TODAY.year
    TrainingRecord.objects.create(employee=a, kind="course", title="Securitatea la incendiu", provider="Centrul de instruire",
                                  date_from=date(year - 3, 5, 1), valid_until=date(year, 11, 30), hours=16)
    plan = admin_client.post("/api/training/plans/", {"year": year, "number": "1"}, format="json").data
    assert admin_client.post(f"/api/training/plans/{plan['id']}/fill/").data["added"] == 1
    assert admin_client.post(f"/api/training/plans/{plan['id']}/fill/").data["added"] == 0  # al doilea clic nu dublează
    lines = admin_client.get(f"/api/training/plan-lines/?plan={plan['id']}").data
    assert len(lines) == 1 and lines[0]["month"] == 11 and lines[0]["hours"] == "16.0" and "credits" not in lines[0]
    listed = admin_client.get("/api/training/plans/").data[0]
    assert listed["hours_total"] == "16.0" and listed["lines_count"] == 1 and "credits_total" not in listed
    start = date(year, TODAY.month, 1)
    order = make_order(admin_client, "training", [a], date_=start.isoformat())
    set_params(admin_client, order, {"date_from": start.isoformat(), "date_to": (start + timedelta(days=2)).isoformat(),
                                     "destination": "Centrul de instruire", "purpose": "Securitatea la incendiu"})
    sign(admin_client, order)
    rec = TrainingRecord.objects.get(employee=a, order_item__isnull=False)
    assert rec.title == "Securitatea la incendiu" and Absence.objects.filter(employee=a, kind="training").exists()
    assert admin_client.get(f"/api/training/plan-lines/?plan={plan['id']}").data[0]["record"] == rec.pk
    assert admin_client.delete(f"/api/training/records/{rec.pk}/").status_code == 400  # vine din ordin
    html = admin_client.get(f"/api/training/plans/{plan['id']}/print/").content.decode()
    assert "PLANUL ANUAL DE FORMARE PROFESIONALĂ" in html and "realizat" in html and "Credite" not in html
    admin_client.post(f"/api/training/plans/{plan['id']}/approve/")
    assert admin_client.post(f"/api/training/plans/{plan['id']}/fill/").status_code == 400
    cancel(admin_client, order)
    assert not TrainingRecord.objects.filter(employee=a, order_item__isnull=False).exists()


def test_reports_and_scope(org, admin_client, make_user, client_for):
    a = person(org, "Popescu", "Ion")
    b = person(org, "Rusu", "Ana", sub="it")
    for e in (a, b):
        TrainingRecord.objects.create(employee=e, title="Curs", date_from=TODAY - timedelta(days=10), hours=24)
    data = admin_client.get(f"/api/reports/training_period/?date_from={TODAY - timedelta(days=30)}&date_to={TODAY}").data
    assert data["totals"]["hours"] == 48 and len(data["rows"]) == 2 and "credits" not in data["totals"]
    head = make_user("sef", ["department_head"])
    org["it"].users.add(head)
    api = client_for(head)
    assert [r["employee_name"] for r in api.get("/api/training/records/").data["results"]] == ["Rusu Ana"]
    assert api.post("/api/training/records/", {"employee": a.pk, "title": "x", "date_from": TODAY.isoformat()}, format="json").status_code in (403, 404)
