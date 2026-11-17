from django.apps import AppConfig


class HealthConfig(AppConfig):
    name = "apps.health"
    label = "health"
    verbose_name = "Sănătatea în muncă"

    def ready(self):
        from apps.core.audit import register

        from . import hooks
        from .models import MedicalExam, SafetyBriefing, Vaccination

        hooks.register()
        for model in (MedicalExam, Vaccination, SafetyBriefing):
            register(model, parent="employee")
