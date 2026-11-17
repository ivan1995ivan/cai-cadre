"""Cabinetul angajatului: datele proprii, ordinele cu „am luat cunoștință”, cererile, fișele de calcul.
Totul se ia din angajatul legat de utilizator (Employee.user); un angajat nu vede datele altuia."""
import secrets

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.leave import balance
from apps.leave import services as leave_services
from apps.leave.models import Absence, LeaveRequest
from apps.leave.serializers import LeaveRequestSerializer
from apps.orders.models import OrderItem
from apps.staff import services as staff
from apps.staff.models import Employee

from . import notify
from .models import EmployeeRequest

NOT_LINKED = "Contul nu este legat de un angajat — adresați-vă secției resurse umane."


def me(request) -> Employee:
    emp = Employee.objects.filter(user=request.user).first()
    if emp is None:
        raise NotFound(NOT_LINKED)
    return emp


def _d(day):
    return day.isoformat() if day else None


class ProfileView(APIView):
    """Datele mele: raporturile de muncă, vechimea, soldul concediului, absențele apropiate, ce am de făcut."""

    perm_module = "portal"

    def get(self, request):
        emp = me(request)
        lang = request.user.language or "ro"
        today = timezone.localdate()
        jobs = [{"subdivision": j.subdivision.local_name(lang), "occupation": j.occupation.local_name(lang), "kind": j.get_kind_display(),
                 "rate": float(j.rate) * 100, "date_from": _d(j.date_from), "date_to": _d(j.date_to), "status": j.get_status_display()}
                for j in emp.employments.select_related("subdivision", "occupation").exclude(status="ended")]
        bal = balance.balance(emp, today)
        absences = [{"kind": a.get_kind_display(), "date_from": _d(a.date_from), "date_to": _d(a.date_to), "days": a.days}
                    for a in Absence.objects.filter(employee=emp, date_to__gte=today).order_by("date_from")[:6]]
        return Response({
            "id": emp.pk, "full_name": emp.full_name(), "tab_number": emp.tab_number, "birth_date": _d(emp.birth_date),
            "phone": emp.phone, "email": emp.email, "address": emp.address, "jobs": jobs,
            "seniority": staff.seniority_text(staff.seniority(emp, today)["total"], lang),
            "leave": {"available": bal["available"], "remaining": bal["remaining"], "current": bal["current"]},
            "absences": absences,
            "todo": {"orders": OrderItem.objects.filter(employee=emp, order__status="signed", acknowledged_on__isnull=True).count(),
                     "requests": LeaveRequest.objects.filter(employee=emp, status__in=("new", "approved"), deletion_mark=False).count()
                     + EmployeeRequest.objects.filter(employee=emp, status__in=("new", "in_work")).count()},
            "payroll": _payroll_on(),
        })


def _payroll_on() -> bool:
    from apps.core.models import Company

    return Company.get().payroll_enabled


class OrdersView(APIView):
    """Ordinele mele (semnate), cu „am luat cunoștință”."""

    perm_module = "portal"

    def get(self, request):
        emp = me(request)
        items = (OrderItem.objects.filter(employee=emp, order__status="signed").select_related("order__order_type")
                 .order_by("-order__date", "-order__id"))
        return Response([{"id": i.id, "number": i.order.number, "date": _d(i.order.date), "type": i.order.order_type.name_ro,
                          "title": i.order.title, "text": i.text, "acknowledged_on": _d(i.acknowledged_on)} for i in items])

    def post(self, request):
        emp = me(request)
        item = OrderItem.objects.filter(pk=request.data.get("item"), employee=emp, order__status="signed").first()
        if item is None:
            raise NotFound()
        if not item.acknowledged_on:
            item.acknowledged_on = timezone.localdate()
            item.save(update_fields=["acknowledged_on"])
        return Response({"id": item.id, "acknowledged_on": _d(item.acknowledged_on)})


