from django.apps import AppConfig


class PayrollConfig(AppConfig):
    name = "apps.payroll"
    label = "payroll"
    verbose_name = "Salarizare"

    def ready(self):
        from apps.core.audit import register
        from apps.printing import views as printing_views

        from . import payment_printing, printing, salary_book  # noqa: F401 — cartea de salarii intră în catalogul de rapoarte
        from .models import EmployeePayItem, ExemptionRequest, PayConstant, Payment, PaymentLine, Payroll, PayrollItem, PayType

        register(Payment)
        register(PaymentLine, parent="payment")
        printing_views.SAMPLE_BUILDERS["payment_sheet"] = payment_printing.sample_payment
        printing_views.SAMPLE_BUILDERS["bank_list"] = payment_printing.sample_bank
        printing_views.SAMPLE_BUILDERS["annual_card"] = payment_printing.sample_annual
        register(PayConstant)
        register(PayType)
        register(EmployeePayItem, parent="employee")
        register(ExemptionRequest, parent="employee")
        register(Payroll, exclude={"totals"})
        register(PayrollItem, parent="line")
        printing_views.SAMPLE_BUILDERS["payslip"] = printing.sample_payslip
        printing_views.SAMPLE_BUILDERS["payroll_sheet"] = printing.sample_sheet
