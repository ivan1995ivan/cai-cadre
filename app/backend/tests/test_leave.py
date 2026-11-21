"""Etapa 4 (partea 1): concediile — dreptul și soldul, ordinele de concediu, graficul anual, cererile, foile de boală."""
from datetime import date
from decimal import Decimal

import pytest

from apps.leave import balance, services
from apps.leave.models import Absence, LeaveAdjustment, LeaveRequest, LeaveRight, LeaveSchedule
from apps.org.models import DictItem, Occupation, Subdivision
from apps.staff import services as staff
from apps.staff.models import Employee, FamilyMember

from .test_orders import cancel, make_order, set_params, sign


@pytest.fixture
def org(seeded):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1")
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția ATI", extra_leave_days=7, harmful=True)
    return {"tr1": tr1, "ati": ati,
            "doctor": Occupation.objects.get(name_ro="Medic traumatolog-ortoped"),
            "anest": Occupation.objects.get(name_ro="Medic anesteziolog-reanimatolog"),
            "nurse": Occupation.objects.get(name_ro="Asistent medical de secție")}


def person(org, last="Popescu", first="Ion", sub="tr1", occ="doctor", hired=date(2024, 3, 1), **extra):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first)
    staff.hire(e, kind="main", subdivision=org[sub], occupation=org[occ], rate=Decimal("1"), base_salary=Decimal("14000"),
               date_from=hired, **extra)
    return e


def absence(e, start, end, days, kind="annual", **extra):
    return Absence.objects.create(employee=e, kind=kind, date_from=start, date_to=end, days=days, **extra)


# --- dreptul și soldul -------------------------------------------------------------------------------------
def test_balance_by_work_years_with_fifo_and_personal_rights(org):
    e = person(org)
    absence(e, date(2024, 7, 1), date(2024, 7, 14), 14)  # fără anul de muncă: pe cel mai vechi an
    absence(e, date(2025, 8, 1), date(2025, 8, 20), 20)  # 14 rămase din anul 1, apoi 6 din anul 2
    LeaveRight.objects.create(employee=e, reason="children", days=4, date_from=date(2025, 6, 1))
    data = balance.balance(e, on_date=date(2026, 3, 1))
    years = data["years"]
    assert [(y["from"], y["to"]) for y in years] == [
        (date(2024, 3, 1), date(2025, 2, 28)), (date(2025, 3, 1), date(2026, 2, 28)), (date(2026, 3, 1), date(2027, 2, 28))]
    assert [y["entitled"] for y in years] == [28, 32, 32]  # dreptul personal din iunie 2025
    assert [y["used"] for y in years] == [28, 6, 0]
    assert years[2]["accrued"] == round(32 / 365, 2)
    assert data["remaining"] == round(0 + 26 + 32 / 365, 2)
    assert data["available"] == 26 + 32


def test_harmful_subdivision_days_and_dismissal_prorata(org):
    e = person(org, sub="ati", occ="anest", hired=date(2025, 1, 1))
    data = balance.balance(e, on_date=date(2025, 6, 1))
    assert data["years"][0]["extra"] == 7 and data["years"][0]["entitled"] == 35
    job = e.employments.get()
    staff.terminate(job, date(2025, 7, 1), None)
    data = balance.balance(e, on_date=date(2026, 1, 1))
    assert data["years"][0]["accrued"] == round(35 * 182 / 365, 2)  # 01.01–01.07: 182 zile lucrate


def test_childcare_leave_shifts_the_work_year(org):
    e = person(org, hired=date(2020, 1, 1))
    absence(e, date(2021, 1, 1), date(2021, 12, 31), 365, kind="childcare")
    years = balance.balance(e, on_date=date(2023, 1, 10))["years"]
    assert (years[1]["from"], years[1]["to"], years[1]["skipped"]) == (date(2021, 1, 1), date(2022, 12, 31), 365)
    assert years[2]["from"] == date(2023, 1, 1)


