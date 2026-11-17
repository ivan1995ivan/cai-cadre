import sys

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.core import seed


class Command(BaseCommand):
    help = "Actualizează baza după o versiune nouă: copie de rezervă, migrații, date inițiale."

    def handle(self, *args, **options):
        if settings.SETUP_MODE:
            self.stdout.write("Sistemul nu este instalat; nimic de actualizat.")
            return
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            from apps.setup import backup

            try:
                result = backup.make_backup("upgrade")
                self.stdout.write(f"Copie de rezervă: {result['name']}")
            except backup.BackupError as exc:
                self.stderr.write(f"Copia de rezervă nu s-a putut face: {exc}")
                sys.exit(1)
            self.stdout.write(f"Se aplică {len(plan)} migrații...")
            call_command("migrate", interactive=False, verbosity=0)
        seed.run()
        self.stdout.write(self.style.SUCCESS("Baza de date este la zi."))
