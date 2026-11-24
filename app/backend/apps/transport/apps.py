from django.apps import AppConfig


class TransportConfig(AppConfig):
    name = "apps.transport"
    label = "transport"
    verbose_name = "Transportul (cursele, diurnele, plata pe km)"

    def ready(self):
        from apps.core.audit import register
        from apps.printing import views as printing_views

        from . import printing
        from .models import Country, KmRate, PerDiemNorm, Trip, TripLeg, Vehicle

        printing_views.SAMPLE_BUILDERS["trip_sheet"] = printing.sample_trip
        register(Vehicle)
        register(KmRate)
        register(Country)
        register(PerDiemNorm, parent="country")
        register(Trip)
        register(TripLeg, parent="trip")