def test_start_date_and_opening_balance(org, admin_client):
    e = person(org, hired=date(2015, 9, 1))
    r = admin_client.put("/api/leave/settings/", {"start_date": "2026-01-01"}, format="json")
    assert r.status_code == 200 and r.data["start_date"] == "2026-01-01"
    LeaveAdjustment.objects.create(employee=e, kind="opening", date=date(2026, 1, 1), work_year_from=date(2024, 9, 1),
                                   days=Decimal("10"))
    data = balance.balance(e, on_date=date(2026, 3, 1))
    assert data["years"][0]["from"] == date(2025, 9, 1)  # anii încheiați înainte de pornire nu se mai calculează
    assert data["opening"] == 10 and data["remaining"] == round(10 + 28 * 182 / 365, 2)
    rows = admin_client.get("/api/leave/balances/", {"on_date": "2026-03-01"}).data["results"]
    assert rows[0]["full_name"] == "Popescu Ion" and rows[0]["entitled"] == 28


# --- ordinele de concediu --------------------------------------------------------------------------------
def test_annual_leave_order_takes_the_oldest_work_year(admin_client, org):
    e = person(org)
    order = make_order(admin_client, "leave_annual", [e])
    set_params(admin_client, order, {"date_from": "2026-07-01", "days": 14})
    signed = sign(admin_client, order).data
    a = Absence.objects.get(employee=e)
    assert (a.work_year_from, a.work_year_to) == (date(2024, 3, 1), date(2025, 2, 28))
    assert "pentru anul de muncă 01.03.2024 – 28.02.2025" in signed["items"][0]["text"]


def test_compensation_and_dismissal_compensation_leave_the_balance(admin_client, org):
    e = person(org)
    comp = make_order(admin_client, "leave_compensation", [e])
    set_params(admin_client, comp, {"days": 5})
    signed = sign(admin_client, comp).data
    adj = LeaveAdjustment.objects.get(employee=e)
    assert adj.days == Decimal("-5") and adj.kind == "compensated"
    assert admin_client.delete(f"/api/leave/adjustments/{adj.id}/").status_code == 400  # se întoarce prin anularea ordinului
    cancel(admin_client, signed)
    assert not LeaveAdjustment.objects.filter(employee=e).exists()
    reason = DictItem.objects.get(kind="termination", code="resignation")
    term = make_order(admin_client, "terminate", [e])
    set_params(admin_client, term, {"date_from": "2026-03-31", "reason": reason.id, "compensation_days": 12})
    sign(admin_client, term)
    assert LeaveAdjustment.objects.get(employee=e).days == Decimal("-12")


def test_postpone_moves_a_future_leave_and_cancel_restores(admin_client, org):
    e = person(org)
    leave = make_order(admin_client, "leave_annual", [e], date_="2026-10-01")
    set_params(admin_client, leave, {"date_from": "2026-12-01", "days": 14})
    sign(admin_client, leave)
    a = Absence.objects.get(employee=e)
    post = make_order(admin_client, "leave_postpone", [e], date_="2026-10-20")
    set_params(admin_client, post, {"absence": a.id, "date_from": "2027-02-01"})
    signed = sign(admin_client, post).data
    a.refresh_from_db()
    assert (a.date_from, a.days) == (date(2027, 2, 1), 14)
    assert "planificat de la 01.12.2026, pentru perioada 01.02.2027 – 14.02.2027" in signed["items"][0]["text"]
    cancel(admin_client, signed)
    a.refresh_from_db()
    assert a.date_from == date(2026, 12, 1)


