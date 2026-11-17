from django.core.management.base import BaseCommand

from apps.core import seed


class Command(BaseCommand):
    help = "Încarcă/actualizează datele inițiale (drepturi, roluri, valute, TVA, numerotare)."

    def handle(self, *args, **options):
        seed.run()
        self.stdout.write(self.style.SUCCESS("Datele inițiale sunt la zi."))