class LeaveRequestsView(APIView):
    """Cererile mele de concediu: depun, văd starea, retrag cererea neaprobată."""

    perm_module = "portal"

    def get(self, request):
        emp = me(request)
        qs = LeaveRequest.objects.filter(employee=emp).select_related("employee", "decided_by", "order_item__order")
        return Response(LeaveRequestSerializer(qs.order_by("-created_at"), many=True, context={"request": request}).data)

    @transaction.atomic
    def post(self, request):
        emp = me(request)
        ser = LeaveRequestSerializer(data={**request.data, "employee": emp.pk}, context={"request": request})
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        clash = leave_services.overlapping(emp, data["date_from"], data["date_to"]).first()
        if clash is not None:
            raise ValidationError({"date_from": f"Perioada se suprapune cu {clash.get_kind_display().lower()} "
                                                f"{clash.date_from:%d.%m.%Y}–{clash.date_to:%d.%m.%Y}."})
        req = ser.save(created_by=request.user, status="new")
        leave_services.fire("created", req)
        return Response(LeaveRequestSerializer(req, context={"request": request}).data, status=201)



class LeaveWithdrawView(APIView):
    """Retrag cererea de concediu încă neaprobată (sau respinsă)."""

    perm_module = "portal"

    def post(self, request):
        emp = me(request)
        req = LeaveRequest.objects.filter(pk=request.data.get("id"), employee=emp).first()
        if req is None:
            raise NotFound()
        if req.status not in ("new", "rejected"):
            raise ValidationError({"detail": "Cererea aprobată se retrage prin secția resurse umane."})
        req.status = "withdrawn"
        req.save(update_fields=["status"])
        return Response({"status": req.status})


class EmployeeRequestSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    tab_number = serializers.CharField(source="employee.tab_number", read_only=True)
    handled_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeRequest
        fields = ["id", "employee", "employee_name", "tab_number", "kind", "kind_label", "text", "copies", "status", "status_label",
                  "answer", "handled_by_name", "handled_at", "created_at"]
        read_only_fields = ["employee", "handled_at", "created_at"]

    def get_handled_by_name(self, obj):
        return str(obj.handled_by) if obj.handled_by_id else ""

    def validate_copies(self, value):
        if not 1 <= value <= 10:
            raise serializers.ValidationError("1–10 exemplare.")
        return value


class MyRequestsViewSet(viewsets.ModelViewSet):
    """Cererile mele (adeverințe, modificarea datelor, altele)."""

    perm_module = "portal"
    perm_actions = {"withdraw": "create"}
    serializer_class = EmployeeRequestSerializer
    pagination_class = None
    http_method_names = ["get", "post"]

    def get_queryset(self):
        return EmployeeRequest.objects.filter(employee=me(self.request)).select_related("employee", "handled_by")

    def perform_create(self, serializer):
        req = serializer.save(employee=me(self.request), created_by=self.request.user, status="new")
        transaction.on_commit(lambda: notify.request_created(req))

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        req = self.get_object()
        if req.status != "new":
            raise ValidationError({"detail": "Cererea luată în lucru nu se mai retrage."})
        req.status = "withdrawn"
        req.save(update_fields=["status"])
        return Response(self.get_serializer(req).data)


class RequestsInboxViewSet(viewsets.ModelViewSet):
    """Cererile angajaților pentru cadre: în lucru, gata (cu răspuns), respinse."""

    perm_module = "employees"
    serializer_class = EmployeeRequestSerializer
    http_method_names = ["get", "patch"]

    def get_queryset(self):
        p = self.request.query_params
        visible = staff.scope_employees(Employee.objects.all(), self.request.user)
        qs = EmployeeRequest.objects.filter(employee__in=visible).select_related("employee", "handled_by")
        if p.get("status") == "open":
            qs = qs.filter(status__in=("new", "in_work"))
        elif p.get("status"):
            qs = qs.filter(status=p["status"])
        return qs

    def perform_update(self, serializer):
        allowed = {"status", "answer"}
        if set(serializer.validated_data) - allowed:
            raise ValidationError({"detail": "Se schimbă doar starea și răspunsul."})
        if serializer.validated_data.get("status") not in (None, "in_work", "done", "rejected"):
            raise ValidationError({"status": "Starea: în lucru, gata sau respinsă."})
        req = serializer.save(handled_by=self.request.user, handled_at=timezone.now())
        transaction.on_commit(lambda: notify.request_handled(req))


