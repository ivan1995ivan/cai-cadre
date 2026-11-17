from django.apps import AppConfig


class LeaveConfig(AppConfig):
    name = "apps.leave"
    label = "leave"
    verbose_name = "Concedii și absențe"

    def ready(self):
        from apps.core import nightly
        from apps.core.audit import register
        from apps.printing import views as printing_views

        from . import printing, services
        from .models import Absence, LeaveAdjustment, LeaveRequest, LeaveRight, LeaveSchedule, LeaveScheduleLine, SickLeave

        register(Absence, parent="employee")
        register(LeaveRight, parent="employee")
        register(LeaveAdjustment, parent="employee")
        register(LeaveRequest, parent="employee")
        register(SickLeave, parent="employee")
        register(LeaveSchedule)
        register(LeaveScheduleLine, parent="schedule")
        printing_views.SAMPLE_BUILDERS["leave_schedule"] = printing.sample
        if not any(name == "childcare_return" for name, _ in nightly.TASKS):
            nightly.TASKS.append(("childcare_return", services.resume_after_childcare))
