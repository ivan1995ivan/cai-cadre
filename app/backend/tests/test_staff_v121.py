"""Versiunea 1.2.1: mărimile echipamentului de lucru (dosar, import, raport) și fișa scurtă a angajatului din listă."""
from datetime import date

from apps.staff.models import AccessLog

from .test_staff import hire, make_emp, org  # noqa: F401 — fixtura și ajutoarele comune


def test_sizes_saved_validated_and_reported(admin_client, org):  # noqa: F811
    a, b, c = make_emp("Albu", "Ion"), make_emp("Botnaru", "Ana"), make_emp("Ciobanu", "Vera")
    for e in (a, b, c):
        hire(e, org)
    r = admin_client.patch(f"/api/staff/employees/{a.id}/", {"clothing_size": "48", "shoe_size": "42", "height": 178}, format="json")
    assert r.status_code == 200 and (r.data["clothing_size"], r.data["shoe_size"], r.data["height"]) == ("48", "42", 178)
    assert admin_client.patch(f"/api/staff/employees/{a.id}/", {"height": 1780}, format="json").status_code == 400
    admin_client.patch(f"/api/staff/employees/{b.id}/", {"clothing_size": "48", "shoe_size": "38"}, format="json")
    data = admin_client.get("/api/reports/workwear_sizes/").data
    rows = [r for r in data["rows"] if "name" in r]
    assert {r["name"]: (r["clothing"], r["shoes"]) for r in rows} == {"Albu Ion": ("48", "42"), "Botnaru Ana": ("48", "38"),
                                                                       "Ciobanu Vera": ("", "")}
    summary = {s["label"]: s["value"] for s in data["summary"]}
    assert summary["Îmbrăcăminte, pe mărimi"] == "48 — 2" and summary["Încălțăminte, pe mărimi"] == "38 — 1, 42 — 1"
    assert summary["Fără mărimi în dosar"] == 1


def test_quick_card_has_age_seniority_and_is_not_logged(admin_client, org, make_user, client_for):  # noqa: F811
    e = make_emp("Popescu", "Ion", idnp="2001000000001", birth_date=date(1980, 5, 10), phone="069000000")
    hire(e, org)
    card = admin_client.get(f"/api/staff/employees/{e.id}/summary/").data
    assert card["full_name"] == "Popescu Ion" and card["age"] >= 46 and card["jobs"][0]["occupation"]
    assert set(card["seniority"]) == {"total", "healthcare", "specialty", "institution"} and card["phone"] == "069000000"
    assert not AccessLog.objects.filter(employee=e).exists()  # trecerea mouse-ului nu e deschiderea dosarului
    # cine nu vede contactele nu le vede nici în fișa scurtă
    clerk = make_user("clerk", ["hr_inspector"])
    role = clerk.roles.first()
    role.hidden_fields = ["contacts"]
    role.save()
    clerk = type(clerk).objects.get(pk=clerk.pk)
    assert client_for(clerk).get(f"/api/staff/employees/{e.id}/summary/").data["phone"] is None
