from django.apps import AppConfig


class HealthConfig(AppConfig):
    name = "apps.health"
    label = "health"
    verbose_name = "Sănătatea și securitatea în muncă"

    def ready(self):
        from apps.core.audit import register

        from . import hooks
        from .models import ExamRule, MedicalExam, SafetyBriefing

        hooks.register()
        for model in (MedicalExam, SafetyBriefing):
            register(model, parent="employee")
        register(ExamRule)
