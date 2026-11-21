"""Etapa 3: ordinele — calendarul, numerotarea pe registre, efectele la semnare și anularea lor, tiparul, registrul."""
from datetime import date
from decimal import Decimal

import pytest

from apps.leave.models import Absence
from apps.org import calendar
from apps.org import services as org_services
from apps.org.models import DictItem, Occupation, OrderType, StaffList, StaffListLine, Subdivision
from apps.orders.models import Order, Sanction
from apps.staff import services as staff
from apps.staff.models import Employee
from .conftest import occupation


@pytest.fixture
def org(seeded):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1")
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția ATI")
    return {"tr1": tr1, "ati": ati,
            "doctor": occupation("Medic traumatolog-ortoped"),
            "anest": occupation("Medic anesteziolog-reanimatolog")}


def emp(last="Popescu", first="Ion"):
    return Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first)


def hired(org, last="Popescu", first="Ion", **extra):
    e = emp(last, first)
    staff.hire(e, kind="main", subdivision=org["tr1"], occupation=org["doctor"], rate=Decimal("1"),
               base_salary=Decimal("14660"), date_from=date(2020, 1, 1), **extra)
    return e


def make_order(api, code, employees=(), date_="2026-03-02"):
    ot = OrderType.objects.get(code=code)
    r = api.post("/api/orders/orders/", {"order_type": ot.id, "employees": [e.id for e in employees], "date": date_}, format="json")
    assert r.status_code == 201, r.data
    return r.data


def set_params(api, order, params, idx=0, **extra):
    item = order["items"][idx]
    r = api.patch(f"/api/orders/items/{item['id']}/", {"params": params, **extra}, format="json")
    assert r.status_code == 200, r.data
    return r.data


def sign(api, order, ok=True):
    r = api.post(f"/api/orders/orders/{order['id']}/sign/", format="json")
    if ok:
        assert r.status_code == 200, r.data
    return r


def cancel(api, order):
    draft = api.post(f"/api/orders/orders/{order['id']}/cancel-by-order/", format="json")
    assert draft.status_code == 201, draft.data
    return sign(api, draft.data).data


# --- calendarul ----------------------------------------------------------------------------
def test_orthodox_easter_and_leave_days(seeded):
    assert calendar.orthodox_easter(2026) == date(2026, 4, 12)
    assert calendar.orthodox_easter(2027) == date(2027, 5, 2)
    assert calendar.orthodox_easter(2025) == date(2025, 4, 20)
    # 27.04–10.05.2026: 14 zile calendaristice, dintre care 1 mai și 9 mai sunt sărbători
    assert calendar.leave_days(date(2026, 4, 27), date(2026, 5, 10)) == 12
    # 28 de zile din 27.04: sărbătorile (1 mai, 9 mai, 1 iunie) prelungesc concediul
    assert calendar.leave_end(date(2026, 4, 27), 28) == date(2026, 5, 26)


def test_leave_days_endpoint(admin_client, seeded):
    r = admin_client.get("/api/orders/leave-days/", {"from": "2026-04-27", "days": 14}).data
    assert r["to"] == date(2026, 5, 12) and r["days"] == 14 and len(r["holidays"]) == 2
    unpaid_maternity = admin_client.get("/api/orders/leave-days/", {"from": "2026-04-27", "days": 14, "kind": "maternity"}).data
    assert unpaid_maternity["to"] == date(2026, 5, 10)  # maternitatea: zile calendaristice simple


# --- numerotarea și ciclul ordinului ------------------------------------------------------------
def test_numbering_per_register_and_locking(admin_client, org):
    a, b = hired(org), hired(org, "Rusu", "Ana")
    o1 = make_order(admin_client, "salary_set", [a])
    set_params(admin_client, o1, {"date_from": "2026-03-01", "base_salary": "16000"})
    assert sign(admin_client, o1).data["number"] == "1-p"
    o2 = make_order(admin_client, "bonus", [a, b])
    set_params(admin_client, o2, {"amount": "1000", "note": "pentru activitate"})
    set_params(admin_client, o2, {"amount": "800"}, idx=1)
    assert sign(admin_client, o2).data["number"] == "2-p"
    leave = make_order(admin_client, "leave_annual", [b])
    set_params(admin_client, leave, {"date_from": "2026-06-01", "days": 14, "work_year_from": "2025-01-01",
                                     "work_year_to": "2025-12-31"})
    assert sign(admin_client, leave).data["number"] == "1-c"  # alt registru, numerotare proprie
    signed = admin_client.get(f"/api/orders/orders/{o1['id']}/").data
    assert admin_client.patch(f"/api/orders/orders/{o1['id']}/", {"title": "x"}, format="json").status_code == 400
    assert admin_client.patch(f"/api/orders/items/{signed['items'][0]['id']}/", {"text": "x"}, format="json").status_code == 400
    assert admin_client.delete(f"/api/orders/orders/{o1['id']}/").status_code == 400
    single = make_order(admin_client, "hire", [a])
    extra = admin_client.post("/api/orders/items/", {"order": single["id"], "employee": b.id}, format="json")
    assert extra.status_code == 400  # angajarea e pentru un singur angajat


