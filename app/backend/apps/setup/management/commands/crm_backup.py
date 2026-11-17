from django.core.management.base import BaseCommand, CommandError

from apps.setup import backup


class Command(BaseCommand):
    help = "Copia de rezervă a bazei de date și a fișierelor (instance/backups/)."

    def handle(self, *args, **options):
        try:
            result = backup.make_backup("manual")
        except backup.BackupError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Copia: {backup.backup_dir() / result['name']} ({result['size'] // 1024} KB)"))
