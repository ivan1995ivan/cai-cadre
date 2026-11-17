"""Etapa 8: datele demo — spitalul fictiv se creează prin serviciile modulelor și rapoartele lucrează pe el."""
import pytest

from apps.core import demo
from apps.payroll.models import Payroll
from apps.staff.models import Employee
from apps.users.models import User


def test_demo_hospital(seeded, admin_client, client_for):
    result = demo.run()
    assert result["employees"] >= 45 and set(result["users"]) == {"cadre", "inspector", "director", "sef.trauma", "contabil", "angajat"}
    assert Employee.objects.count() == result["employees"] + 1  # + contractul de prestări servicii
    payroll = Payroll.objects.get()
    assert payroll.status == "approved" and payroll.lines.count() >= result["employees"]
    assert demo.has_business_data()
    with pytest.raises(demo.DemoError):
        demo.run()
    # rapoartele și cabinetul merg pe datele demo
    assert admin_client.get("/api/reports/structure/").status_code == 200
    assert admin_client.get("/api/alerts/dashboard/").data["employees"] >= 45
    angajat = client_for(User.objects.get(username="angajat"))
    assert angajat.get("/api/portal/profile/").data["full_name"]
    sef = client_for(User.objects.get(username="sef.trauma"))
    assert 0 < sef.get("/api/alerts/dashboard/").data["employees"] < 20


def test_demo_year(seeded, admin_client):
    """Datele pe un an: fiecare lună din noiembrie anul trecut până azi are pontaj, calcul aprobat (luna curentă — ciornă),
    avans și plată; ordinele anului sunt semnate; graficul concediilor e aprobat."""
    from django.utils import timezone

    from apps.core import demo_year
    from apps.leave.models import LeaveSchedule
    from apps.orders.models import Order
    from apps.payroll.models import Payment
    from apps.worktime.models import Timesheet

    with pytest.raises(demo.DemoError):
        demo_year.run()  # fără crm_demo nu are pe ce lucra
    demo.run()
    stats = demo_year.run()
    today = timezone.localdate()
    months = 2 + today.month
    assert Payroll.objects.count() == months and Payroll.objects.filter(status="approved").count() == months - 1
    current = Payroll.objects.get(year=today.year, month=today.month)
    assert current.status == "draft" and current.lines.count() > 60 and all(ln.net > 0 for ln in current.lines.all())
    assert Payment.objects.filter(kind="salary", status="paid").count() == months - 1
    assert Payment.objects.filter(kind="advance", status="paid").count() >= months - 1
    assert Timesheet.objects.filter(status="closed").count() == 9 * (months - 1)
    assert Order.objects.filter(status="signed").count() == stats["ordine"] and stats["concedii"] > 40
    assert LeaveSchedule.objects.filter(year=today.year, status="approved").count() == 9
    with pytest.raises(demo.DemoError):
        demo_year.run()
    assert admin_client.get("/api/payroll/payrolls/").status_code == 200
    assert admin_client.get(f"/api/payroll/payments/?year={today.year}").status_code == 200