def test_hire_order_then_cancel(admin_client, org):
    candidate = emp("Ceban", "Dan")
    order = make_order(admin_client, "hire", [candidate])
    item = set_params(admin_client, order, {"kind": "main", "subdivision": org["ati"].id, "occupation": org["anest"].id,
                                            "rate": "1", "base_salary": "15200", "date_from": "2026-03-02",
                                            "probation_until": "2026-06-01", "contract_number": "45"})
    assert "Se angajează Ceban Dan în funcția de Medic anesteziolog-reanimatolog" in item["text"]
    assert "perioadă de probă până la 01.06.2026" in item["text"]
    signed = sign(admin_client, order).data
    job = candidate.employments.get()
    assert job.hire_order == f"{signed['number']} din 02.03.2026" and job.history.get().order == job.hire_order
    assert job.probation_until == date(2026, 6, 1)
    cancel(admin_client, signed)
    assert not candidate.employments.exists()
    assert Order.objects.get(pk=order["id"]).status == "cancelled"


def test_transfer_records_history_and_cancel_restores(admin_client, org):
    a = hired(org)
    order = make_order(admin_client, "transfer", [a])
    set_params(admin_client, order, {"date_from": "2026-03-02", "subdivision": org["ati"].id, "occupation": org["anest"].id,
                                     "base_salary": "15200"})
    signed = sign(admin_client, order).data
    job = a.employments.get()
    assert job.subdivision == org["ati"] and job.history.count() == 2
    assert job.history.last().order == f"{signed['number']} din 02.03.2026"
    cancel(admin_client, signed)
    job.refresh_from_db()
    assert job.subdivision == org["tr1"] and job.base_salary == Decimal("14660") and job.history.count() == 1
    nothing = make_order(admin_client, "transfer", [a])
    set_params(admin_client, nothing, {"date_from": "2026-03-02", "subdivision": org["tr1"].id})
    assert sign(admin_client, nothing, ok=False).status_code == 400  # nu se schimbă nimic


def test_annual_leave_overlap_and_recall(admin_client, org):
    a = hired(org)
    order = make_order(admin_client, "leave_annual", [a])
    set_params(admin_client, order, {"date_from": "2026-04-27", "days": 28, "work_year_from": "2025-01-01",
                                     "work_year_to": "2025-12-31"})
    signed = sign(admin_client, order).data
    absence = Absence.objects.get(employee=a)
    assert (absence.date_to, absence.days) == (date(2026, 5, 26), 28)
    assert "de 28 zile calendaristice, de la 27.04.2026 până la 26.05.2026" in signed["items"][0]["text"]
    again = make_order(admin_client, "leave_unpaid", [a])
    set_params(admin_client, again, {"date_from": "2026-05-20", "days": 3})
    r = sign(admin_client, again, ok=False)
    assert r.status_code == 400 and "suprapune" in r.data["detail"]
    recall = make_order(admin_client, "leave_recall", [a])
    set_params(admin_client, recall, {"absence": absence.id, "date_from": "2026-05-18"})
    sign(admin_client, recall)
    absence.refresh_from_db()
    assert absence.date_to == date(2026, 5, 17) and absence.recalled_on == date(2026, 5, 18)
    assert absence.days + absence.days_returned == 28


