from django.apps import AppConfig


class WorktimeConfig(AppConfig):
    name = "apps.worktime"
    label = "worktime"
    verbose_name = "Timp de muncă"

    def ready(self):
        from apps.core.audit import register
        from apps.printing import views as printing_views

        from . import printing
        from .models import JobSchedule, Roster, ShiftType, Timesheet, WorkSchedule

        register(ShiftType)
        register(WorkSchedule)
        register(JobSchedule)
        register(Roster)
        register(Timesheet)
        printing_views.SAMPLE_BUILDERS["timesheet"] = printing.sample
        printing_views.SAMPLE_BUILDERS["roster"] = printing.sample_roster
