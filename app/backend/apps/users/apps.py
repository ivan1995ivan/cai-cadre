from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "apps.users"
    label = "users"
    verbose_name = "Utilizatori"

    def ready(self):
        from apps.core.audit import register

        from .models import Role, User

        register(User, exclude={"password", "last_login"})
        register(Role)
