from django.apps import AppConfig


class PrintingConfig(AppConfig):
    name = "apps.printing"
    label = "printing"
    verbose_name = "Forme de tipar"

    def ready(self):
        from apps.core.audit import register

        from .models import PrintTemplate

        register(PrintTemplate, exclude={"updated_at", "original_body", "original_css"})
