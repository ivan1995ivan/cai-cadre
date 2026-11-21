import pytest
from rest_framework.test import APIClient

from apps.core import seed
from apps.users.models import Role, User


@pytest.fixture
def seeded(db):
    seed.run()


@pytest.fixture
def make_user(seeded):
    def _make(username="user", role_codes=(), password="Parola-Sigura-2026", **extra):
        user = User.objects.create_user(username=username, password=password, **extra)
        user.roles.set(Role.objects.filter(code__in=role_codes))
        return user

    return _make


@pytest.fixture
def admin_user(make_user):
    return make_user("admin", ["admin"])


@pytest.fixture
def client_for():
    def _client(user):
        api = APIClient()
        api.force_authenticate(user)
        return api

    return _client


@pytest.fixture
def admin_client(admin_user, client_for):
    return client_for(admin_user)


# Clasificatoarele livrate nu mai au funcții și categorii de spital (S1). Testele modulelor care încă le folosesc își fac
# singure ce le trebuie, cu aceste două funcții.
TEST_OCCUPATIONS = {  # denumirea → (grupa CORM = codul categoriei de personal, ore pe săptămână)
    "Medic traumatolog-ortoped": ("2", 35), "Medic anesteziolog-reanimatolog": ("2", 35),
    "Asistent medical de secție": ("3", 35), "Director": ("1", 40),
}


def occupation(name: str):
    """Funcția de test (după denumire), cu categoria de personal din clasificator."""
    from apps.org.models import DictItem, Occupation

    group, hours = TEST_OCCUPATIONS[name]
    obj, _ = Occupation.objects.get_or_create(name_ro=name, defaults={
        "category": DictItem.objects.get(kind="staff_category", code=group), "weekly_hours": hours})
    return obj


def legacy_qualification():
    """Categoriile de calificare și tipul de ordin „Conferirea categoriei” — nu se mai livrează (erau de spital)."""
    from apps.org.models import DictItem, OrderType

    for i, (code, name) in enumerate([("none", "Fără categorie"), ("second", "Categoria a doua"), ("first", "Categoria întâi"),
                                      ("superior", "Categoria superioară")], start=1):
        DictItem.objects.get_or_create(kind="qualification", code=code, defaults={"name_ro": name, "sort": i * 10})
    OrderType.objects.get_or_create(code="category_award", defaults={
        "name_ro": "Conferirea / confirmarea categoriei de calificare", "group": "F", "effect": "qualification",
        "collective": True, "title_ro": "Cu privire la conferirea categoriei de calificare", "payroll_effect": True})
