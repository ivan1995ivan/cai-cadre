from django.apps import AppConfig


class StaffConfig(AppConfig):
    name = "apps.staff"
    label = "staff"
    verbose_name = "Dosarul angajatului"

    def ready(self):
        from apps.core import nightly
        from apps.core.audit import register
        from apps.org import services as org_services
        from apps.printing import views as printing_views

        from . import printing, services
        from .models import (Education, Employee, EmployeeDocument, Employment, FamilyMember, MilitaryRecord,
                             PriorExperience)

        register(Employee, exclude={"checklist"})
        for model in (EmployeeDocument, FamilyMember, Education, PriorExperience, MilitaryRecord, Employment):
            register(model, parent="employee")
        if services.occupancy_provider not in org_services.OCCUPANCY_PROVIDERS:
            org_services.OCCUPANCY_PROVIDERS.append(services.occupancy_provider)
        for doc in printing.EMPLOYEE_DOCS:
            printing_views.SAMPLE_BUILDERS[doc] = printing.sample_builder(doc)
            printing_views.DEFAULT_OPTIONS[doc] = printing.OPTIONS[doc]
        printing_views.SAMPLE_BUILDERS["employee_list"] = printing.sample_list
        printing_views.DEFAULT_OPTIONS["employee_list"] = printing.OPTIONS["employee_list"]
        if not any(name == "employment_changes" for name, _ in nightly.TASKS):
            nightly.TASKS.append(("employment_changes", services.apply_due_changes))
