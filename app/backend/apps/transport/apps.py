from django.apps import AppConfig


class TransportConfig(AppConfig):
    name = "apps.transport"
    label = "transport"
    verbose_name = "Transportul (cursele, diurnele, plata pe km)"

    def ready(self):
        from apps.alerts import engine as alerts
        from apps.core.audit import register
        from apps.printing import views as printing_views

        from . import printing, tacho
        from .models import Country, KmRate, PerDiemNorm, TachoFile, Trip, TripLeg, Vehicle

        alerts.register("tacho_download", True, 7, ("head", "accounting"), tacho.download_alerts)
        alerts.register("tacho_infringement", True, 14, ("head", "accounting"), tacho.infringement_alerts)

        printing_views.SAMPLE_BUILDERS["trip_sheet"] = printing.sample_trip
        register(Vehicle)
        register(KmRate)
        register(Country)
        register(PerDiemNorm, parent="country")
        register(Trip)
        register(TripLeg, parent="trip")
        register(TachoFile)
