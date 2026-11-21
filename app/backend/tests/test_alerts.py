"""Etapa 5 (partea 1): termenele și alertele, notificările de noapte (în sistem și pe e-mail), panoul de start."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core import mail as django_mail
from django.utils import timezone

from apps.alerts import engine
from apps.alerts.models import AlertLog
from apps.core.models import Notification
from apps.leave.models import Absence, LeaveRequest
from apps.org.models import DictItem, Occupation, Subdivision
from apps.staff import services as staff
from apps.staff.models import Employee, EmployeeDocument
from .conftest import occupation

TODAY = timezone.localdate()


@pytest.fixture
def org(seeded):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1")
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția ATI")
    return {"tr1": tr1, "ati": ati, "doctor": occupation("Medic traumatolog-ortoped")}


def person(org, last, first, sub="tr1", hired=None, **extra):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first,
                                **{k: extra.pop(k) for k in ("birth_date", "sex") if k in extra})
    staff.hire(e, kind="main", subdivision=org[sub], occupation=org["doctor"], rate=Decimal("1"), base_salary=Decimal("14000"),
               date_from=hired or TODAY - timedelta(days=400), **extra)
    return e


def kinds_of(alerts):
    return {a.kind for a in alerts}


def test_collect_alerts_for_terms_and_events(org):
    a = person(org, "Popescu", "Ion", probation_until=TODAY + timedelta(days=5), hired=TODAY - timedelta(days=80))
    b = person(org, "Rusu", "Ana", sub="ati", date_to=TODAY + timedelta(days=20), birth_date=TODAY.replace(year=TODAY.year - 40) + timedelta(days=2), sex="F")
    EmployeeDocument.objects.create(employee=a, doc_type=DictItem.objects.filter(kind="document").first(), number="B123",
                                    expiry_date=TODAY + timedelta(days=15))
    Absence.objects.create(employee=b, kind="childcare", date_from=TODAY - timedelta(days=300), date_to=TODAY + timedelta(days=10), days=310)
    LeaveRequest.objects.create(employee=a, kind="annual", date_from=TODAY + timedelta(days=40), days=14,
                                date_to=TODAY + timedelta(days=55))
    old = person(org, "Ceban", "Dan", hired=TODAY - timedelta(days=365 * 3 + 30))  # 2 ani de muncă încheiați, fără concediu
    alerts = engine.collect(TODAY)
    got = kinds_of(alerts)
    assert {"probation_end", "contract_end", "document_expiry", "childcare_end", "leave_requests", "leave_unused", "birthday"} <= got
    jubilee = next(x for x in alerts if x.kind == "birthday")
    assert jubilee.title == "Jubileu" and jubilee.employee == b.pk
    unused = next(x for x in alerts if x.kind == "leave_unused")
    assert unused.employee == old.pk and "art. 118" in unused.text
    # zilele de avertizare se schimbă din setări; tipul se poate opri
    engine.save_settings({"probation_end": {"enabled": True, "days": 3}, "birthday": {"enabled": False, "days": 7}})
    got = kinds_of(engine.collect(TODAY))
    assert "probation_end" not in got and "birthday" not in got


def test_retirement_and_sanction_and_unacknowledged_order(org, admin_client):
    from apps.orders.models import Sanction

    from .test_orders import make_order, set_params, sign

    e = person(org, "Lungu", "Petru", birth_date=TODAY.replace(year=TODAY.year - 63) + timedelta(days=60), sex="M")
    Sanction.objects.create(employee=e, kind=DictItem.objects.get(kind="sanction", code="reprimand"), date=TODAY - timedelta(days=360),
                            valid_until=TODAY + timedelta(days=5))
    order = make_order(admin_client, "bonus", [e], date_=(TODAY - timedelta(days=5)).isoformat())
    set_params(admin_client, order, {"amount": "500"})
    sign(admin_client, order)
    from apps.orders.models import Order

    Order.objects.filter(pk=order["id"]).update(signed_at=timezone.now() - timedelta(days=5))
    got = kinds_of(engine.collect(TODAY))
    assert {"retirement", "sanction_expiry", "order_unacknowledged", "payroll_orders"} <= got


def test_nightly_run_notifies_once_by_audience_and_emails(org, make_user, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    person(org, "Popescu", "Ion", probation_until=TODAY + timedelta(days=5), hired=TODAY - timedelta(days=80))
    person(org, "Rusu", "Ana", sub="ati", probation_until=TODAY + timedelta(days=6), hired=TODAY - timedelta(days=80))
    hr = make_user("insp", ["hr_inspector"], email="insp@spital.md")
    head = make_user("sef", ["department_head"])
    org["tr1"].users.add(head)
    acc = make_user("contabil", ["accountant"])
    from apps.alerts import mail

    mail.save_smtp({"enabled": True, "host": "smtp.test", "port": 25, "from_email": "cadre@spital.md", "use_tls": False})
    import unittest.mock as mock

    from django.core.mail import get_connection

    with mock.patch("apps.alerts.mail.get_connection", lambda *a, **k: get_connection("django.core.mail.backends.locmem.EmailBackend")):
        result = engine.run(TODAY)
    assert result["notified"] >= 3 and result["emails"] == 1
    assert Notification.objects.filter(user=hr, kind="alert_probation_end").count() == 2  # cadrele văd ambele secții
    assert Notification.objects.filter(user=head, kind="alert_probation_end").count() == 1  # șeful — doar secția lui
    assert not Notification.objects.filter(user=acc, kind="alert_probation_end").exists()  # contabilitatea nu
    assert len(django_mail.outbox) == 1 and django_mail.outbox[0].to == ["insp@spital.md"]
    assert "perioada de probă" in django_mail.outbox[0].body
    again = engine.run(TODAY)
    assert again["notified"] == 0 and AlertLog.objects.filter(user=hr, key__startswith="probation").count() == 2  # o singură dată


def test_alert_list_dashboard_and_settings_api(org, admin_client, make_user, client_for):
    person(org, "Popescu", "Ion", probation_until=TODAY + timedelta(days=5), hired=TODAY - timedelta(days=80))
    b = person(org, "Rusu", "Ana", sub="ati")
    Absence.objects.create(employee=b, kind="sick", date_from=TODAY, date_to=TODAY + timedelta(days=3), days=4)
    r = admin_client.get("/api/alerts/")
    assert r.status_code == 200 and r.data["counts"]["probation_end"] == 1
    d = admin_client.get("/api/alerts/dashboard/").data
    assert d["employees"] == 2 and d["sick"] == 1 and d["alerts"]["total"] >= 1 and d["alerts"]["top"]
    head = make_user("sef", ["department_head"])
    org["ati"].users.add(head)
    api = client_for(head)
    assert api.get("/api/alerts/dashboard/").data["employees"] == 1
    assert "probation_end" not in {r["kind"] for r in api.get("/api/alerts/").data["rows"]}  # perioada de probă e în traumatologie
    assert api.put("/api/alerts/settings/", {"retirement_men": 65}, format="json").status_code == 403
    s = admin_client.put("/api/alerts/settings/", {"retirement_men": 65, "contract_end": {"enabled": True, "days": 45}}, format="json").data
    assert s["retirement_men"] == 65 and s["contract_end"]["days"] == 45
    smtp = admin_client.put("/api/alerts/smtp/", {"host": "smtp.x", "password": "secret", "enabled": True}, format="json").data
    assert smtp["password"] == "********" and smtp["host"] == "smtp.x"