def test_social_leave_dates_and_automatic_return(admin_client, org):
    e = person(org, "Rusu", "Ana", hired=date(2020, 1, 1))
    child = FamilyMember.objects.create(employee=e, full_name="Rusu Maria", birth_date=date(2023, 5, 10))
    r = admin_client.get("/api/leave/social-dates/", {"kind": "maternity", "from": "2023-03-06"}).data
    assert r["to"] == date(2023, 7, 9) and r["days"] == 126
    r = admin_client.get("/api/leave/social-dates/", {"kind": "childcare", "child": child.id, "from": "2023-07-10"}).data
    assert r["to"] == date(2026, 5, 9)
    r = admin_client.get("/api/leave/social-dates/", {"kind": "childcare_unpaid", "child": child.id}).data
    assert (r["from"], r["to"]) == (date(2026, 5, 10), date(2027, 5, 9))
    order = make_order(admin_client, "leave_childcare", [e], date_="2023-07-05")
    set_params(admin_client, order, {"date_from": "2023-07-10", "date_to": "2026-05-09"})
    sign(admin_client, order)
    job = e.employments.get()
    assert job.status == "suspended"
    assert services.resume_after_childcare(date(2026, 5, 9)) == 0  # ultima zi a concediului
    assert services.resume_after_childcare(date(2026, 5, 11)) == 1
    job.refresh_from_db()
    assert job.status == "active" and job.history.last().date == date(2026, 5, 10)


# --- graficul anual --------------------------------------------------------------------------------------
def test_schedule_fill_overlaps_orders_and_print(admin_client, org):
    a = person(org, "Popescu", "Ion")
    b = person(org, "Rusu", "Ana")
    person(org, "Ceban", "Dan", occ="nurse")
    r = admin_client.post("/api/leave/schedules/", {"year": 2027, "subdivision": org["tr1"].id}, format="json")
    assert r.status_code == 201, r.data
    sid = r.data["id"]
    report = admin_client.get(f"/api/leave/schedules/{sid}/report/").data
    assert len(report["rows"]) == 3 and {row["days"] for row in report["rows"]} == {28}
    lines = {row["name"]: row["id"] for row in report["rows"]}
    for name, start in (("Popescu Ion", "2027-07-05"), ("Rusu Ana", "2027-07-19")):
        r = admin_client.patch(f"/api/leave/schedule-lines/{lines[name]}/", {"date_from": start, "days": 28}, format="json")
        assert r.status_code == 200, r.data
    assert r.data["date_to"] == "2027-08-15"
    report = admin_client.get(f"/api/leave/schedules/{sid}/report/").data
    assert not [w for w in report["warnings"] if w["kind"] == "physicians"]  # fără avertismentul de spital „toți medicii”
    gaps = [w for w in report["warnings"] if w["kind"] == "occupation"]
    assert len(gaps) == 1 and (gaps[0]["from"], gaps[0]["to"]) == (date(2027, 7, 19), date(2027, 8, 1))  # ambii de aceeași funcție
    assert gaps[0]["count"] == 2
    r = admin_client.post(f"/api/leave/schedules/{sid}/make-orders/", {"month": 7}, format="json")
    assert r.status_code == 201, r.data
    order = admin_client.get(f"/api/orders/orders/{r.data['id']}/").data
    assert order["type_code"] == "leave_annual" and len(order["items"]) == 2 and "Graficul concediilor" in order["basis"]
    sign(admin_client, order)
    assert Absence.objects.filter(employee__in=[a, b], kind="annual").count() == 2
    states = {row["name"]: row["state"] for row in admin_client.get(f"/api/leave/schedules/{sid}/report/").data["rows"]}
    assert states["Popescu Ion"] == "taken" and states["Ceban Dan"] == "planned"
    again = admin_client.post(f"/api/leave/schedules/{sid}/make-orders/", {"month": 7}, format="json")
    assert again.status_code == 400  # ordinele sunt deja emise
    html = admin_client.get(f"/api/leave/schedules/{sid}/print/").content.decode()
    assert "GRAFICUL CONCEDIILOR DE ODIHNĂ ANUALE" in html and "Rusu Ana" in html and "05.07.2027" in html


