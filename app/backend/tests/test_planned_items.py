"""S3: acumulările planificate — tabelul „Acumulări și rețineri” din ordinele de personal, acumulările-tip ale funcției,
documentul „Modificarea acumulărilor planificate”, fila „Salariu” cu sursa rândului; scutirea la locul de cumul."""
from datetime import date
from decimal import Decimal

import pytest

from apps.orders.models import Order
from apps.payroll import engine
from apps.payroll.models import EmployeePayItem, ExemptionRequest, OccupationPayItem, PayItemChange, PaymentLine, PayType

from .test_orders import cancel, emp, make_order, set_params, sign
from .test_payroll import items_of, org, person  # noqa: F401 — fixtura și ajutoarele comune
from .test_payroll_payments import approved_payroll, paid_salary

D = Decimal


def ptype(code):
    return PayType.objects.get(code=code)


def rows_of(employee):
    return list(EmployeePayItem.objects.filter(employee=employee).select_related("pay_type").order_by("date_from", "id"))


# --- ordinul de angajare ------------------------------------------------------------------------------------------------
def test_hire_order_with_pay_items_sign_and_cancel(admin_client, org):  # noqa: F811
    dan = emp("Ceban", "Dan")
    order = make_order(admin_client, "hire", [dan])
    item = set_params(admin_client, order, {
        "kind": "main", "subdivision": org["ati"].id, "occupation": org["anest"].id, "rate": "1", "base_salary": "15200",
        "date_from": "2026-03-02",
        "pay_items": [{"pay_type": ptype("NOCIV").id, "action": "add", "percent": "10", "document": "CCM, anexa 2"},
                      {"pay_type": ptype("SINDICAT").id, "action": "add", "date_to": "2026-12-31"}]})
    assert "Acumulări și rețineri: se stabilește spor pentru condiții nocive / vătămătoare 10%" in item["text"]
    signed = sign(admin_client, order).data
    job = dan.employments.get()
    rows = rows_of(dan)
    assert [(r.pay_type.code, r.percent, r.date_from, r.date_to, r.employment_id) for r in rows] == [
        ("NOCIV", D("10"), date(2026, 3, 2), None, job.id), ("SINDICAT", None, date(2026, 3, 2), date(2026, 12, 31), job.id)]
    assert rows[0].document == "CCM, anexa 2" and rows[1].document == f"Ordinul nr. {signed['number']} din 02.03.2026"
    assert all(r.order_item_id == item["id"] for r in rows)
    # fila „Salariu”: sursa cu legătura; rândul din ordin nu se schimbă / nu se șterge de mână
    data = admin_client.get("/api/payroll/employee-items/", {"employee": dan.id}).data
    assert data[0]["source"] == {"kind": "order", "id": order["id"], "label": f"Ordinul nr. {signed['number']} din 02.03.2026",
                                 "status": "signed"}
    assert admin_client.patch(f"/api/payroll/employee-items/{rows[0].id}/", {"percent": "20"}, format="json").status_code == 400
    assert admin_client.patch(f"/api/payroll/employee-items/{rows[0].id}/", {"note": "verificat"}, format="json").status_code == 200
    assert admin_client.delete(f"/api/payroll/employee-items/{rows[0].id}/").status_code == 400
    # calculul lunii le folosește: NOCIV 10 % din salariu
    doc = engine.Payroll.objects.create(year=2026, month=3)
    engine.calculate(doc)
    assert items_of(doc.lines.get())["NOCIV"].percent == 10
    doc.delete()
    cancel(admin_client, signed)
    assert not EmployeePayItem.objects.filter(employee=dan).exists() and not dan.employments.exists()


def test_hire_order_fills_from_occupation_defaults(admin_client, org):  # noqa: F811
    OccupationPayItem.objects.create(occupation=org["anest"], pay_type=ptype("NOCIV"), percent=D("15"), sort=10)
    OccupationPayItem.objects.create(occupation=org["anest"], pay_type=ptype("SINDICAT"), sort=20)
    r = admin_client.get("/api/payroll/occupation-items/", {"occupation": org["anest"].id})
    assert [x["pay_type_code"] for x in r.data] == ["NOCIV", "SINDICAT"]
    dan = emp("Ceban", "Dan")
    order = make_order(admin_client, "hire", [dan])
    set_params(admin_client, order, {"kind": "main", "subdivision": org["ati"].id, "occupation": org["anest"].id,
                                     "base_salary": "15200", "date_from": "2026-03-02"})  # tabelul n-a fost atins
    signed = sign(admin_client, order).data
    assert [(r.pay_type.code, r.percent) for r in rows_of(dan)] == [("NOCIV", D("15")), ("SINDICAT", None)]
    stored = signed["items"][0]["params"]["pay_items"]  # ordinul păstrează ce s-a aplicat
    assert [x["pay_type"] for x in stored] == [ptype("NOCIV").id, ptype("SINDICAT").id]
    # tabelul golit de mână → nimic din funcție
    ana = emp("Rusu", "Ana")
    order = make_order(admin_client, "hire", [ana])
    set_params(admin_client, order, {"kind": "main", "subdivision": org["ati"].id, "occupation": org["anest"].id,
                                     "base_salary": "15200", "date_from": "2026-03-02", "pay_items": []})
    sign(admin_client, order)
    assert rows_of(ana) == []


