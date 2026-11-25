"""Lista angajaților: semnele din prima coloană (absent azi, în probă, contractul pe termen care expiră, lipsește IDNP / IBAN)
și telefonul verificat la salvare (doar valoarea nouă)."""
from datetime import timedelta

from django.utils import timezone

from apps.leave.models import Absence

from .test_staff import hire, make_emp, org  # noqa: F401 — fixtura și ajutoarele comune


def rows(api):
    return {r["full_name"]: r for r in api.get("/api/staff/employees/").json()["results"]}


def test_list_flags(admin_client, org):  # noqa: F811
    today = timezone.localdate()
    a = make_emp("Albu", "Ana", idnp="2001000000011", iban="MD24AG000225100013104168")
    b = make_emp("Botnaru", "Ion")
    hire(a, org, date_from=today - timedelta(days=40), probation_until=today + timedelta(days=20),
         date_to=today + timedelta(days=10))
    hire(b, org)
    Absence.objects.create(employee=a, kind="sick", date_from=today - timedelta(days=1), date_to=today + timedelta(days=3))
    got = rows(admin_client)
    fa, fb = got["Albu Ana"]["flags"], got["Botnaru Ion"]["flags"]
    assert fa["absent"]["kind"] == "sick" and fa["absent"]["to"] == (today + timedelta(days=3)).isoformat()
    assert fa["probation"] == (today + timedelta(days=20)).isoformat()
    assert fa["contract_ends"] == (today + timedelta(days=10)).isoformat() and "missing" not in fa
    assert fb == {"missing": ["idnp"]}  # IBAN-ul lipsă — plata în numerar, nu semn
    # semnele nu adaugă cereri pe rând: cu 10 angajați în plus — tot atâtea cereri
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as before:
        admin_client.get("/api/staff/employees/")
    for n in range(10):
        hire(make_emp(f"Extra{n}", "X"), org)
    with CaptureQueriesContext(connection) as after:
        admin_client.get("/api/staff/employees/")
    assert len(after) == len(before)


def test_phone_checked_only_when_changed(admin_client, org):  # noqa: F811
    e = make_emp(phone="tel. vechi, după ora 18")  # valoarea veche, scrisă liber, nu oprește salvarea fișei
    hire(e, org)
    url = f"/api/staff/employees/{e.id}/"
    assert admin_client.patch(url, {"phone": "tel. vechi, după ora 18", "email": "a@b.md"}, format="json").status_code == 200
    r = admin_client.patch(url, {"phone": "069 12-34-56"}, format="json")
    assert r.status_code == 200 and r.data["phone"] == "069123456"
    assert admin_client.patch(url, {"phone": "+373 69 123 456"}, format="json").data["phone"] == "+37369123456"
    assert admin_client.patch(url, {"phone": "+48 123 456 789"}, format="json").data["phone"] == "+48123456789"
    for bad in ("06912345", "+3736912345", "nu am", "12345"):
        assert admin_client.patch(url, {"phone": bad}, format="json").status_code == 400, bad
    assert admin_client.patch(url, {"phone": ""}, format="json").data["phone"] == ""
