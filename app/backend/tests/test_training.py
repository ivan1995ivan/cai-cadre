"""Etapa 6 (partea 1): registrul EMC, creditele pe perioada de atestare, atestarea, planul anual de formare."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.alerts import engine
from apps.leave.models import Absence
from apps.org.models import DictItem, Occupation, Specialty, Subdivision
from apps.staff import services as staff
from apps.staff.models import Employee, Qualification
from apps.training.models import Attestation, TrainingPlan, TrainingRecord

TODAY = timezone.localdate()


@pytest.fixture
def org(seeded):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1")
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția ATI")
    doctor = Occupation.objects.get(name_ro="Medic traumatolog-ortoped")
    assert doctor.category == "physicians"
    return {"tr1": tr1, "ati": ati, "doctor": doctor, "spec": Specialty.objects.first(),
            "first": DictItem.objects.get(kind="qualification", code="first"),
            "superior": DictItem.objects.get(kind="qualification", code="superior")}


def person(org, last, first, sub="tr1"):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first)
    staff.hire(e, kind="main", subdivision=org[sub], occupation=org["doctor"], rate=Decimal("1"), base_salary=Decimal("14000"),
               date_from=TODAY - timedelta(days=3000))
    return e


def qualify(org, e, awarded, cat="first"):
    return Qualification.objects.create(employee=e, category=org[cat], specialty=org["spec"], awarded_on=awarded)


def test_credits_in_attestation_period(org, admin_client):
    a = person(org, "Popescu", "Ion")
    qualify(org, a, TODAY - timedelta(days=365 * 4 + 200))  # expiră în ~5 luni
    TrainingRecord.objects.create(employee=a, title="Curs vechi", date_from=TODAY - timedelta(days=365 * 6), credits=100)  # înainte de perioadă
    r = admin_client.post("/api/training/records/", {"employee": a.pk, "title": "Traumatologie pediatrică", "kind": "course",
                                                     "date_from": (TODAY - timedelta(days=100)).isoformat(), "hours": 36, "credits": 120},
                          format="json")
    assert r.status_code == 201, r.data
    b = person(org, "Rusu", "Ana", sub="ati")
    qualify(org, b, TODAY - timedelta(days=200))
    TrainingRecord.objects.create(employee=b, title="Congres", date_from=TODAY - timedelta(days=30), credits=30)
    data = admin_client.get("/api/training/credits/").data
    by = {x["name"]: x for x in data["rows"]}
    assert by["Popescu Ion"]["credits"] == 120 and by["Popescu Ion"]["required"] == 250 and by["Popescu Ion"]["status"] == "risk"
    assert by["Rusu Ana"]["status"] == "ok"  # 30 de credite în 200 de zile — peste cât se cere pro-rata
    assert data["counts"]["risk"] == 1
    # norma se schimbă din setări
    admin_client.put("/api/training/settings/", {"credits": {"physicians": 100}}, format="json")
    assert {x["name"]: x["status"] for x in admin_client.get("/api/training/credits/").data["rows"]}["Popescu Ion"] == "done"
    # alerta „credite insuficiente” vine cu un an înainte de expirare
    admin_client.put("/api/training/settings/", {"credits": {"physicians": 250}}, format="json")
    alerts = [x for x in engine.collect(TODAY, ["credits_missing"])]
    assert [x.employee for x in alerts] == [a.pk]


def test_attestation_flow_until_award_order(org, admin_client):
    from .test_orders import sign

    a = person(org, "Popescu", "Ion")
    qualify(org, a, TODAY - timedelta(days=365 * 5 - 60))
    b = person(org, "Rusu", "Ana")
    qualify(org, b, TODAY - timedelta(days=100))  # nu e în calendar
    due = admin_client.get("/api/training/attestation-due/?months=6").data["rows"]
    assert [x["name"] for x in due] == ["Popescu Ion"] and not due[0]["in_list"]
    r = admin_client.post("/api/training/attestations/plan/", {"employees": [a.pk], "session_date": (TODAY + timedelta(days=30)).isoformat()},
                          format="json")
    assert r.data["created"] == 1
    assert admin_client.get("/api/training/attestation-due/?months=6").data["rows"][0]["in_list"]
    att = Attestation.objects.get(employee=a)
    assert att.requested_category == org["first"] and att.due_date
    html = admin_client.get("/api/training/attestations/print-list/?status=open").content.decode()
    assert "LISTA CANDIDAȚILOR" in html and "Popescu Ion" in html
    # rezultatul pozitiv cere categoria și data
    bad = admin_client.patch(f"/api/training/attestations/{att.pk}/", {"status": "awarded"}, format="json")
    assert bad.status_code == 400
    ok = admin_client.patch(f"/api/training/attestations/{att.pk}/", {"status": "awarded", "result_category": org["superior"].pk,
                                                                     "result_date": TODAY.isoformat(), "decision": "PV nr. 7"}, format="json")
    assert ok.status_code == 200, ok.data
    made = admin_client.post("/api/training/attestations/make-order/", {"ids": [att.pk]}, format="json")
    assert made.status_code == 200, made.data
    order = admin_client.get(f"/api/orders/orders/{made.data['orders'][0]['id']}/").data
    sign(admin_client, order)
    q = Qualification.objects.filter(employee=a).order_by("-awarded_on").first()
    assert q.category == org["superior"] and q.awarded_on == TODAY and q.valid_until.year == TODAY.year + 5
    assert admin_client.post("/api/training/attestations/make-order/", {"ids": [att.pk]}, format="json").status_code == 400


def test_training_order_creates_record_and_plan(org, admin_client):
    from .test_orders import cancel, make_order, set_params, sign

    a = person(org, "Popescu", "Ion")
    qualify(org, a, TODAY - timedelta(days=365 * 2))
    plan = admin_client.post("/api/training/plans/", {"year": TODAY.year, "number": "1"}, format="json").data
    filled = admin_client.post(f"/api/training/plans/{plan['id']}/fill/", {"only_behind": False}, format="json").data
    assert filled["added"] == 1
    lines = admin_client.get(f"/api/training/plan-lines/?plan={plan['id']}").data
    assert lines[0]["credits"] == "50.0" and not lines[0]["record"]
    start = date(TODAY.year, TODAY.month, 1)
    order = make_order(admin_client, "training", [a], date_=start.isoformat())
    set_params(admin_client, order, {"date_from": start.isoformat(), "date_to": (start + timedelta(days=4)).isoformat(),
                                     "destination": "USMF „Nicolae Testemițanu”", "purpose": "Ortopedie modernă"})
    sign(admin_client, order)
    rec = TrainingRecord.objects.get(employee=a)
    assert rec.provider.startswith("USMF") and rec.title == "Ortopedie modernă" and rec.order_item_id
    assert Absence.objects.filter(employee=a, kind="training").exists()
    assert admin_client.get(f"/api/training/plan-lines/?plan={plan['id']}").data[0]["record"] == rec.pk
    plans = admin_client.get("/api/training/plans/").data
    assert plans[0]["done_count"] == 1
    assert admin_client.delete(f"/api/training/records/{rec.pk}/").status_code == 400  # vine din ordin
    html = admin_client.get(f"/api/training/plans/{plan['id']}/print/").content.decode()
    assert "PLANUL ANUAL DE FORMARE" in html and "realizat" in html
    admin_client.post(f"/api/training/plans/{plan['id']}/approve/")
    assert admin_client.post(f"/api/training/plans/{plan['id']}/fill/").status_code == 400
    cancel(admin_client, order)
    assert not TrainingRecord.objects.filter(employee=a).exists()


def test_reports_and_scope(org, admin_client, make_user, client_for):
    a = person(org, "Popescu", "Ion")
    b = person(org, "Rusu", "Ana", sub="ati")
    for e in (a, b):
        qualify(org, e, TODAY - timedelta(days=300))
        TrainingRecord.objects.create(employee=e, title="Curs", date_from=TODAY - timedelta(days=10), hours=24, credits=20)
    data = admin_client.get(f"/api/reports/training_period/?date_from={TODAY - timedelta(days=30)}&date_to={TODAY}").data
    assert data["totals"]["credits"] == 40 and len(data["rows"]) == 2
    assert len(admin_client.get("/api/reports/emc_credits/").data["rows"]) == 2
    head = make_user("sef", ["department_head"])
    org["ati"].users.add(head)
    api = client_for(head)
    assert [r["name"] for r in api.get("/api/training/credits/").data["rows"]] == ["Rusu Ana"]
    assert [r["employee_name"] for r in api.get("/api/training/records/").data["results"]] == ["Rusu Ana"]
    assert api.post("/api/training/records/", {"employee": a.pk, "title": "x", "date_from": TODAY.isoformat()}, format="json").status_code in (403, 404)