def test_department_head_plans_own_schedule_and_order_approves_it(admin_client, org, make_user, client_for):
    person(org)
    head = make_user("sef", ["department_head"])
    org["tr1"].users.add(head)
    api = client_for(head)
    assert api.post("/api/leave/schedules/", {"year": 2027, "subdivision": org["ati"].id}, format="json").status_code == 403
    r = api.post("/api/leave/schedules/", {"year": 2027, "subdivision": org["tr1"].id}, format="json")
    assert r.status_code == 201
    sid = r.data["id"]
    line = api.get("/api/leave/schedule-lines/", {"schedule": sid}).data[0]
    assert api.patch(f"/api/leave/schedule-lines/{line['id']}/", {"date_from": "2027-09-01"}, format="json").status_code == 200
    assert api.post(f"/api/leave/schedules/{sid}/submit/").status_code == 200
    assert api.patch(f"/api/leave/schedule-lines/{line['id']}/", {"days": 14}, format="json").status_code == 400
    order = make_order(admin_client, "leave_schedule", date_="2026-12-15")
    admin_client.post("/api/orders/items/", {"order": order["id"], "params": {"year": 2027}}, format="json")
    signed = sign(admin_client, admin_client.get(f"/api/orders/orders/{order['id']}/").data).data
    sch = LeaveSchedule.objects.get(pk=sid)
    assert sch.status == "approved" and sch.approved_by == f"Ordinul nr. {signed['number']} din 15.12.2026"
    cancel(admin_client, signed)
    sch.refresh_from_db()
    assert sch.status == "submitted"


# --- cererile de concediu ------------------------------------------------------------------------------------
def test_request_approved_by_head_becomes_order(admin_client, org, make_user, client_for):
    e = person(org)
    head = make_user("sef", ["department_head"])
    org["tr1"].users.add(head)
    api = client_for(head)
    r = api.post("/api/leave/requests/", {"employee": e.id, "kind": "annual", "date_from": "2027-04-26", "days": 14},
                 format="json")
    assert r.status_code == 201, r.data
    assert r.data["date_to"] == "2027-05-14"  # 1 mai, Paștele (2, 3 și 10 mai), 9 mai nu intră în concediu
    rid = r.data["id"]
    assert admin_client.post("/api/leave/requests/make-orders/", {"ids": [rid]}, format="json").status_code == 400
    assert api.post(f"/api/leave/requests/{rid}/approve/", {"note": "de acord"}, format="json").data["status"] == "approved"
    assert api.post("/api/leave/requests/make-orders/", {"ids": [rid]}, format="json").status_code == 403  # fără drept de ordine
    r = admin_client.post("/api/leave/requests/make-orders/", {"ids": [rid]}, format="json")
    assert r.status_code == 201 and len(r.data) == 1
    req = LeaveRequest.objects.get(pk=rid)
    assert req.status == "ordered" and req.order_item.params["request"] == rid
    sign(admin_client, admin_client.get(f"/api/orders/orders/{r.data[0]['id']}/").data)
    assert Absence.objects.get(employee=e).date_to == date(2027, 5, 14)
    clash = admin_client.post("/api/leave/requests/", {"employee": e.id, "kind": "unpaid", "date_from": "2027-05-10",
                                                       "days": 3}, format="json")
    assert clash.status_code == 400 and "suprapune" in str(clash.data)


# --- foile de boală -------------------------------------------------------------------------------------------
def test_sick_leave_creates_absence_and_warns_about_annual_leave(admin_client, org):
    e = person(org)
    absence(e, date(2026, 8, 3), date(2026, 8, 16), 14)
    r = admin_client.post("/api/leave/sick-leaves/", {"employee": e.id, "series": "A", "number": "123456", "kind": "illness",
                                                      "date_from": "2026-08-10", "date_to": "2026-08-19"}, format="json")
    assert r.status_code == 201, r.data
    assert r.data["days"] == 10 and r.data["warnings"] and "art. 116" in r.data["warnings"][0]
    sick = Absence.objects.get(pk=r.data["absence"])
    assert sick.kind == "sick" and "A 123456" in sick.note
    again = admin_client.post("/api/leave/sick-leaves/", {"employee": e.id, "number": "999", "date_from": "2026-08-15",
                                                          "date_to": "2026-08-25"}, format="json")
    assert again.status_code == 400
    r2 = admin_client.patch(f"/api/leave/sick-leaves/{r.data['id']}/", {"date_to": "2026-08-21"}, format="json")
    assert r2.status_code == 200 and Absence.objects.get(pk=sick.pk).date_to == date(2026, 8, 21)
    assert admin_client.delete(f"/api/leave/sick-leaves/{r.data['id']}/").status_code == 204
    assert not Absence.objects.filter(kind="sick").exists()
    preg = admin_client.post("/api/leave/sick-leaves/", {"employee": e.id, "number": "555", "kind": "pregnancy",
                                                         "date_from": "2026-09-01", "date_to": "2027-01-05"}, format="json")
    assert preg.status_code == 201 and preg.data["absence"] is None  # maternitatea intră prin ordin


