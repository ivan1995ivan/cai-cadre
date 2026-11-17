"""Șeful de secție se leagă de secțiile lui din Administrare → Utilizatori și vede doar angajații de acolo."""
from datetime import date
from decimal import Decimal

from apps.org.models import Occupation, Subdivision
from apps.staff import services as staff
from apps.staff.models import Employee
from apps.users.models import Role, User


def test_head_sees_only_assigned_subdivisions(seeded, admin_client, client_for):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Traumatologie")
    ati = Subdivision.objects.create(code="ATI", name_ro="ATI")
    occ = Occupation.objects.get(name_ro="Medic traumatolog-ortoped")
    for i, (name, sub) in enumerate((("Popescu", tr1), ("Rusu", ati)), start=1):
        e = Employee.objects.create(tab_number=str(i), last_name=name, first_name="X")
        staff.hire(e, kind="main", subdivision=sub, occupation=occ, rate=Decimal("1"), base_salary=Decimal("1"), date_from=date(2024, 1, 1))
    role = Role.objects.get(code="department_head")
    r = admin_client.post("/api/users/", {"username": "sef", "password": "Sef-Sectie-2026x", "roles": [role.pk], "subdivisions": [tr1.pk]},
                          format="json")
    assert r.status_code == 201, r.data
    assert r.data["subdivisions"] == [tr1.pk]
    sef = client_for(User.objects.get(username="sef"))
    names = [x["last_name"] for x in sef.get("/api/staff/employees/").data["results"]]
    assert names == ["Popescu"]
    admin_client.patch(f"/api/users/{r.data['id']}/", {"subdivisions": [tr1.pk, ati.pk]}, format="json")
    assert len(sef.get("/api/staff/employees/").data["results"]) == 2
