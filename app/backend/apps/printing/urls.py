from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("print-templates", views.PrintTemplateViewSet, basename="print-template")

urlpatterns = [
    path("print/preview/", views.PreviewView.as_view()),
] + router.urls
