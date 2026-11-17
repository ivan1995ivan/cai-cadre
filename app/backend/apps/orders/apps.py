from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = "apps.orders"
    label = "orders"
    verbose_name = "Ordine"

    def ready(self):
        from apps.core.audit import register
        from apps.printing import views as printing_views

        from . import printing
        from .models import Incentive, Order, OrderItem, Sanction

        register(Order)
        register(OrderItem, parent="order", exclude={"result"})
        register(Sanction, parent="employee")
        register(Incentive, parent="employee")
        printing_views.SAMPLE_BUILDERS["order"] = printing.sample
        printing_views.SAMPLE_BUILDERS["order_extract"] = printing.sample_extract
        printing_views.SAMPLE_BUILDERS["orders_register"] = printing.sample_register
