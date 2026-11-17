import getpass

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.users.models import Role, User


class Command(BaseCommand):
    help = ("Creează administratorul sau îi pune o parolă nouă (când parola s-a uitat sau asistentul n-a creat contul). "
            "Pe server: crm-admin.cmd din dosarul programului, pornit ca administrator.")

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", help="Fără el, parola se cere de la tastatură (de două ori)")

    def handle(self, *args, username="admin", password=None, **options):
        username = (username or "").strip() or "admin"
        if not password:
            password = getpass.getpass(f"Parola nouă pentru „{username}”: ")
            if password != getpass.getpass("Încă o dată: "):
                raise CommandError("Parolele nu coincid.")
        if len(password) < 8:
            raise CommandError("Parola trebuie să aibă cel puțin 8 caractere.")
        # după o instalare întreruptă: structura bazei și datele inițiale (roluri, drepturi) se termină întâi
        call_command("migrate", interactive=False, verbosity=0)
        if not Role.objects.filter(code="admin").exists():
            from apps.core import seed

            seed.run()
        user, created = User.objects.get_or_create(username=username)
        user.is_superuser = user.is_staff = user.is_active = True
        user.must_change_password = False
        user.set_password(password)
        user.save()
        user.roles.add(Role.objects.get(code="admin"))
        self.stdout.write(self.style.SUCCESS(
            f"Administratorul „{username}” a fost {'creat' if created else 'actualizat'}: intrați cu parola nouă."))
