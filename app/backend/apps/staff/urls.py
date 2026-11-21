from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .import_views import ImportView

router = DefaultRouter()
router.register("employees", views.EmployeeViewSet, basename="employee")
router.register("documents", views.DocumentViewSet, basename="employee-document")
router.register("family", views.FamilyViewSet, basename="family-member")
router.register("education", views.EducationViewSet, basename="education")
router.register("experience", views.ExperienceViewSet, basename="experience")
router.register("military", views.MilitaryViewSet, basename="military")
router.register("employments", views.EmploymentViewSet, basename="employment")

urlpatterns = [
    path("import/<str:code>/", ImportView.as_view()),
    path("import/<str:code>/template/", ImportView.as_view()),
] + router.urls
