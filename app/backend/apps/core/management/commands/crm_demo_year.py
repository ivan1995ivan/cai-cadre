from django.core.management.base import BaseCommand, CommandError

from apps.core import demo, demo_year


class Command(BaseCommand):
    help = "Completează baza demo cu evidența unui an întreg: graficele de ture, pontaj, salarii (avans, calcul, plată), ordine, concedii, foi de boală."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=None, help="Anul (implicit: cel curent)")
        parser.add_argument("--force", action="store_true", help="Chiar dacă anul are deja calcule lunare")

    def handle(self, *args, **options):
        try:
            stats = demo_year.run(year=options["year"], force=options["force"], log=lambda text: self.stdout.write(text))
        except demo.DemoError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS("Datele pe an sunt gata: " + ", ".join(f"{k} {v}" for k, v in sorted(stats.items()))))
