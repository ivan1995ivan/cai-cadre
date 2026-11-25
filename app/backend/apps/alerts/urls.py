from django.urls import path

from . import views

urlpatterns = [
    path("", views.AlertListView.as_view()),
    path("settings/", views.AlertSettingsView.as_view()),
    path("run/", views.AlertRunView.as_view()),
    path("smtp/", views.SmtpView.as_view()),
    path("smtp/test/", views.SmtpTestView.as_view()),
    path("dashboard/", views.DashboardStatsView.as_view()),
    path("calendar/", views.CalendarView.as_view()),
]
