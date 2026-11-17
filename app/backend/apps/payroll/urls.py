from django.urls import path
from rest_framework.routers import DefaultRouter

from . import payment_views, views

router = DefaultRouter()
router.register("constants", views.PayConstantViewSet, basename="pay-constant")
router.register("types", views.PayTypeViewSet, basename="pay-type")
router.register("employee-items", views.EmployeePayItemViewSet, basename="employee-pay-item")
router.register("exemptions", views.ExemptionRequestViewSet, basename="exemption-request")
router.register("payrolls", views.PayrollViewSet, basename="payroll")
router.register("items", views.PayrollItemViewSet, basename="payroll-item")
router.register("payments", payment_views.PaymentViewSet, basename="payment")
router.register("payment-lines", payment_views.PaymentLineViewSet, basename="payment-line")

urlpatterns = [
    path("debts/", payment_views.DebtsView.as_view()),
    path("annual-card/<int:employee>/", payment_views.AnnualCardView.as_view()),
    path("tax-reports/settings/", payment_views.TaxSettingsView.as_view()),
    path("tax-reports/<str:report>/", payment_views.TaxReportView.as_view()),
] + router.urls
