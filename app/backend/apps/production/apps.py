from django.apps import AppConfig


class ProductionConfig(AppConfig):
    name = "apps.production"
    label = "production"
    verbose_name = "Producția (salarizarea în acord)"

    def ready(self):
        from apps.core.audit import register
        from apps.printing import views as printing_views

        from . import printing
        from .models import (Brigade, BrigadeMember, Operation, OperationRate, ProductionLine, ProductionMember, ProductionReport,
                             TariffGrid, TariffRank)

        printing_views.SAMPLE_BUILDERS["production_report"] = printing.sample_report
        register(TariffGrid)
        register(TariffRank, parent="grid")
        register(Operation)
        register(OperationRate, parent="operation")
        register(Brigade)
        register(BrigadeMember, parent="brigade")
        register(ProductionReport)
        register(ProductionLine, parent="report")
        register(ProductionMember, parent="report")
