"""Blocarea contului după parole greșite la rând (settings.LOGIN_MAX_FAILURES, pe LOGIN_LOCK_MINUTES minute): cât e blocat,
nici parola bună nu intră; reușita șterge numărătoarea; administratorul deblochează (butonul sau parola nouă)."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import AuditLog
from apps.users.models import User

GOOD = "Parola-Sigura-2026"


def login(username, password):
    return APIClient().post("/api/auth/login/", {"username": username, "password": password}, format="json")


def test_lock_after_failures_and_reset_on_success(make_user, settings):
    settings.LOGIN_MAX_FAILURES, settings.LOGIN_LOCK_MINUTES = 3, 15
    make_user("ion")
    assert login("ion", "gresit").status_code == 401
    assert login("ion", GOOD).status_code == 200  # reușita șterge numărătoarea
    assert User.objects.get(username="ion").failed_logins == 0
    for _ in range(2):
        r = login("ion", "gresit")
        assert r.status_code == 401 and "code" not in r.data
    r = login("ion", "gresit")  # a treia la rând — blocat
    assert r.status_code == 401 and r.data["code"] == "locked" and "blocat până la" in r.data["detail"]
    u = User.objects.get(username="ion")
    assert u.locked_until > timezone.now() + timedelta(minutes=14) and u.failed_logins == 0
    assert login("ion", GOOD).data["code"] == "locked"  # nici parola bună cât ține blocarea
    assert AuditLog.objects.filter(action="action", object_repr__contains="cont blocat").count() == 1
    # trece timpul — intră și numărătoarea e ștearsă
    User.objects.filter(username="ion").update(locked_until=timezone.now() - timedelta(seconds=1))
    assert login("ion", GOOD).status_code == 200
    u.refresh_from_db()
    assert u.locked_until is None and u.failed_logins == 0
    # un nume inexistent nu blochează nimic și răspunde la fel ca parola greșită
    r = login("nimeni", "x")
    assert r.status_code == 401 and r.data == {"detail": "Utilizator sau parolă greșită."}


def test_admin_unlocks(admin_client, make_user, client_for, settings):
    settings.LOGIN_MAX_FAILURES = 2
    u = make_user("ana")
    for _ in range(2):
        login("ana", "gresit")
    u.refresh_from_db()
    assert u.locked_until is not None
    row = next(x for x in admin_client.get("/api/users/", {"search": "ana"}).data["results"] if x["id"] == u.pk)
    assert row["locked_until"] is not None
    assert client_for(make_user("simplu")).post(f"/api/users/{u.pk}/unlock/").status_code == 403
    assert admin_client.post(f"/api/users/{u.pk}/unlock/").data["locked_until"] is None
    assert login("ana", GOOD).status_code == 200
    # parola nouă dată de administrator deblochează și ea
    for _ in range(2):
        login("ana", "gresit")
    assert admin_client.patch(f"/api/users/{u.pk}/", {"password": "Alta-Parola-Sigura-2026"}, format="json").status_code == 200
    assert login("ana", "Alta-Parola-Sigura-2026").status_code == 200
