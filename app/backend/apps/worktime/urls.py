from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("shifts", views.ShiftTypeViewSet, basename="shift-type")
router.register("hour-types", views.HourTypeViewSet, basename="hour-type")
router.register("job-hour-rates", views.JobHourRateViewSet, basename="job-hour-rate")
router.register("occupation-hour-rates", views.OccupationHourRateViewSet, basename="occupation-hour-rate")
router.register("schedules", views.WorkScheduleViewSet, basename="work-schedule")
router.register("calendar-days", views.CalendarDayViewSet, basename="calendar-day")
router.register("job-schedules", views.JobScheduleViewSet, basename="job-schedule")
router.register("rosters", views.RosterViewSet, basename="roster")
router.register("roster-lines", views.RosterLineViewSet, basename="roster-line")
router.register("timesheets", views.TimesheetViewSet, basename="timesheet")
router.register("timesheet-lines", views.TimesheetLineViewSet, basename="timesheet-line")

urlpatterns = [
    path("calendar/", views.CalendarView.as_view()),
    path("settings/", views.SettingsView.as_view()),
    path("employee-month/<int:employee>/", views.EmployeeMonthView.as_view()),
    path("timesheets/<int:pk>/import/<str:code>/", views.TimesheetImportView.as_view()),
    path("timesheets/<int:pk>/import/<str:code>/template/", views.TimesheetImportView.as_view()),
] + router.urls
