"""Etapa S1 (SRL): ce s-a scos din spital — felul „rezident”, vechimea „în sistemul sănătății”, categoria de calificare
medicală, alertele ei, rolurile cu denumiri de spital."""
from datetime import date
from decimal import Decimal

import pytest

from apps.alerts import engine
from apps.org.models import DictItem, Occupation, Subdivision
from apps.staff import services as staff
from apps.staff.models import EMPLOYMENT_KINDS, MAIN_KINDS, Employee, PriorExperience
from apps.users.models import Role


@pytest.fixture
def org(seeded):
    return {"sub": Subdivision.objects.create(code="ADM", name_ro="Administrația"),
            "occ": Occupation.objects.create(code="241103", name_ro="Contabil")}


def test_no_resident_kind(org, admin_client):
    assert "resident" not in dict(EMPLOYMENT_KINDS) and MAIN_KINDS == ("main", "main_student")
    assert not DictItem.objects.filter(kind="employment", code="resident").exists()
    e = Employee.objects.create(tab_number="1", last_name="Popescu", first_name="Ion")
    r = admin_client.post("/api/staff/employments/", {"employee": e.pk, "kind": "resident", "subdivision": org["sub"].pk,
                                                      "occupation": org["occ"].pk, "date_from": "2026-01-01"}, format="json")
    assert r.status_code == 400 and "kind" in r.data


def test_seniority_without_healthcare(org, admin_client):
    e = Employee.objects.create(tab_number="1", last_name="Popescu", first_name="Ion")
    PriorExperience.objects.create(employee=e, organization="„Alfa” SRL", date_from=date(2015, 1, 1), date_to=date(2019, 12, 31))
    PriorExperience.objects.create(employee=e, organization="„Beta” SA", date_from=date(2012, 1, 1), date_to=date(2013, 12, 31),
                                   in_specialty=False)
    staff.hire(e, kind="main", subdivision=org["sub"], occupation=org["occ"], rate=Decimal("1"), base_salary=Decimal("9000"),
               date_from=date(2020, 1, 1))
    s = staff.seniority(e, date(2025, 12, 31))
    assert set(s) == {"on_date", "total", "specialty", "institution"}
    # în specialitate: stagiul bifat + raporturile de aici (orice funcție, nu doar cele „medicale”)
    assert (s["total"]["years"], s["specialty"]["years"], s["institution"]["years"]) == (13, 11, 6)
    exp = admin_client.get("/api/staff/experience/", {"employee": e.pk}).data
    assert "in_healthcare" not in exp[0]
    sen = admin_client.get(f"/api/staff/employees/{e.pk}/seniority/").data
    assert "healthcare" not in sen
    html = admin_client.get(f"/api/staff/employees/{e.pk}/print/?doc=employee_card").content.decode()
    assert "sistemul sănătății" not in html and "Categoria de calificare" not in html
    cert = admin_client.get(f"/api/staff/employees/{e.pk}/print/?doc=certificate_seniority").content.decode()
    assert "sistemul sănătății" not in cert


def test_qualification_category_removed(org, admin_client):
    assert admin_client.get("/api/staff/qualifications/").status_code == 404
    assert not DictItem.objects.filter(kind__in=("qualification", "degree", "title", "vaccine")).exists()
    assert not {"qualification_expiry", "seniority_step", "credits_missing", "vaccination_due"} & set(engine.KINDS)
    e = Employee.objects.create(tab_number="1", last_name="Popescu", first_name="Ion")
    card = admin_client.get(f"/api/staff/employees/{e.pk}/summary/").data
    assert "qualification" not in card
    tpl = admin_client.get("/api/staff/import/qualifications/template/")
    assert tpl.status_code in (400, 404)


def test_roles_for_a_company(seeded):
    assert Role.objects.get(code="department_head").name_ro == "Șef de subdiviziune"
    assert Role.objects.get(code="director").name_ro == "Director / administrator"
    assert Role.objects.get(code="director").name_ru == "Директор / администратор"
