"""Etapa 7: cabinetul angajatului — accesul, datele proprii, ordinele cu „am luat cunoștință”, cererile, notificările."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail as django_mail
from django.utils import timezone

from apps.core.models import Notification
from apps.org.models import Occupation, Subdivision
from apps.portal.models import EmployeeRequest
from apps.staff import services as staff
from apps.staff.models import Employee
from apps.users.models import User

TODAY = timezone.localdate()


@pytest.fixture
def org(seeded):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1")
    return {"tr1": tr1, "doctor": Occupation.objects.get(name_ro="Medic traumatolog-ortoped")}


def person(org, last, first, **extra):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first, **extra)
    staff.hire(e, kind="main", subdivision=org["tr1"], occupation=org["doctor"], rate=Decimal("1"), base_salary=Decimal("14000"),
               date_from=TODAY - timedelta(days=500))
    return e


def portal_client(admin_client, client_for, emp):
    r = admin_client.post(f"/api/portal/access/{emp.pk}/")
    assert r.status_code == 200, r.data
    assert r.data["password"] and r.data["username"]
    user = User.objects.get(username=r.data["username"])
    assert user.must_change_password and user.roles.filter(code="employee").exists()
    return client_for(user), user


def test_access_profile_and_isolation(org, admin_client, client_for):
    a = person(org, "Popescu", "Ion", email="ion.popescu@spital.md")
    b = person(org, "Rusu", "Ana")
    api, user = portal_client(admin_client, client_for, a)
    assert user.username == "ion.popescu"
    prof = api.get("/api/portal/profile/").data
    assert prof["full_name"] == "Popescu Ion" and prof["jobs"][0]["rate"] == 100 and prof["leave"]["available"] > 0
    # angajatul nu vede lista angajaților și nici dosarul altuia
    assert api.get("/api/staff/employees/").status_code == 403
    assert api.get(f"/api/staff/employees/{b.pk}/").status_code == 403
    # parola nouă pentru același cont; oprirea accesului
    again = admin_client.post(f"/api/portal/access/{a.pk}/").data
    assert again["username"] == "ion.popescu"
    admin_client.delete(f"/api/portal/access/{a.pk}/")
    assert not User.objects.get(pk=user.pk).is_active
    # utilizatorul fără angajat legat
    lonely = client_for(User.objects.create_user("singur", password="x-Parola-2026"))
    lonely.force_authenticate(User.objects.get(username="singur"))
    User.objects.get(username="singur").roles.set(user.roles.all())
    assert client_for(User.objects.get(username="singur")).get("/api/portal/profile/").status_code == 404


def test_orders_acknowledge_and_notification(org, admin_client, client_for, django_capture_on_commit_callbacks):
    from .test_orders import make_order, set_params, sign

    a = person(org, "Popescu", "Ion")
    api, user = portal_client(admin_client, client_for, a)
    order = make_order(admin_client, "bonus", [a], date_=TODAY.isoformat())
    set_params(admin_client, order, {"amount": "500"})
    with django_capture_on_commit_callbacks(execute=True):
        sign(admin_client, order)
    assert Notification.objects.filter(user=user, kind="portal_order").exists()
    rows = api.get("/api/portal/orders/").data
    assert len(rows) == 1 and rows[0]["acknowledged_on"] is None
    assert api.get("/api/portal/profile/").data["todo"]["orders"] == 1
    r = api.post("/api/portal/orders/", {"item": rows[0]["id"]}, format="json")
    assert r.data["acknowledged_on"] == TODAY.isoformat()
    assert api.get("/api/portal/profile/").data["todo"]["orders"] == 0


def test_leave_request_flow_with_notifications(org, admin_client, make_user, client_for, settings, django_capture_on_commit_callbacks):
    from apps.alerts import mail

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    a = person(org, "Popescu", "Ion", email="ion@spital.md")
    api, user = portal_client(admin_client, client_for, a)
    head = make_user("sef", ["department_head"], email="sef@spital.md")
    org["tr1"].users.add(head)
    hr = make_user("insp", ["hr_inspector"])
    mail.save_smtp({"enabled": True, "host": "smtp.test", "port": 25, "from_email": "cadre@spital.md", "use_tls": False})
    import unittest.mock as mock

    from django.core.mail import get_connection

    start = TODAY + timedelta(days=40)
    patch = mock.patch("apps.alerts.mail.get_connection", lambda *x, **k: get_connection("django.core.mail.backends.locmem.EmailBackend"))
    with patch, django_capture_on_commit_callbacks(execute=True):
        r = api.post("/api/portal/leave-requests/", {"kind": "annual", "date_from": start.isoformat(), "days": 7}, format="json")
    assert r.status_code == 201, r.data
    assert Notification.objects.filter(user=head, kind="portal_leave").exists()
    assert any("sef@spital.md" in m.to for m in django_mail.outbox)
    # șeful aprobă → angajatul și cadrele sunt anunțați
    with django_capture_on_commit_callbacks(execute=True):
        ok = client_for(head).post(f"/api/leave/requests/{r.data['id']}/approve/", {}, format="json")
    assert ok.status_code == 200, ok.data
    assert Notification.objects.filter(user=user, title__contains="aprobată").exists()
    assert Notification.objects.filter(user=hr, kind="portal_leave").exists()
    mine = api.get("/api/portal/leave-requests/").data
    assert mine[0]["status"] == "approved"
    assert api.post("/api/portal/leave-requests/withdraw/", {"id": r.data["id"]}, format="json").status_code == 400  # aprobată — nu se retrage din cabinet
    # ordinul din cerere → „ordinul este emis”
    with django_capture_on_commit_callbacks(execute=True):
        made = admin_client.post("/api/leave/requests/make-orders/", {"ids": [r.data["id"]]}, format="json")
    assert made.status_code == 201, made.data
    assert Notification.objects.filter(user=user, title__contains="Ordinul pentru concediu").exists()


def test_other_requests_inbox(org, admin_client, make_user, client_for, django_capture_on_commit_callbacks):
    a = person(org, "Popescu", "Ion")
    api, user = portal_client(admin_client, client_for, a)
    hr = make_user("insp", ["hr_inspector"])
    with django_capture_on_commit_callbacks(execute=True):
        r = api.post("/api/portal/my-requests/", {"kind": "certificate_work", "text": "Pentru bancă", "copies": 2}, format="json")
    assert r.status_code == 201, r.data
    assert Notification.objects.filter(user=hr, kind="portal_request").exists()
    inbox = client_for(hr).get("/api/portal/requests/?status=open").data["results"]
    assert [x["employee_name"] for x in inbox] == ["Popescu Ion"]
    with django_capture_on_commit_callbacks(execute=True):
        done = client_for(hr).patch(f"/api/portal/requests/{r.data['id']}/", {"status": "done", "answer": "Ridicați la cabinetul 12"},
                                    format="json")
    assert done.status_code == 200, done.data
    assert Notification.objects.filter(user=user, kind="portal_request", message__contains="cabinetul 12").exists()
    assert api.post(f"/api/portal/my-requests/{r.data['id']}/withdraw/").status_code == 400  # gata — nu se mai retrage
    # angajatul nu are acces la lista cadrelor
    assert api.get("/api/portal/requests/").status_code == 403
    assert EmployeeRequest.objects.get(pk=r.data["id"]).handled_by == hr


def test_payslips_only_own_and_bulk_access(org, admin_client, client_for):
    a = person(org, "Popescu", "Ion")
    person(org, "Rusu", "Ana")
    api, _ = portal_client(admin_client, client_for, a)
    assert api.get("/api/portal/payslips/").data == []
    made = admin_client.post("/api/portal/access/bulk/").data
    assert [x["employee"] for x in made] == ["Rusu Ana"]  # Popescu are deja cont
