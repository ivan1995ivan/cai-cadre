"""Notificările cabinetului: în clopoțel și (dacă e pornit serverul de e-mail) un e-mail scurt."""
import logging

from apps.core.models import Notification

log = logging.getLogger(__name__)


def send(users, title: str, message: str = "", link: str = "", kind: str = "portal", level: str = "info"):
    from apps.alerts import mail

    users = [u for u in dict.fromkeys(users) if u is not None and u.is_active]
    for u in users:
        Notification.send(u, title, message, level=level, kind=kind, link=link)
    to = [u.email for u in users if u.email]
    if to:
        try:
            mail.send(to, f"CAI CADRE: {title}", f"{message}\n\nDeschideți CAI CADRE pentru detalii.")
        except Exception:  # noqa: BLE001 — e-mailul e în plus; notificarea din sistem a rămas
            log.exception("Notificarea pe e-mail nu s-a trimis")


def hr_users():
    """Cadrele: cine editează angajații în toată întreprinderea."""
    from apps.users.models import User

    return [u for u in User.objects.filter(is_active=True) if not u.is_crm_admin and u.has_crm_perm("employees.edit")
            and u.data_scope("employees") == "all"]


def heads_of(employee):
    """Șefii secțiilor angajatului (aprobă cererile de concediu)."""
    subs = {e.subdivision_id for e in employee.employments.all() if e.status != "ended"}
    out = []
    from apps.org.models import Subdivision

    for sub in Subdivision.objects.filter(pk__in=subs).prefetch_related("users"):
        out += [u for u in sub.users.all() if u.has_crm_perm("leave.approve")]
    return out


# --- abonamentele la evenimentele modulelor ---------------------------------------------------------------------------
def leave_created(req):
    if req.created_by_id and req.created_by_id != getattr(req.employee.user, "pk", None):
        return  # cererea pusă de cadre — șeful o vede în lista lui
    send(heads_of(req.employee) or hr_users(), "Cerere de concediu nouă",
         f"{req.employee.full_name()}: {req.get_kind_display().lower()} {req.date_from:%d.%m.%Y} – {req.date_to:%d.%m.%Y} ({req.days} zile)",
         "/leave?tab=requests", kind="portal_leave", level="task")


def leave_decided(req):
    user = req.employee.user
    if user is None:
        return
    verdict = "aprobată" if req.status == "approved" else "respinsă"
    note = f" — {req.decision_note}" if req.decision_note else ""
    send([user], f"Cererea de concediu este {verdict}",
         f"{req.get_kind_display()} {req.date_from:%d.%m.%Y} – {req.date_to:%d.%m.%Y}{note}", "/portal?tab=requests",
         kind="portal_leave", level="success" if req.status == "approved" else "warning")
    if req.status == "approved":
        send(hr_users(), "Cerere de concediu aprobată — de făcut ordinul",
             f"{req.employee.full_name()}: {req.get_kind_display().lower()} {req.date_from:%d.%m.%Y} – {req.date_to:%d.%m.%Y}",
             "/leave?tab=requests", kind="portal_leave", level="task")


def leave_ordered(req):
    user = req.employee.user
    if user is not None and req.order_item_id:
        send([user], "Ordinul pentru concediu este emis", f"Nr. {req.order_item.order.number or '—'}: "
             f"{req.get_kind_display().lower()} {req.date_from:%d.%m.%Y} – {req.date_to:%d.%m.%Y}", "/portal?tab=orders",
             kind="portal_order")


def order_signed(order):
    """Ordinul semnat: fiecare angajat din el primește „luați cunoștință”."""
    for item in order.items.select_related("employee__user"):
        user = item.employee.user if item.employee_id else None
        if user is not None and not item.acknowledged_on:
            send([user], "Ordin nou — luați cunoștință", f"Nr. {order.number} din {order.date:%d.%m.%Y}: {order.order_type.name_ro}",
                 "/portal?tab=orders", kind="portal_order", level="task")


def request_created(req):
    send(hr_users(), "Cerere nouă în cabinet", f"{req.employee.full_name()}: {req.get_kind_display().lower()}",
         "/employee-requests", kind="portal_request", level="task")


def request_handled(req):
    user = req.employee.user
    if user is not None:
        state = {"done": "este gata", "rejected": "este respinsă", "in_work": "este în lucru"}.get(req.status, req.get_status_display())
        send([user], f"Cererea „{req.get_kind_display()}” {state}", req.answer, "/portal?tab=requests", kind="portal_request",
             level="success" if req.status == "done" else "info")
