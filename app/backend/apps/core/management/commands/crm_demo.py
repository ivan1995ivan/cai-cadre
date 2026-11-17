from django.core.management.base import BaseCommand, CommandError

from apps.core import demo


class Command(BaseCommand):
    help = "Umple o bază nouă cu date demo (un spital fictiv) pentru prezentări."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Chiar dacă baza are deja clienți sau comenzi")

    def handle(self, *args, **options):
        try:
            result = demo.run(force=options["force"])
        except demo.DemoError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Datele demo sunt gata: {result.get('employees', 0)} angajați. Utilizatori: {', '.join(result['users'])} "
            f"(parola {result['password']})."))
