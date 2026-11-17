from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.StatusView.as_view()),
    path("drivers/", views.DriversView.as_view()),
    path("test/", views.TestConnectionView.as_view()),
    path("create-db/", views.CreateDatabaseView.as_view()),
    path("install/", views.InstallView.as_view()),
]
