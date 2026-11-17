import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.core import bnm


class Command(BaseCommand):
    help = "Preia cursul oficial BNM (implicit pentru azi)."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="AAAA-LL-ZZ")

    def handle(self, *args, date=None, **options):
        day = datetime.date.fromisoformat(date) if date else datetime.date.today()
        try:
            saved = bnm.update_rates(day)
        except bnm.BnmError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Cursuri salvate pentru {day}: {saved}"))
