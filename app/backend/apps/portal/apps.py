from django.apps import AppConfig


class PortalConfig(AppConfig):
    name = "apps.portal"
    label = "portal"
    verbose_name = "Cabinetul angajatului"

    def ready(self):
        from apps.leave import services as leave_services
        from apps.orders import services as order_services

        from . import notify

        hooks = leave_services.REQUEST_HOOKS
        for event, fn in (("created", notify.leave_created), ("decided", notify.leave_decided), ("ordered", notify.leave_ordered)):
            if fn not in hooks[event]:
                hooks[event].append(fn)
        if notify.order_signed not in order_services.AFTER_SIGN:
            order_services.AFTER_SIGN.append(notify.order_signed)
