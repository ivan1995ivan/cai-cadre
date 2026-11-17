from django.urls import path

from . import views

urlpatterns = [
    path("", views.CatalogView.as_view()),
    path("<slug:key>/", views.ReportView.as_view()),
    path("<slug:key>/print/", views.ReportPrintView.as_view()),
]