def test_childcare_leave_suspends_and_cancel_resumes(admin_client, org):
    a = hired(org)
    order = make_order(admin_client, "leave_childcare", [a])
    set_params(admin_client, order, {"date_from": "2026-03-01", "date_to": "2028-02-28"})
    signed = sign(admin_client, order).data
    job = a.employments.get()
    a.refresh_from_db()
    assert job.status == "suspended" and a.status == "suspended"
    occ_line_list = StaffList.objects.create(effective_from=date(2026, 1, 1))
    StaffListLine.objects.create(staff_list=occ_line_list, subdivision=org["tr1"], occupation=org["doctor"], units=2)
    org_services.approve(occ_line_list)
    row = org_services.occupancy(on_date=date(2026, 6, 1))["rows"][0]
    assert row["temporary"] == "1.00"  # postul e temporar vacant (poate fi suplinit)
    cancel(admin_client, signed)
    job.refresh_from_db()
    assert job.status == "active" and not Absence.objects.filter(employee=a).exists()


def test_terminate_order_and_cancel(admin_client, org):
    a = hired(org)
    reason = DictItem.objects.get(kind="termination", code="resignation")
    order = make_order(admin_client, "terminate", [a])
    item = set_params(admin_client, order, {"date_from": "2026-03-31", "reason": reason.id, "compensation_days": 12})
    assert "în temeiul: Demisie" in item["text"] and "12 zile de concediu nefolosit" in item["text"]
    signed = sign(admin_client, order).data
    a.refresh_from_db()
    assert a.status == "dismissed" and a.employments.get().end_order == f"{signed['number']} din 02.03.2026"
    cancel(admin_client, signed)
    a.refresh_from_db()
    assert a.status == "active" and a.employments.get().end_date is None


def test_sanction_and_its_lift(admin_client, org):
    a = hired(org)
    kind = DictItem.objects.get(kind="sanction", code="reprimand")
    order = make_order(admin_client, "sanction", [a])
    item = set_params(admin_client, order, {"sanction": kind.id, "misconduct": "absența nemotivată din 10.02.2026"})
    assert "sancțiunea disciplinară „mustrare”" in item["text"]
    sign(admin_client, order)
    sanction = Sanction.objects.get(employee=a)
    assert sanction.valid_until == date(2027, 3, 2)
    lift = make_order(admin_client, "sanction_lift", [a])
    set_params(admin_client, lift, {"sanction_record": sanction.id, "date_from": "2026-09-01"})
    sign(admin_client, lift)
    sanction.refresh_from_db()
    assert sanction.lifted_on == date(2026, 9, 1)
    assert len(admin_client.get("/api/orders/sanctions/", {"employee": a.id}).data) == 1


def test_staff_list_order_approves_the_draft(admin_client, org):
    sl = StaffList.objects.create(effective_from=date(2026, 7, 1))
    StaffListLine.objects.create(staff_list=sl, subdivision=org["tr1"], occupation=org["doctor"], units=3)
    order = make_order(admin_client, "staff_list")
    item = admin_client.post("/api/orders/items/", {"order": order["id"], "params": {"staff_list": sl.id}}, format="json").data
    assert "în vigoare de la" in item["text"]
    sign(admin_client, admin_client.get(f"/api/orders/orders/{order['id']}/").data)
    sl.refresh_from_db()
    assert sl.status == "approved" and sl.approved_by.startswith("Ordinul nr. 1")


def test_print_order_extract_and_register_with_gaps(admin_client, org):
    from apps.core.models import Company

    company = Company.get()
    company.director = "Ion Director"
    company.save()
    a, b = hired(org), hired(org, "Rusu", "Ana")
    order = make_order(admin_client, "leave_annual", [a, b])
    for idx in (0, 1):
        set_params(admin_client, order, {"date_from": "2026-07-01", "days": 14}, idx=idx)
    admin_client.patch(f"/api/orders/orders/{order['id']}/", {"basis": "Cererile salariaților", "approvals": [
        {"name": "Șef RU", "position": "Șef resurse umane"}]}, format="json")
    signed = sign(admin_client, order).data
    html = admin_client.get(f"/api/orders/orders/{order['id']}/print/").content.decode()
    assert "ORDIN" in html and "ORDON:" in html and f"<b>{signed['number']}</b>" in html
    assert "Popescu Ion" in html and "Rusu Ana" in html and "Am luat cunoștință" in html and "Ion Director" in html
    assert 'class="company-header"' in html and "REPUBLICA MOLDOVA" not in html and "data:image/svg+xml" not in html
    extract = admin_client.get(f"/api/orders/orders/{order['id']}/print/", {"item": signed["items"][1]["id"]}).content.decode()
    assert "EXTRAS" in extract and "Rusu Ana" in extract and "Popescu Ion" not in extract
    admin_client.post(f"/api/orders/orders/{order['id']}/acknowledge/", {"date": "2026-06-25"}, format="json")
    assert Order.objects.get(pk=order["id"]).items.filter(acknowledged_on=date(2026, 6, 25)).count() == 2
    # numerotare manuală: nr. 4 → în registru lipsesc 2 și 3
    manual = make_order(admin_client, "leave_unpaid", [a])
    set_params(admin_client, manual, {"date_from": "2026-09-01", "days": 2})
    admin_client.patch(f"/api/orders/orders/{manual['id']}/", {"seq": 4}, format="json")
    assert sign(admin_client, manual).data["number"] == "4-c"
    reg = admin_client.get("/api/orders/orders/register/", {"register": "order_leave", "year": 2026}).data
    assert reg["gaps"] == ["2-c", "3-c"] and len(reg["orders"]) == 2
    printed = admin_client.get("/api/orders/orders/print-register/", {"register": "order_leave", "year": 2026}).content.decode()
    assert "REGISTRUL ORDINELOR" in printed and "Numere lipsă" in printed


