"""Datele demo — o întreprindere privată fictivă („Demo Producție” SRL), făcută prin serviciile modulelor; rapoartele, cabinetul
și salariul lucrează pe ea, iar în ce se creează nu apare nimic de spital sau de stat."""
import re
import unicodedata
from io import StringIO

import pytest
from django.core.management import call_command

from apps.core import demo
from apps.core.models import Company
from apps.org.models import Occupation, StaffList, Subdivision
from apps.payroll.models import Payment, Payroll
from apps.staff.models import Employee, Employment, FamilyMember
from apps.users.models import User

DEMO_USERS = {"cadre", "inspector", "director", "sef.productie", "contabil", "angajat"}
# termenii de spital / de stat care nu au ce căuta într-un SRL (cuvinte întregi, fără diacritice și majuscule)
HOSPITAL = re.compile(r"\b(spital\w*|imsp|ministerul sanatatii|medic|medici|medicul|asistent medical|infermier\w*|infirmier\w*|"
                      r"pat|paturi|garda|garzi|vaccin\w*|emc|rezident\w*|categori[ae] de calificare|traumatolog\w*|"
                      r"anestez\w*|reanimat\w*|farmac\w*|laborant\w*|sec[tț]ia|usmf|amt)\b")


def _texts():
    """Toate denumirile și textele libere puse de datele demo (cele din clasificatoarele livrate nu sunt ale demo-ului)."""
    from apps.health.models import MedicalExam, SafetyBriefing
    from apps.leave.models import SickLeave
    from apps.orders.models import Order, OrderItem
    from apps.staff.models import Education, PriorExperience
    from apps.training.models import TrainingPlanLine, TrainingRecord

    c = Company.get()
    out = [c.name_ro, c.name_ru, c.name_en, c.legal_address, c.director_position_ro, c.hr_head_position_ro]
    out += [f"{s.name_ro} {s.head_name}" for s in Subdivision.objects.all()]
    out += [f"{s.approved_by} {s.basis}" for s in StaffList.objects.all()]
    out += [f"{o.basis} {o.title}" for o in Order.objects.all()] + list(OrderItem.objects.values_list("text", flat=True))
    out += [j.occupation.name_ro for j in Employment.objects.select_related("occupation")]
    out += [f"{e.institution} {e.specialty.name_ro if e.specialty_id else ''}" for e in Education.objects.select_related("specialty")]
    out += [f"{p.organization} {p.position}" for p in PriorExperience.objects.all()]
    out += [f"{t.title} {t.provider}" for t in TrainingRecord.objects.all()]
    out += [f"{t.title} {t.provider}" for t in TrainingPlanLine.objects.all()]
    out += [f"{m.institution}" for m in MedicalExam.objects.all()] + [f"{b.instructor} {b.topic}" for b in SafetyBriefing.objects.all()]
    out += list(SickLeave.objects.values_list("issued_by", flat=True))
    out += [f"{u.first_name} {u.last_name} {u.email}" for u in User.objects.all()]
    return out


def _hospital_terms():
    def plain(text):
        return "".join(ch for ch in unicodedata.normalize("NFKD", (text or "").lower()) if not unicodedata.combining(ch))

    return sorted({m.group(0) for text in _texts() for m in HOSPITAL.finditer(plain(text))})


