"""Marcarea pentru ștergere: „Șterge” marchează, obiectul marcat nu se schimbă, ștergerea de tot (Administrare) doar fără
legături în bază; obiectele alese împreună se șterg în ordinea potrivită."""
from datetime import date

import pytest

from apps.leave.models import Absence, SickLeave
from apps.org.models import Occupation, Specialty
from apps.orders.models import Order, OrderItem
from apps.staff import services as staff
from apps.staff.models import Employee
from apps.training.models import TrainingRecord

from .test_orders import hired, make_order, org  # noqa: F401 (fixture)


def marked(admin_client, keys):
    return admin_client.post("/api/system/marked/delete/", {"keys": keys}, format="json").data


def test_order_mark_blocks_changes_until_unmarked(admin_client, org):
    e = hired(org)
    o = make_order(admin_client, "bonus", [e])
    assert admin_client.delete(f"/api/orders/orders/{o['id']}/").status_code == 204
    assert Order.objects.get(pk=o["id"]).deletion_mark
    assert admin_client.get(f"/api/orders/orders/{o['id']}/").data["deletion_mark"] is True
    edit = admin_client.patch(f"/api/orders/orders/{o['id']}/", {"note": "x"}, format="json")
    assert edit.status_code == 400 and "marcat" in edit.data["detail"]
    assert admin_client.post(f"/api/orders/orders/{o['id']}/sign/", format="json").status_code == 400
    item = o["items"][0]["id"]
    assert admin_client.patch(f"/api/orders/items/{item}/", {"params": {}}, format="json").status_code == 400
    assert admin_client.post(f"/api/orders/orders/{o['id']}/unmark/", format="json").data["deletion_mark"] is False
    assert admin_client.patch(f"/api/orders/orders/{o['id']}/", {"note": "x"}, format="json").status_code == 200
    # ordinul marcat fără legături se șterge de tot, cu pozițiile lui
    admin_client.delete(f"/api/orders/orders/{o['id']}/")
    rows = admin_client.get("/api/system/marked/").data
    assert [r["key"] for r in rows] == [f"orders.Order:{o['id']}"]
    done = marked(admin_client, [f"orders.Order:{o['id']}"])
    assert len(done["deleted"]) == 1 and not done["blocked"]
    assert not Order.objects.filter(pk=o["id"]).exists() and not OrderItem.objects.filter(pk=item).exists()
    assert Employee.objects.filter(pk=e.id).exists()


def test_signed_order_is_not_marked(admin_client, org):
    e = hired(org)
    o = make_order(admin_client, "bonus", [e])
    Order.objects.filter(pk=o["id"]).update(status="signed")
    assert admin_client.delete(f"/api/orders/orders/{o['id']}/").status_code == 400
    assert not Order.objects.get(pk=o["id"]).deletion_mark


def test_objects_deleted_together_in_the_right_order(admin_client, org):
    cand = Employee.objects.create(tab_number=staff.next_tab_number(), last_name="Candidat", first_name="Ion", status="candidate")
    o = make_order(admin_client, "bonus", [cand])
    admin_client.delete(f"/api/staff/employees/{cand.id}/")
    alone = marked(admin_client, [f"staff.Employee:{cand.id}"])
    assert not alone["deleted"]
    refs = alone["blocked"][0]["refs"]
    assert refs[0]["model"] == "orders.Order" and refs[0]["part"]  # poziția ordinului, arătată prin ordin
    admin_client.delete(f"/api/orders/orders/{o['id']}/")
    both = marked(admin_client, [f"staff.Employee:{cand.id}", f"orders.Order:{o['id']}"])
    assert len(both["deleted"]) == 2 and not both["blocked"]
    assert not Employee.objects.filter(pk=cand.id).exists()


def test_used_classifiers_stay_and_pickers_hide_marked(admin_client, org):
    e = hired(org)
    occ = org["doctor"]
    assert admin_client.delete(f"/api/org/occupations/{occ.id}/").status_code == 204
    picker = admin_client.get("/api/org/occupations/", {"active": "1"}).data
    assert occ.id not in [r["id"] for r in picker]
    assert next(r for r in admin_client.get("/api/org/occupations/").data if r["id"] == occ.id)["deletion_mark"]
    check = admin_client.post("/api/system/marked/check/", {"keys": [f"org.Occupation:{occ.id}"]}, format="json").data
    assert check[f"org.Occupation:{occ.id}"][0]["model"] == "staff.Employee"  # raportul de muncă al angajatului
    assert not marked(admin_client, [f"org.Occupation:{occ.id}"])["deleted"]
    assert Occupation.objects.filter(pk=occ.id).exists()
    # câmpul care s-ar goli (SET_NULL) e tot o legătură
    spec = Specialty.objects.create(name_ro="Ortopedie pediatrică")
    TrainingRecord.objects.create(employee=e, kind="course", title="Curs", date_from=date(2026, 3, 1), specialty=spec)
    admin_client.delete(f"/api/org/specialties/{spec.id}/")
    assert marked(admin_client, [f"org.Specialty:{spec.id}"])["blocked"][0]["refs"][0]["model"] == "training.TrainingRecord"
    unused = Specialty.objects.create(name_ro="Nefolosită")
    admin_client.delete(f"/api/org/specialties/{unused.id}/")
    assert marked(admin_client, [f"org.Specialty:{unused.id}"])["deleted"][0]["title"] == "Nefolosită"


def test_marked_sick_leave_is_no_longer_an_absence(admin_client, org):
    e = hired(org)
    r = admin_client.post("/api/leave/sick-leaves/", {"employee": e.id, "number": "77", "kind": "illness",
                                                      "date_from": "2026-08-10", "date_to": "2026-08-14"}, format="json")
    assert r.status_code == 201, r.data
    assert admin_client.delete(f"/api/leave/sick-leaves/{r.data['id']}/").status_code == 204
    assert not Absence.objects.filter(kind="sick").exists() and SickLeave.objects.get(pk=r.data["id"]).deletion_mark
    assert admin_client.post(f"/api/leave/sick-leaves/{r.data['id']}/unmark/", format="json").status_code == 200
    assert Absence.objects.get(kind="sick").date_to == date(2026, 8, 14)


def test_marked_objects_tool_needs_settings_rights(org, make_user, client_for):
    hr = client_for(make_user("insp", ["hr_inspector"]))
    assert hr.get("/api/system/marked/").status_code == 403
    assert hr.post("/api/system/marked/delete/", {"keys": ["org.Occupation:1"]}, format="json").status_code == 403


@pytest.mark.parametrize("url", ["/api/org/occupations/", "/api/org/specialties/"])
def test_unmark_needs_delete_right(org, make_user, client_for, url, admin_client):
    Specialty.objects.get_or_create(name_ro="Contabilitate")  # specialitățile nu se mai livrează
    row = admin_client.get(url).data[0]
    admin_client.delete(f"{url}{row['id']}/")
    viewer = client_for(make_user("insp", ["hr_inspector"]))
    assert viewer.post(f"{url}{row['id']}/unmark/", format="json").status_code == 403
