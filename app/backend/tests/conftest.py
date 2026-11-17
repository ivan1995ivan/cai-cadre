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
