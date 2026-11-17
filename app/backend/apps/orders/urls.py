from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("orders", views.OrderViewSet, basename="order")
router.register("items", views.OrderItemViewSet, basename="order-item")
router.register("absences", views.AbsenceViewSet, basename="absence")
router.register("sanctions", views.SanctionViewSet, basename="sanction")
router.register("incentives", views.IncentiveViewSet, basename="incentive")

urlpatterns = [
    path("leave-days/", views.LeaveDaysView.as_view()),
] + router.urls
