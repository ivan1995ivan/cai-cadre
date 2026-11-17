from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("records", views.TrainingRecordViewSet, basename="training-record")
router.register("attestations", views.AttestationViewSet, basename="attestation")
router.register("plans", views.PlanViewSet, basename="training-plan")
router.register("plan-lines", views.PlanLineViewSet, basename="training-plan-line")

urlpatterns = [
    path("credits/", views.CreditsView.as_view()),
    path("attestation-due/", views.AttestationDueView.as_view()),
    path("settings/", views.SettingsView.as_view()),
] + router.urls
