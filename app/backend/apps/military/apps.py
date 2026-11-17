from django.apps import AppConfig


class MilitaryConfig(AppConfig):
    """Evidența militară: fișa e în dosarul angajatului (staff.MilitaryRecord); aici — registrul și rapoartele."""

    name = "apps.military"
    label = "military"
    verbose_name = "Evidența militară"

    def ready(self):
        from . import reports  # noqa: F401 — rapoartele se înregistrează în catalog