class PayslipsView(APIView):
    """Fișele mele de calcul: câte una pe lună, din calculele aprobate; ?line=<id> — tiparul fișei lunii acelui rând."""

    perm_module = "portal"

    def get(self, request):
        from apps.payroll.models import PayrollLine
        from apps.payroll.printing import month_lines, print_payslips

        if not _payroll_on():
            raise NotFound()
        emp = me(request)
        lines = PayrollLine.objects.filter(employee=emp, payroll__status="approved").select_related("payroll", "employment__occupation")
        if request.query_params.get("line"):
            line = lines.filter(pk=request.query_params["line"]).first()
            if line is None:
                raise NotFound()
            year, month = line.payroll.year, line.payroll.month
            return print_payslips(request, year, month, month_lines(year, month, [emp.pk]))
        # câte un rând pe lună: impozitul și CNAM se rețin la plată, pe toată luna (apps.payroll.payments.settlement)
        from apps.payroll.payments import settlement

        months: dict = {}
        for ln in lines.order_by("-payroll__year", "-payroll__month", "id"):
            months.setdefault((ln.payroll.year, ln.payroll.month), []).append(ln)
        rows = []
        for (year, month), month_lines in months.items():
            s = settlement(year, month, employee_ids=[emp.pk]).get(emp.pk)
            rows.append({"id": month_lines[0].id, "year": year, "month": month,
                         "occupation": ", ".join(dict.fromkeys(ln.employment.occupation.name_ro for ln in month_lines)),
                         "gross": float(s["gross"]) if s else 0.0,
                         "deductions": float(s["deductions"] + s["cnam"] + s["income_tax"]) if s else 0.0,
                         "net": float(s["net"]) if s else 0.0})
        return Response(rows)


class AccessView(APIView):
    """Accesul angajatului la cabinet (pentru cadre): creează contul cu rolul „Angajat” și parola temporară, sau îl oprește."""

    perm_module = "employees"

    def _employee(self, request, pk):
        emp = Employee.objects.filter(pk=pk).select_related("user").first()
        if emp is None or not staff.can_see(emp, request.user):
            raise NotFound()
        if not request.user.has_crm_perm("users.create"):
            raise PermissionDenied("Conturile le creează cine are dreptul „Utilizatori → creare”.")
        return emp

    def get(self, request, pk):
        emp = Employee.objects.filter(pk=pk).select_related("user").first()
        if emp is None or not staff.can_see(emp, request.user):
            raise NotFound()
        u = emp.user
        return Response({"username": u.username if u else "", "active": bool(u and u.is_active),
                         "last_login": u.last_login if u else None})

    @transaction.atomic
    def post(self, request, pk):
        emp = self._employee(request, pk)
        return Response(create_access(emp))

    def delete(self, request, pk):
        emp = self._employee(request, pk)
        if emp.user_id:
            emp.user.is_active = False
            emp.user.save(update_fields=["is_active"])
        return Response({"active": False})


def create_access(emp: Employee) -> dict:
    """Contul nou (sau parola nouă) pentru cabinet; parola se arată o singură dată și se schimbă la prima intrare."""
    from apps.users.models import Role, User

    password = "-".join(secrets.token_hex(2) for _ in range(3)).upper()
    user = emp.user
    if user is None:
        base = (emp.email.split("@")[0] if emp.email else f"t{emp.tab_number}").lower()[:30] or f"t{emp.pk}"
        username, n = base, 1
        while User.objects.filter(username=username).exists():
            n += 1
            username = f"{base}{n}"
        user = User.objects.create_user(username=username, password=password, first_name=emp.first_name, last_name=emp.last_name,
                                        email=emp.email, must_change_password=True)
        role = Role.objects.filter(code="employee").first()
        if role:
            user.roles.add(role)
        emp.user = user
        emp.save(update_fields=["user"])
    else:
        user.set_password(password)
        user.is_active, user.must_change_password = True, True
        user.save(update_fields=["password", "is_active", "must_change_password"])
    return {"username": user.username, "password": password, "active": True}


class BulkAccessView(APIView):
    """Conturi pentru toți angajații în funcție fără cont (lista cu parolele se arată o singură dată)."""

    perm_module = "employees"

    @transaction.atomic
    def post(self, request):
        if not request.user.has_crm_perm("users.create"):
            raise PermissionDenied("Conturile le creează cine are dreptul „Utilizatori → creare”.")
        people = staff.scope_employees(Employee.objects.filter(status__in=("active", "suspended"), user__isnull=True), request.user)
        out = [{"employee": e.full_name(), "tab_number": e.tab_number, **create_access(e)} for e in people.order_by("last_name")]
        return Response(out)
