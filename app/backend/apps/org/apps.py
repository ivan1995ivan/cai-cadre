from django.apps import AppConfig


class OrgConfig(AppConfig):
    name = "apps.org"
    label = "org"
    verbose_name = "Instituția și statele de personal"

    def ready(self):
        from apps.core.audit import register
        from apps.printing import views as printing_views

        from . import printing
        from .models import DictItem, LegalBasis, Occupation, OrderType, Specialty, StaffList, StaffListLine, Subdivision

        for model in (Occupation, Specialty, DictItem, LegalBasis, OrderType, Subdivision, StaffList):
            register(model)
        register(StaffListLine, parent="staff_list")
        printing_views.SAMPLE_BUILDERS["staff_list"] = printing.sample
        printing_views.DEFAULT_OPTIONS["staff_list"] = printing.OPTIONS