def test_demo_company(seeded, admin_client, client_for):
    out = StringIO()
    call_command("crm_demo", stdout=out)
    assert "Datele demo sunt gata" in out.getvalue() and demo.DEMO_PASSWORD in out.getvalue()
    company = Company.get()
    assert (company.name_ro, company.legal_form, company.caem) == ("Demo Producție", "SRL", "2511")
    assert re.fullmatch(r"\d{13}", company.idno) and company.director == "Gheorghe Ciobanu"
    assert not company.military_enabled  # evidența militară rămâne oprită (doar datele câtorva angajați)

    # structura: șase subdiviziuni de sus, atelierul cu două sectoare, unul cu condiții vătămătoare
    subs = {s.code: s for s in Subdivision.objects.all()}
    assert set(subs) == {"ADM", "CONT", "VNZ", "ATL", "ATL1", "ATL2", "DEP", "TRN"}
    assert {s.code for s in subs.values() if s.parent_id is None} == {"ADM", "CONT", "VNZ", "ATL", "DEP", "TRN"}
    assert {s.code for s in subs["ATL"].children.all()} == {"ATL1", "ATL2"}
    harmful = [s for s in subs.values() if s.harmful]
    assert [(s.code, s.extra_leave_days, s.reduced_hours) for s in harmful] == [("ATL2", 4, 35)]
    assert subs["DEP"].kind == "warehouse" and subs["ATL"].kind == "workshop"

    # funcțiile — doar din clasificatorul livrat (nicio funcție creată de demo), cu cod CORM
    from apps.org import seed as org_seed

    shipped = {ro for _code, ro, *_rest in org_seed.OCCUPATIONS}
    assert set(Occupation.objects.values_list("name_ro", flat=True)) == shipped
    used = Occupation.objects.filter(employment__isnull=False).distinct()
    assert used.exclude(name_ro="Director adjunct").filter(code="").count() == 0

    # statele de personal, aprobate prin ordinul directorului (semnat)
    sl = StaffList.objects.get()
    assert sl.status == "approved" and sl.approved_by.startswith("Ordinul nr.")
    from apps.orders.models import Order

    assert Order.objects.get(order_type__code="staff_list").status == "signed"
    assert Order.objects.filter(order_type__code="bonus", status="signed").count() == 1

    # oamenii: 50–70 de angajați de bază, cumuluri interne și externe, un contract de prestări servicii, dosarele
    result_main = Employment.objects.filter(kind="main").count()
    assert 50 <= result_main <= 70
    kinds = {k: Employment.objects.filter(kind=k).count() for k in ("internal", "external", "contractor")}
    assert kinds == {"internal": 2, "external": 2, "contractor": 1}
    assert Employee.objects.count() == result_main + 3
    assert Employee.objects.filter(documents__is_identity=True).distinct().count() == Employee.objects.count()
    assert Employee.objects.filter(education__isnull=False).distinct().count() == Employee.objects.count()
    assert FamilyMember.objects.filter(dependent=True, relation__code__in=("son", "daughter")).count() >= 10
    assert FamilyMember.objects.filter(dependent=True, relation__code__in=("mother", "father")).exists()
    assert Employee.objects.filter(documents__doc_type__code="driving_licence").count() >= 6
    assert Employee.objects.filter(military__isnull=False).exists()
    from apps.worktime.models import JobSchedule, Roster

    assert JobSchedule.objects.filter(schedule__code="ZN", employment__subdivision__code="ATL1").count() >= 8
    assert Roster.objects.get(subdivision__code="ATL").status == "approved"

    # salariul lunii trecute: calculul aprobat, îndreptarea achitată
    payroll = Payroll.objects.get()
    assert payroll.status == "approved" and payroll.lines.count() >= result_main
    assert Payment.objects.filter(payroll=payroll, kind="salary", status="paid").count() == 1

    # utilizatorii: câte unul pe rol, cu parola demo; administratorul e cel existent (din asistent)
    assert set(User.objects.exclude(username="admin").values_list("username", flat=True)) == DEMO_USERS
    assert User.objects.get(username="director").check_password(demo.DEMO_PASSWORD)
    assert demo.has_business_data()
    with pytest.raises(demo.DemoError):
        demo.run()

    # rapoartele și cabinetul merg pe datele demo
    assert admin_client.get("/api/reports/structure/").status_code == 200
    total = admin_client.get("/api/alerts/dashboard/").data["employees"]
    assert total >= 50
    angajat = client_for(User.objects.get(username="angajat"))
    assert angajat.get("/api/portal/profile/").data["full_name"]
    sef = client_for(User.objects.get(username="sef.productie"))
    assert 20 <= sef.get("/api/alerts/dashboard/").data["employees"] < total  # atelierul cu sectoarele

    assert _hospital_terms() == []


def test_demo_without_admin_creates_one(seeded):
    """crm_demo pe o bază fără asistentul de instalare (fără administrator) face și utilizatorul `admin`."""
    result = demo.run()
    assert set(result["users"]) == DEMO_USERS | {"admin"}
    assert User.objects.get(username="admin").roles.filter(code="admin").exists()


def test_demo_keeps_company_from_setup(seeded):
    """Ce s-a scris în asistentul de instalare rămâne; demo completează doar câmpurile goale."""
    c = Company.get()
    c.name_ro, c.idno = "Firma Clientului", "1002600000000"
    c.save()
    demo.run()
    c = Company.objects.get(pk=1)
    assert (c.name_ro, c.idno, c.caem) == ("Firma Clientului", "1002600000000", "2511")


def test_demo_year(seeded, admin_client):
    """Datele pe un an: fiecare lună din noiembrie anul trecut până azi are pontaj, calcul aprobat (luna curentă — ciornă),
    avans și plată; ordinele anului sunt semnate; graficul concediilor e aprobat."""
    from django.utils import timezone

    from apps.core import demo_year
    from apps.leave.models import LeaveSchedule
    from apps.orders.models import Order
    from apps.worktime.models import Roster, Timesheet

    with pytest.raises(demo.DemoError):
        demo_year.run()  # fără crm_demo nu are pe ce lucra
    demo.run()
    signed_before = Order.objects.filter(status="signed").exclude(order_type__code="bonus").count()  # statele rămân
    out = StringIO()
    call_command("crm_demo_year", stdout=out)
    assert "Datele pe an sunt gata" in out.getvalue()
    today = timezone.localdate()
    months = 2 + today.month
    top = Subdivision.objects.filter(parent__isnull=True).count()
    assert top == 6
    assert Payroll.objects.count() == months and Payroll.objects.filter(status="approved").count() == months - 1
    current = Payroll.objects.get(year=today.year, month=today.month)
    assert current.status == "draft" and current.lines.count() > 60 and all(ln.net > 0 for ln in current.lines.all())
    assert Payment.objects.filter(kind="salary", status="paid").count() == months - 1
    assert Payment.objects.filter(kind="advance", status="paid").count() >= months - 1
    assert Timesheet.objects.filter(status="closed").count() == top * (months - 1)
    assert Roster.objects.filter(subdivision__code="ATL", status="approved").count() == months - 1
    signed = Order.objects.filter(status="signed").count() - signed_before
    assert signed > 20 and Order.objects.filter(order_type__code="hire", status="signed").count() == 2
    assert Order.objects.filter(order_type__code="allowance", status="signed").exists()
    assert LeaveSchedule.objects.filter(year=today.year, status="approved").count() == top
    with pytest.raises(demo.DemoError):
        demo_year.run()
    assert admin_client.get("/api/payroll/payrolls/").status_code == 200
    assert admin_client.get(f"/api/payroll/payments/?year={today.year}").status_code == 200
    assert _hospital_terms() == []
