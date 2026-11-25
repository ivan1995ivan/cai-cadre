from django.apps import AppConfig


class ReportsConfig(AppConfig):
    name = "apps.reports"
    label = "reports"
    verbose_name = "Rapoarte"

    def ready(self):
        from apps.printing.views import SAMPLE_BUILDERS

        from . import activity, personnel, settlement  # noqa: F401 — înregistrează rapoartele în catalog
        from .printing import sample

        SAMPLE_BUILDERS["report"] = sample
