from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("tariff-grids", views.TariffGridViewSet, basename="tariff-grid")
router.register("operations", views.OperationViewSet, basename="operation")
router.register("operation-rates", views.OperationRateViewSet, basename="operation-rate")
router.register("brigades", views.BrigadeViewSet, basename="brigade")
router.register("reports", views.ProductionReportViewSet, basename="production-report")

urlpatterns = [
    path("reports/<int:pk>/import/<str:code>/", views.ReportImportView.as_view()),
    path("reports/<int:pk>/import/<str:code>/template/", views.ReportImportView.as_view()),
] + router.urls
