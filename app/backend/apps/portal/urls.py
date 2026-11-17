from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("my-requests", views.MyRequestsViewSet, basename="portal-my-request")
router.register("requests", views.RequestsInboxViewSet, basename="portal-request")

urlpatterns = [
    path("profile/", views.ProfileView.as_view()),
    path("orders/", views.OrdersView.as_view()),
    path("leave-requests/", views.LeaveRequestsView.as_view()),
    path("leave-requests/withdraw/", views.LeaveWithdrawView.as_view()),
    path("payslips/", views.PayslipsView.as_view()),
    path("access/<int:pk>/", views.AccessView.as_view()),
    path("access/bulk/", views.BulkAccessView.as_view()),
] + router.urls
