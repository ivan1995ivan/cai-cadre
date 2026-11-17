from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register("users", views.UserViewSet, basename="user")
router.register("roles", views.RoleViewSet, basename="role")
router.register("user-lookup", views.UserLookupViewSet, basename="user-lookup")

from .auth import SessionRefreshSerializer


class RefreshView(TokenRefreshView):
    serializer_class = SessionRefreshSerializer
    public = True


urlpatterns = [
    path("auth/login/", views.LoginView.as_view()),
    path("auth/refresh/", RefreshView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("auth/change-password/", views.ChangePasswordView.as_view()),
    path("ui-prefs/", views.UiPrefsView.as_view()),
    path("ui-prefs/<str:key>/", views.UiPrefsView.as_view()),
    path("ui-defaults/", views.UiDefaultsView.as_view()),
    path("ui-defaults/<str:key>/", views.UiDefaultsView.as_view()),
    path("export/xlsx/", views.XlsxExportView.as_view()),
] + router.urls
