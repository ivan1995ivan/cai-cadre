from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import engine, mail


def _require_settings(user):
    if not user.has_crm_perm("settings.edit"):
        raise PermissionDenied("Setările le schimbă administratorul.")


class AlertListView(APIView):
    """„Termene și alerte”: alertele care privesc utilizatorul (administratorul le vede pe toate)."""

    def get(self, request):
        today = timezone.localdate()
        kinds = request.query_params.get("kind")
        alerts = engine.collect(today, kinds.split(",") if kinds else None)
        mine = alerts if request.user.is_crm_admin else engine.for_user(request.user, alerts)
        return Response({"today": today, "rows": [a.as_dict(today) for a in mine], "counts": engine.counts_by_kind(mine)})


class AlertSettingsView(APIView):
    def get(self, request):
        return Response({**engine.get_settings(), "kinds": {k: {"audience": v[2]} for k, v in engine.KINDS.items()}})

    def put(self, request):
        _require_settings(request.user)
        return Response(engine.save_settings(request.data))


class AlertRunView(APIView):
    """Trimite acum notificările (de regulă le trimite sarcina de noapte)."""

    def post(self, request):
        _require_settings(request.user)
        return Response(engine.run())


class SmtpView(APIView):
    def get(self, request):
        _require_settings(request.user)
        return Response(mail.get_smtp())

    def put(self, request):
        _require_settings(request.user)
        return Response(mail.save_smtp(request.data))


class SmtpTestView(APIView):
    def post(self, request):
        _require_settings(request.user)
        to = str(request.data.get("to") or request.user.email or "").strip()
        if not to:
            raise ValidationError({"to": "Scrieți adresa la care se trimite proba."})
        try:
            ok = mail.send([to], "CAI CADRE: proba e-mailului", "Serverul de e-mail este configurat corect.")
        except Exception as exc:  # noqa: BLE001 — mesajul serverului ajută la configurare
            raise ValidationError({"detail": f"Nu s-a trimis: {exc}"}) from exc
        if not ok:
            raise ValidationError({"detail": "Trimiterea pe e-mail nu este pornită sau serverul lipsește."})
        return Response({"sent": to})


class DashboardStatsView(APIView):
    """Indicatorii panoului de start (PLAN.md §5.9, p.15), pe secțiile utilizatorului dacă vede doar secțiile lui."""

    def get(self, request):
        from apps.leave.models import Absence, LeaveRequest
        from apps.org import services as org_services
        from apps.orders.models import Order, OrderItem
        from apps.staff import services as staff
        from apps.staff.models import Employee

        user, today = request.user, timezone.localdate()
        out = {"today": today}
        if user.has_crm_perm("employees.view"):
            ids = staff.visible_subdivision_ids(user, "employees")
            people = staff.scope_employees(Employee.objects.filter(status__in=("active", "suspended")), user)
            out["employees"] = people.count()
            out["suspended"] = people.filter(status="suspended").count()
            absences = Absence.objects.filter(date_from__lte=today, date_to__gte=today, employee__in=people)
            out["on_leave"] = absences.exclude(kind__in=("sick", "travel", "training")).values("employee").distinct().count()
            out["sick"] = absences.filter(kind="sick").values("employee").distinct().count()
            out["travel"] = absences.filter(kind__in=("travel", "training")).values("employee").distinct().count()
            occ = org_services.occupancy(on_date=today)
            rows = [r for r in occ["rows"] if ids is None or r["subdivision_id"] in ids]
            approved = sum((Decimal(r["approved"]) for r in rows), Decimal("0"))
            occupied = sum((Decimal(r["occupied"]) for r in rows), Decimal("0"))
            out["units"] = {"approved": float(approved), "occupied": float(occupied),
                            "vacant": float(sum((max(Decimal(r["vacant"]), Decimal("0")) for r in rows), Decimal("0")))}
            soon = today + timedelta(days=7)
            out["birthdays"] = [{"id": e.pk, "name": e.full_name(), "date": _this_year(e.birth_date, today)}
                                for e in people.filter(birth_date__isnull=False)
                                if today <= _this_year(e.birth_date, today) <= soon]
        if user.has_crm_perm("orders.view"):
            out["orders_draft"] = Order.objects.filter(status="draft").count() if user.has_crm_perm("orders.approve") else None
            out["unacknowledged"] = OrderItem.objects.filter(order__status="signed", acknowledged_on__isnull=True,
                                                             employee__isnull=False, order__signed_at__date__gte=today - timedelta(days=90)).count()
        if user.has_crm_perm("leave.view"):
            reqs = LeaveRequest.objects.filter(status="new", deletion_mark=False)
            ids = staff.visible_subdivision_ids(user, "leave")
            if ids is not None:
                reqs = reqs.filter(Q(employee__employments__subdivision_id__in=ids)).distinct()
            out["leave_requests"] = reqs.count()
        alerts = engine.collect(today)
        mine = alerts if user.is_crm_admin else engine.for_user(user, alerts)
        out["alerts"] = {"total": len(mine), "month": sum(1 for a in mine if a.due <= today + timedelta(days=30)),
                         "urgent": sum(1 for a in mine if a.level == "warning"),
                         "top": [a.as_dict(today) for a in sorted(mine, key=lambda a: (a.level != "warning", a.due))[:8]]}
        return Response(out)


def _this_year(birth, today):
    try:
        return birth.replace(year=today.year)
    except ValueError:
        return birth.replace(year=today.year, day=28)
