from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("exams", views.ExamViewSet, basename="medical-exam")
router.register("vaccinations", views.VaccinationViewSet, basename="vaccination")
router.register("briefings", views.BriefingViewSet, basename="safety-briefing")

urlpatterns = [
    path("due/", views.DueView.as_view()),
    path("settings/", views.SettingsView.as_view()),
] + router.urls
