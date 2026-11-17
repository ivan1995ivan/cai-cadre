"""Limbile sistemului (Constante → Module): doar limbile bifate sunt în interfață; cine lucra în alta trece pe prima."""
from rest_framework.test import APIClient

from apps.users.models import User


def test_company_languages_limit_users_and_branding(admin_client, make_user, client_for):
    api_client = APIClient()
    ivan = make_user("ivan", [], language="ru")
    assert set(api_client.get("/api/public/branding/").data["languages"]) == {"ro", "ru", "en"}  # implicit toate
    r = admin_client.patch("/api/company/", {"languages": ["en", "ro"]}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["languages"] == ["ro", "en"]  # în ordinea firească
    assert api_client.get("/api/public/branding/").data["languages"] == ["ro", "en"]
    assert User.objects.get(pk=ivan.pk).language == "ro"
    me = client_for(ivan)
    assert me.patch("/api/auth/me/", {"language": "ru"}, format="json").status_code == 400
    assert me.patch("/api/auth/me/", {"language": "en"}, format="json").status_code == 200
    assert admin_client.patch("/api/company/", {"languages": []}, format="json").status_code == 400
