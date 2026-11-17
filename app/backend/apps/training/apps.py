from django.apps import AppConfig


class TrainingConfig(AppConfig):
    name = "apps.training"
    label = "training"
    verbose_name = "Formare și atestare"

    def ready(self):
        from . import hooks

        hooks.register()
