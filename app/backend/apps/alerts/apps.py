from django.apps import AppConfig


class AlertsConfig(AppConfig):
    name = "apps.alerts"
    label = "alerts"
    verbose_name = "Termene și alerte"

    def ready(self):
        from apps.core import nightly

        from . import engine

        if not any(name == "alerts" for name, _ in nightly.TASKS):
            nightly.TASKS.append(("alerts", engine.run))
