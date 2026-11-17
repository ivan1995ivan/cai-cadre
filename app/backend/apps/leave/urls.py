from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("rights", views.LeaveRightViewSet, basename="leave-right")
router.register("adjustments", views.LeaveAdjustmentViewSet, basename="leave-adjustment")
router.register("schedules", views.LeaveScheduleViewSet, basename="leave-schedule")
router.register("schedule-lines", views.LeaveScheduleLineViewSet, basename="leave-schedule-line")
router.register("requests", views.LeaveRequestViewSet, basename="leave-request")
router.register("sick-leaves", views.SickLeaveViewSet, basename="sick-leave")

urlpatterns = [
    path("balances/", views.BalanceListView.as_view()),
    path("balance/<int:employee>/", views.EmployeeBalanceView.as_view()),
    path("settings/", views.SettingsView.as_view()),
    path("social-dates/", views.SocialDatesView.as_view()),
] + router.urls
