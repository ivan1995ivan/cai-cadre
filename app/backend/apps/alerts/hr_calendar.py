"""Calendarul de personal pe lună (Principal → Calendarul): pe zile — absențele (concedii, boli, deplasări, staționare),
cursele, zilele de naștere, sfârșitul probei, contractele pe termen care expiră, actele care expiră; sărbătorile și zilele de
odihnă. Fiecare fel apare doar pentru cine are dreptul lui și doar pentru angajații pe care îi vede (subdiviziunile lui)."""
from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone


def month_bounds(year: int, month: int):
    first = date(year, month, 1)
    return first, date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)


def _this_year(birth, year):
    try:
        return birth.replace(year=year)
    except ValueError:  # 29 februarie într-un an fără ea
        return date(year, 3, 1)


def events(user, year: int, month: int) -> dict:
    from apps.leave.models import Absence
    from apps.org import calendar
    from apps.org.models import Holiday
    from apps.staff import services as staff
    from apps.staff.models import Employee, EmployeeDocument, Employment

    first, last = month_bounds(year, month)
    can = user.has_crm_perm
    out = []

    def add(kind, start, end, title, employee=None, link=""):
        out.append({"kind": kind, "from": max(start, first), "to": min(end, last), "title": title,
                    "employee": employee.pk if employee else None, "name": employee.full_name() if employee else "", "link": link})

    people = staff.scope_employees(Employee.objects.all(), user) if can("employees.view") or can("leave.view") else Employee.objects.none()
    if can("leave.view") or can("sick_leave.view"):
        visible_leave = staff.scope_employees(Employee.objects.all(), user, "leave")
        for a in (Absence.objects.filter(date_from__lte=last, date_to__gte=first, employee__in=visible_leave)
                  .select_related("employee")):
            if a.kind == "sick" and not can("sick_leave.view") or a.kind != "sick" and not can("leave.view"):
                continue
            kind = "sick" if a.kind == "sick" else "travel" if a.kind in ("travel", "training") else "idle" \
                if a.kind in ("idle", "tech_unemployment") else "leave"
            add(kind, a.date_from, a.date_to, a.get_kind_display(), a.employee, f"/employees/{a.employee_id}?tab=leave")
    if can("employees.view"):
        active = people.filter(status__in=("active", "suspended"))
        for e in active.filter(birth_date__isnull=False):
            day = _this_year(e.birth_date, year)
            if first <= day <= last:
                add("birthday", day, day, f"{year - e.birth_date.year} ani", e, f"/employees/{e.pk}")
        for j in Employment.objects.filter(employee__in=active).exclude(status="ended").select_related("employee"):
            if j.probation_until and first <= j.probation_until <= last:
                add("probation", j.probation_until, j.probation_until, "Sfârșitul perioadei de probă", j.employee,
                    f"/employees/{j.employee_id}?tab=jobs")
            if j.date_to and first <= j.date_to <= last:
                add("contract", j.date_to, j.date_to, "Expiră contractul pe durată determinată", j.employee,
                    f"/employees/{j.employee_id}?tab=jobs")
        if can("employees.sensitive"):
            for d in (EmployeeDocument.objects.filter(employee__in=active, expiry_date__gte=first, expiry_date__lte=last)
                      .select_related("employee", "doc_type")):
                name = d.doc_type.name_ro if d.doc_type_id else d.title
                add("document", d.expiry_date, d.expiry_date, f"Expiră: {name}", d.employee, f"/employees/{d.employee_id}?tab=documents")
    from apps.core.models import Company

    if can("transport.view") and getattr(Company.get(), "transport_enabled", False):
        from apps.transport.models import Trip

        visible = staff.scope_employees(Employee.objects.all(), user, "transport")
        for t in (Trip.objects.filter(departure__date__lte=last, arrival__date__gte=first, deletion_mark=False)
                  .filter(Q(driver__employee__in=visible) | Q(co_driver__employee__in=visible)).select_related("driver__employee")):
            add("trip", timezone.localtime(t.departure).date(), timezone.localtime(t.arrival).date(),
                f"Cursa {t.number or ''} {t.route or ''}".strip(), t.driver.employee, f"/transport/trips/{t.pk}")
    calendar.holidays_between(first, last)
    holidays = [{"date": h.date, "name": h.name} for h in Holiday.objects.filter(date__gte=first, date__lte=last).order_by("date")]
    out.sort(key=lambda e: (e["from"], e["kind"], e["name"]))
    return {"year": year, "month": month, "events": out, "holidays": holidays}
