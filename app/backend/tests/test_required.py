"""Câmpurile obligatorii (Administrare → Câmpuri obligatorii) pentru dosarul angajatului."""


def test_required_employee_fields(seeded, admin_client):
    cat = admin_client.get("/api/settings/required-fields/").data
    assert {d["key"] for d in cat["docs"]} == {"employee", "document", "education"}
    admin_client.put("/api/settings/required-fields/", {"selected": {"employee": ["idnp", "iban"]}}, format="json")
    r = admin_client.post("/api/staff/employees/", {"tab_number": "900", "last_name": "Popescu", "first_name": "Ion"}, format="json")
    assert r.status_code == 400 and {"idnp", "iban"} <= set(r.data)
    ok = admin_client.post("/api/staff/employees/", {"tab_number": "900", "last_name": "Popescu", "first_name": "Ion",
                                                     "idnp": "2001001001001", "iban": "MD24AG000225100013104168"}, format="json")
    assert ok.status_code == 201, ok.data
