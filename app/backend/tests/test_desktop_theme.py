"""Tema „Clasic de birou”: implicită pentru întreprinderea nouă și pentru cea rămasă pe vechea temă implicită; de ales în
Profil (luminoasă și întunecată) și în Constante."""
import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.core.models import Company

BEFORE, AFTER = ("core", "0008_company_military_enabled"), ("core", "0009_desktop_theme")


def migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.fixture
def before_desktop(transactional_db):
    yield migrate([BEFORE])
    migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def test_migration_moves_only_the_old_default(before_desktop):
    old = before_desktop.get_model("core", "Company")
    old.objects.create(id=1, name_ro="Firma veche", default_theme="green")
    old.objects.create(id=2, name_ro="Firma turcoaz", default_theme="turquoise")
    old.objects.create(id=3, name_ro="Firma 1C", default_theme="onec")

    new = migrate([AFTER]).get_model("core", "Company")
    assert dict(new.objects.values_list("id", "default_theme")) == {1: "desktop", 2: "turquoise", 3: "onec"}

    # înapoi: tema clasică redevine cea veche implicită
    back = migrate([BEFORE]).get_model("core", "Company")
    assert dict(back.objects.values_list("id", "default_theme")) == {1: "green", 2: "turquoise", 3: "onec"}


def test_new_company_and_branding_default_to_desktop(seeded, client):
    assert Company.get().default_theme == "desktop"
    assert client.get("/api/public/branding/").json()["default_theme"] == "desktop"


@pytest.mark.parametrize("theme", ["desktop", "desktop_dark", "green", "auto", ""])
def test_user_can_pick_the_desktop_themes(admin_client, theme):
    r = admin_client.patch("/api/auth/me/", {"theme": theme}, format="json")
    assert r.status_code == 200, r.content
    assert r.json()["theme"] == theme


def test_unknown_theme_is_refused(admin_client):
    assert admin_client.patch("/api/auth/me/", {"theme": "windows95"}, format="json").status_code == 400


@pytest.mark.parametrize("theme", ["desktop", "desktop_dark"])
def test_company_default_theme_in_constants(admin_client, theme):
    r = admin_client.patch("/api/company/", {"default_theme": theme}, format="json")
    assert r.status_code == 200, r.content
    assert Company.get().default_theme == theme