# --- modificarea salariului: „oprește” / „modifică” ----------------------------------------------------------------------
def test_salary_order_stop_and_modify_then_cancel(admin_client, org):  # noqa: F811
    ion, job = person(org, "Popescu", "Ion")
    nociv = EmployeePayItem.objects.create(employee=ion, employment=job, pay_type=ptype("NOCIV"), percent=D("10"),
                                           date_from=date(2025, 1, 1))
    sind = EmployeePayItem.objects.create(employee=ion, pay_type=ptype("SINDICAT"), date_from=date(2025, 1, 1))
    order = make_order(admin_client, "allowance", [ion])
    # doar acumulările (fără schimbarea raportului de muncă)
    set_params(admin_client, order, {"date_from": "2026-04-01", "pay_items": [
        {"pay_type": ptype("NOCIV").id, "action": "modify", "percent": "20"},
        {"pay_type": ptype("SINDICAT").id, "action": "stop"},
        {"pay_type": ptype("IMPRUMUT").id, "action": "add", "amount": "500", "date_to": "2026-09-30", "document": "Contractul de împrumut nr. 3"}]})
    signed = sign(admin_client, order).data
    nociv.refresh_from_db()
    sind.refresh_from_db()
    assert nociv.date_to == date(2026, 3, 31) and sind.date_to == date(2026, 3, 31)  # cel de bază (fără raport) se găsește și el
    new = EmployeePayItem.objects.get(employee=ion, pay_type__code="NOCIV", date_from=date(2026, 4, 1))
    assert new.percent == 20 and new.date_to is None and new.employment_id == job.id and new.order_item_id
    loan = EmployeePayItem.objects.get(employee=ion, pay_type__code="IMPRUMUT")
    assert loan.amount == 500 and loan.date_to == date(2026, 9, 30)
    assert job.history.count() == 1  # raportul nu s-a schimbat
    # o oprire a unui rând care nu există: eroare clară, nimic pe jumătate
    bad = make_order(admin_client, "allowance", [ion])
    set_params(admin_client, bad, {"date_from": "2026-05-01", "pay_items": [
        {"pay_type": ptype("IMPRUMUT").id, "action": "add", "amount": "100"},
        {"pay_type": ptype("PENSIE").id, "action": "stop"}]})
    r = sign(admin_client, bad, ok=False)
    assert r.status_code == 400 and "nu are PENSIE" in r.data["detail"]
    assert EmployeePayItem.objects.filter(employee=ion, pay_type__code="IMPRUMUT").count() == 1
    assert Order.objects.get(pk=bad["id"]).status == "draft"
    cancel(admin_client, signed)
    nociv.refresh_from_db()
    sind.refresh_from_db()
    assert nociv.date_to is None and sind.date_to is None
    assert set(EmployeePayItem.objects.filter(employee=ion).values_list("pay_type__code", flat=True)) == {"NOCIV", "SINDICAT"}


