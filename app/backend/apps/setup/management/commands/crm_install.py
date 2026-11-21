import json
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core import seed
from apps.core.banks import fill
from apps.core.models import BankAccount, Company
from apps.users.models import Role, User

# datele întreprinderii pe care le poate aduce asistentul de instalare (restul — în Constante)
COMPANY_FIELDS = [
    "name_ro", "name_ru", "legal_form", "idno", "caem", "legal_address", "postal_address", "phone", "email", "website",
    "director", "director_position_ro", "chief_accountant", "hr_head", "default_theme",
]


class Command(BaseCommand):
    help = "Instalează sau actualizează structura bazei de date (folosit de asistentul de instalare)."

    def add_arguments(self, parser):
        parser.add_argument("--payload", help="Fișier JSON cu datele firmei și ale administratorului")

    def handle(self, *args, payload=None, **options):
        data = json.loads(Path(payload).read_text(encoding="utf-8")) if payload else {}
        self.stdout.write("Se creează/actualizează structura bazei de date...")
        call_command("migrate", interactive=False, verbosity=1, stdout=self.stdout)
        self.stdout.write("Se încarcă datele inițiale...")
        seed.run()
        if data.get("mode", "new") == "new":
            self._configure(data)
        self.stdout.write(self.style.SUCCESS("Instalarea s-a terminat cu succes."))

    @transaction.atomic
    def _configure(self, data):
        company = Company.get()
        for field in COMPANY_FIELDS:
            if data.get("company", {}).get(field) not in (None, ""):
                setattr(company, field, data["company"][field])
        company.save()
        bank = fill(dict(data.get("company", {}).get("bank") or {}))
        if bank.get("iban") and not company.bank_accounts.filter(iban=bank["iban"]).exists():
            BankAccount.objects.create(company=company, iban=bank["iban"], bank_name=bank.get("bank_name", ""),
                                       bic=bank.get("bic", ""), is_default=True)

        admin = data.get("admin") or {}
        if not admin.get("username"):
            return
        if User.objects.filter(username=admin["username"]).exists():
            raise CommandError(f"Utilizatorul „{admin['username']}” există deja în această bază.")
        user = User.objects.create_superuser(
            username=admin["username"],
            password=admin["password"],
            email=admin.get("email", ""),
            first_name=admin.get("first_name", ""),
            last_name=admin.get("last_name", ""),
            language=data.get("language", "ro"),
        )
        user.roles.add(Role.objects.get(code="admin"))
        self.stdout.write(f"Administratorul „{user.username}” a fost creat.")
