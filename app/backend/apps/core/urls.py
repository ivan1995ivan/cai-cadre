from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("bank-accounts", views.BankAccountViewSet, basename="bank-account")
router.register("currencies", views.CurrencyViewSet, basename="currency")
router.register("exchange-rates", views.ExchangeRateViewSet, basename="exchange-rate")
router.register("vat-rates", views.VatRateViewSet, basename="vat-rate")
router.register("number-series", views.NumberSeriesViewSet, basename="number-series")
router.register("payment-methods", views.PaymentMethodViewSet, basename="payment-method")
router.register("audit-log", views.AuditLogViewSet, basename="audit-log")
router.register("notifications", views.NotificationViewSet, basename="notification")
router.register("localities", views.LocalityViewSet, basename="locality")
router.register("banks", views.BankViewSet, basename="bank")

urlpatterns = [
    path("public/branding/", views.BrandingView.as_view()),
    path("company/", views.CompanyView.as_view()),
    path("company/images/<str:field>/", views.CompanyImageView.as_view()),
    path("settings/menu/", views.MenuLayoutView.as_view()),
    path("settings/localities/", views.LocalitiesLoadView.as_view()),
    path("settings/banks/", views.BanksLoadView.as_view()),
    path("settings/required-fields/", views.RequiredFieldsView.as_view()),
    path("license/", views.LicenseView.as_view()),
    path("settings/periods/", views.PeriodSettingsView.as_view()),
    path("history/", views.HistoryView.as_view()),
    path("history/<int:pk>/restore/", views.HistoryRestoreView.as_view()),
    path("comments/", views.CommentsView.as_view()),
    path("system-info/", views.SystemInfoView.as_view()),
    path("online/", views.OnlineView.as_view()),
    path("dashboard/", views.DashboardView.as_view()),
] + router.urls
