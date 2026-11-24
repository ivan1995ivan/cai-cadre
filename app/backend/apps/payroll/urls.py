from django.urls import path
from rest_framework.routers import DefaultRouter

from . import it_park_views, meal_views, payment_views, views

router = DefaultRouter()
router.register("constants", views.PayConstantViewSet, basename="pay-constant")
router.register("types", views.PayTypeViewSet, basename="pay-type")
router.register("employee-items", views.EmployeePayItemViewSet, basename="employee-pay-item")
router.register("occupation-items", views.OccupationPayItemViewSet, basename="occupation-pay-item")
router.register("item-changes", views.PayItemChangeViewSet, basename="pay-item-change")
router.register("exemptions", views.ExemptionRequestViewSet, basename="exemption-request")
router.register("payrolls", views.PayrollViewSet, basename="payroll")
router.register("items", views.PayrollItemViewSet, basename="payroll-item")
router.register("payments", payment_views.PaymentViewSet, basename="payment")
router.register("payment-lines", payment_views.PaymentLineViewSet, basename="payment-line")
router.register("fiscal-regimes", it_park_views.FiscalRegimeViewSet, basename="fiscal-regime")
router.register("meal-vouchers", meal_views.MealVoucherViewSet, basename="meal-voucher")

urlpatterns = [
    path("debts/", payment_views.DebtsView.as_view()),
    path("annual-card/<int:employee>/", payment_views.AnnualCardView.as_view()),
    path("tax-reports/settings/", payment_views.TaxSettingsView.as_view()),
    path("it-park/", it_park_views.ItParkYearView.as_view()),
    path("it-park/<int:year>/<int:month>/", it_park_views.ItParkMonthView.as_view()),
    path("tax-reports/<str:report>/", payment_views.TaxReportView.as_view()),
] + router.urls
