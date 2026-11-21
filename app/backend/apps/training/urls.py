from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("records", views.TrainingRecordViewSet, basename="training-record")
router.register("plans", views.PlanViewSet, basename="training-plan")
router.register("plan-lines", views.PlanLineViewSet, basename="training-plan-line")

urlpatterns = router.urls