def test_continued_sick_leave_is_closed(admin_client, org):
    """Certificatul continuat de altul e încheiat (data prezentării o are doar ultimul): nu mai e „deschis” nici în filtru,
    nici în listă; dacă continuarea se marchează pentru ștergere, redevine deschis."""
    e = person(org)
    first = admin_client.post("/api/leave/sick-leaves/", {"employee": e.id, "series": "A", "number": "1001", "kind": "illness",
                                                          "date_from": "2026-08-10", "date_to": "2026-08-19"}, format="json").data
    assert first["continued_by"] == ""
    nxt = admin_client.post("/api/leave/sick-leaves/", {"employee": e.id, "series": "A", "number": "1002", "kind": "illness",
                                                        "date_from": "2026-08-20", "date_to": "2026-08-28",
                                                        "continuation_of": first["id"]}, format="json")
    assert nxt.status_code == 201, nxt.data
    rows = {r["number"]: r for r in admin_client.get("/api/leave/sick-leaves/", {"employee": e.id}).data["results"]}
    assert rows["1001"]["continued_by"] == "Certificatul A 1002" and rows["1002"]["continued_by"] == ""
    is_open = lambda: [r["number"] for r in admin_client.get("/api/leave/sick-leaves/", {"employee": e.id, "open": 1}).data["results"]]
    assert is_open() == ["1002"]  # continuarea e încă deschisă (fără data prezentării)
    admin_client.patch(f"/api/leave/sick-leaves/{nxt.data['id']}/", {"return_date": "2026-08-29"}, format="json")
    assert is_open() == []
    admin_client.delete(f"/api/leave/sick-leaves/{nxt.data['id']}/")  # marcată pentru ștergere: nu mai continuă nimic
    assert is_open() == ["1001"]
    assert admin_client.get(f"/api/leave/sick-leaves/{first['id']}/").data["continued_by"] == ""



def test_schedule_counts_people_working_in_the_department_by_cumul(admin_client, org):
    a = person(org, "Popescu", "Ion")
    b = person(org, "Rusu", "Ana", sub="ati", occ="anest")
    staff.hire(b, kind="internal", subdivision=org["tr1"], occupation=org["doctor"], rate=Decimal("0.5"),
               date_from=date(2025, 1, 1))
    tr = admin_client.post("/api/leave/schedules/", {"year": 2027, "subdivision": org["tr1"].id}, format="json").data
    ati = admin_client.post("/api/leave/schedules/", {"year": 2027, "subdivision": org["ati"].id}, format="json").data
    tr_line = admin_client.get("/api/leave/schedule-lines/", {"schedule": tr["id"]}).data
    ati_line = admin_client.get("/api/leave/schedule-lines/", {"schedule": ati["id"]}).data
    assert [ln["employee"] for ln in tr_line] == [a.id]  # concediul se planifică în secția de bază
    admin_client.patch(f"/api/leave/schedule-lines/{tr_line[0]['id']}/", {"date_from": "2027-07-05"}, format="json")
    admin_client.patch(f"/api/leave/schedule-lines/{ati_line[0]['id']}/", {"date_from": "2027-07-19"}, format="json")
    report = admin_client.get(f"/api/leave/schedules/{tr['id']}/report/").data
    assert report["guests"][0]["name"] == "Rusu Ana" and report["guests"][0]["home"] == "Secția ATI"
    assert any(w["kind"] == "occupation" for w in report["warnings"])
    rows = admin_client.get(f"/api/leave/schedules/{ati['id']}/report/").data["rows"]
    assert rows[0]["other_jobs"] == ["Cumul intern: Medic traumatolog-ortoped, Secția traumatologie nr. 1 (50%)"]
