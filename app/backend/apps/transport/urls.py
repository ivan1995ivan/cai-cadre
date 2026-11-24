from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("vehicles", views.VehicleViewSet, basename="vehicle")
router.register("km-rates", views.KmRateViewSet, basename="km-rate")
router.register("countries", views.CountryViewSet, basename="country")
router.register("per-diem-norms", views.PerDiemNormViewSet, basename="per-diem-norm")
router.register("trips", views.TripViewSet, basename="trip")

urlpatterns = [
    path("trips/import/", views.TripImportView.as_view()),
    path("trips/import/template/", views.TripImportView.as_view()),
] + router.urls