def test_department_head_sees_only_orders_of_own_people(org, admin_client, make_user, client_for):
    a = hired(org)
    b = emp("Rusu", "Ana")
    staff.hire(b, kind="main", subdivision=org["ati"], occupation=org["anest"], rate=1, date_from=date(2020, 1, 1))
    for person in (a, b):
        o = make_order(admin_client, "bonus", [person])
        set_params(admin_client, o, {"amount": "500"})
        sign(admin_client, o)
    head = make_user("sef", ["department_head"])
    org["ati"].users.add(head)
    rows = client_for(head).get("/api/orders/orders/").data["results"]
    assert [r["employees"] for r in rows] == ["Rusu A."]


def test_extend_contract_and_change_terms(admin_client, org):
    a = hired(org, date_to=date(2026, 6, 30))
    order = make_order(admin_client, "extend_contract", [a])
    item = set_params(admin_client, order, {"date_to": "2027-06-30"})
    assert "până la 30.06.2027" in item["text"]
    signed = sign(admin_client, order).data
    job = a.employments.get()
    assert job.date_to == date(2027, 6, 30) and job.history.last().note == "Prelungit până la 30.06.2027"
    cancel(admin_client, signed)
    job.refresh_from_db()
    assert job.date_to == date(2026, 6, 30)
    terms = make_order(admin_client, "change_terms", [a])
    set_params(admin_client, terms, {"date_from": "2026-04-01", "text": "regimul de muncă în ture de 12 ore"})
    sign(admin_client, terms)
    assert a.employments.get().history.last().note == "regimul de muncă în ture de 12 ore"


def test_order_with_several_legal_bases(admin_client, org):
    from apps.org.models import LegalBasis

    cm = "Codul muncii nr. 154/2003"
    a55 = LegalBasis.objects.create(code="T-55", act=cm, article="55", letter="a", name_ro="Contract pe durată determinată")
    a60 = LegalBasis.objects.create(code="T-60", act=cm, article="60", name_ro="Perioada de probă")
    hg = LegalBasis.objects.create(code="T-HG", act="HG nr. 426/2004", article="", name_ro="Media salarială")
    assert LegalBasis.combined([a55, a60, hg]) == "art. 55 lit. a) și art. 60 din Codul muncii nr. 154/2003, HG nr. 426/2004"
    assert LegalBasis.combined([a55, a60, a55]) == "art. 55 lit. a) și art. 60 din Codul muncii nr. 154/2003"  # fără dubluri
    assert LegalBasis.preamble([]) == ""
    r = admin_client.get("/api/org/legal-bases/preamble/", {"ids": f"{a60.id},{a55.id}"})
    assert r.data["text"] == "În temeiul art. 60 și art. 55 lit. a) din Codul muncii nr. 154/2003,"  # în ordinea alegerii
    # tipul cu două temeiuri implicite: ordinul nou le ia pe amândouă, cu preambulul compus
    ot = OrderType.objects.get(code="hire")
    ot.legal_bases.set([a55, a60])
    order = make_order(admin_client, "hire")
    assert sorted(order["legal_bases"]) == sorted([a55.id, a60.id])
    assert order["preamble"] == "În temeiul art. 55 lit. a) și art. 60 din Codul muncii nr. 154/2003,"
    r = admin_client.patch(f"/api/orders/orders/{order['id']}/", {"legal_bases": [hg.id]}, format="json")
    assert r.status_code == 200 and r.data["legal_bases"] == [hg.id] and r.data["legal_bases_ref"] == "HG nr. 426/2004"