# --- documentul separat -------------------------------------------------------------------------------------------------
def test_change_document_approve_unapprove_and_order_of_undo(admin_client, org):  # noqa: F811
    ion, job = person(org, "Popescu", "Ion")
    ana, job2 = person(org, "Rusu", "Ana")
    r = admin_client.post("/api/payroll/item-changes/", {"date": "2026-03-10", "lines": [
        {"employee": ion.id, "pay_type": ptype("PENSIE").id, "action": "add", "percent": "25", "document": "Titlul executoriu nr. 2-15/2026"},
        {"employee": ana.id, "employment": job2.id, "pay_type": ptype("SINDICAT").id, "action": "add", "document": "Cererea din 09.03.2026"},
    ]}, format="json")
    assert r.status_code == 201, r.data
    doc = PayItemChange.objects.get(pk=r.data["id"])
    assert doc.number.startswith("MA-") and doc.status == "draft" and r.data["employees"] == "Popescu I., Rusu A."
    assert not EmployeePayItem.objects.exists()
    bad = admin_client.post("/api/payroll/item-changes/", {"lines": [{"employee": ion.id, "employment": job2.id,
                                                                       "pay_type": ptype("PENSIE").id, "percent": "1"}]}, format="json")
    assert bad.status_code == 400  # raportul altui angajat
    ok = admin_client.post(f"/api/payroll/item-changes/{doc.id}/approve/")
    assert ok.status_code == 200 and ok.data["status"] == "approved"
    pensie = EmployeePayItem.objects.get(employee=ion)
    assert (pensie.percent, pensie.date_from, pensie.employment_id, pensie.document) == (
        D("25"), date(2026, 3, 10), None, "Titlul executoriu nr. 2-15/2026")
    assert EmployeePayItem.objects.get(employee=ana).employment_id == job2.id
    # aprobat — nu se mai modifică și nu se marchează
    assert admin_client.patch(f"/api/payroll/item-changes/{doc.id}/", {"note": "x"}, format="json").status_code == 400
    assert admin_client.delete(f"/api/payroll/item-changes/{doc.id}/").status_code == 400
    src = admin_client.get("/api/payroll/employee-items/", {"employee": ion.id}).data[0]["source"]
    assert src["kind"] == "change" and src["id"] == doc.id and doc.number in src["label"]
    # al doilea document oprește pensia; anularea primului se oprește până nu se anulează al doilea
    r = admin_client.post("/api/payroll/item-changes/", {"date": "2026-06-01", "lines": [
        {"employee": ion.id, "pay_type": ptype("PENSIE").id, "action": "stop", "document": "Hotărârea de încetare"}]}, format="json")
    doc2 = PayItemChange.objects.get(pk=r.data["id"])
    assert admin_client.post(f"/api/payroll/item-changes/{doc2.id}/approve/").status_code == 200
    pensie.refresh_from_db()
    assert pensie.date_to == date(2026, 5, 31)
    r = admin_client.post(f"/api/payroll/item-changes/{doc.id}/unapprove/")
    assert r.status_code == 400 and "anulați întâi documentul" in r.data["detail"]
    assert admin_client.post(f"/api/payroll/item-changes/{doc2.id}/unapprove/").status_code == 200
    pensie.refresh_from_db()
    assert pensie.date_to is None
    # rândul Anei e pe raportul ei de bază; un rând „oprește” fără raport ales îl găsește
    r = admin_client.post("/api/payroll/item-changes/", {"date": "2026-04-01", "lines": [
        {"employee": ana.id, "pay_type": ptype("SINDICAT").id, "action": "stop"}]}, format="json")
    doc3 = PayItemChange.objects.get(pk=r.data["id"])
    assert admin_client.post(f"/api/payroll/item-changes/{doc3.id}/approve/").status_code == 200
    assert EmployeePayItem.objects.get(employee=ana).date_to == date(2026, 3, 31)
    assert admin_client.post(f"/api/payroll/item-changes/{doc.id}/unapprove/").status_code == 400  # întâi doc3
    assert admin_client.post(f"/api/payroll/item-changes/{doc3.id}/unapprove/").status_code == 200
    assert admin_client.post(f"/api/payroll/item-changes/{doc.id}/unapprove/").status_code == 200
    assert not EmployeePayItem.objects.exists()
    # ciorna se poate marca pentru ștergere; tiparul
    html = admin_client.get(f"/api/payroll/item-changes/{doc.id}/print/").content.decode()
    assert "MODIFICAREA ACUMULĂRILOR PLANIFICATE" in html and "Titlul executoriu nr. 2-15/2026" in html and "Popescu Ion" in html
    assert admin_client.delete(f"/api/payroll/item-changes/{doc.id}/").status_code == 204
    assert PayItemChange.objects.get(pk=doc.id).deletion_mark


def test_change_document_needs_payroll_rights(org, make_user, client_for):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion")
    hr = client_for(make_user("hr", ["hr_inspector"]))
    r = hr.post("/api/payroll/item-changes/", {"lines": [{"employee": ion.id, "pay_type": ptype("PENSIE").id, "percent": "5"}]},
                format="json")
    assert r.status_code == 403


# --- scutirea la locul de cumul ------------------------------------------------------------------------------------------
def test_exemption_applies_when_the_only_job_here_is_external_cumul(admin_client, org):  # noqa: F811
    """Regulamentul aprobat prin HG 697/2014, pct. 9: angajatul poate cere scutirea la locul de muncă prin cumul; aici are doar
    cumulul extern — scutirea se acordă pe venitul de aici."""
    ion, job = person(org, "Popescu", "Ion", kind="external", rate="0.5", salary="12000")
    r = admin_client.post("/api/payroll/exemptions/", {"employee": ion.id, "date": "2025-12-20", "kind": "personal"}, format="json")
    assert r.status_code == 201 and r.data["place"] == "secondary" and r.data["place_label"] == "Locul de muncă prin cumul"
    req = ExemptionRequest.objects.get(pk=r.data["id"])
    approved_payroll(3)
    paid_salary(admin_client, 3, "2026-04-05")
    line = PaymentLine.objects.get(employee=ion)
    # 6 000 lei (0,5 normă): CNAM 9 % = 540; scutirea P 29 700 / 12 = 2 475; impozitul 12 % × (6 000 − 540 − 2 475) = 358,20
    assert line.gross == 6000 and line.exemption == D("2475") and line.income_tax == D("358.20")
    html = admin_client.get(f"/api/payroll/exemptions/{req.id}/print/").content.decode()
    assert "<b>locul de muncă prin cumul</b>" in html
    # la cel cu raport de bază — implicit locul de bază
    ana, _ = person(org, "Rusu", "Ana")
    r = admin_client.post("/api/payroll/exemptions/", {"employee": ana.id, "date": "2025-12-20", "kind": "personal"}, format="json")
    assert r.data["place"] == "main"
