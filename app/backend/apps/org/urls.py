from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("occupations", views.OccupationViewSet, basename="occupation")
router.register("specialties", views.SpecialtyViewSet, basename="specialty")
router.register("dict-items", views.DictItemViewSet, basename="dict-item")
router.register("legal-bases", views.LegalBasisViewSet, basename="legal-basis")
router.register("order-types", views.OrderTypeViewSet, basename="order-type")
router.register("subdivisions", views.SubdivisionViewSet, basename="subdivision")
router.register("staff-lists", views.StaffListViewSet, basename="staff-list")
router.register("staff-list-lines", views.StaffListLineViewSet, basename="staff-list-line")

urlpatterns = [
    path("meta/", views.MetaView.as_view()),
    path("occupancy/", views.OccupancyView.as_view()),
    path("import/<str:code>/", views.ImportView.as_view()),
    path("import/<str:code>/template/", views.ImportView.as_view()),
] + router.urls
