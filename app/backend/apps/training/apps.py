from django.apps import AppConfig


class TrainingConfig(AppConfig):
    name = "apps.training"
    label = "training"
    verbose_name = "Formarea profesională"

    def ready(self):
        from . import hooks

        hooks.register()
