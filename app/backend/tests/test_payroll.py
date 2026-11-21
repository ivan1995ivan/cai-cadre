"""Etapa 4b (partea 1): salarizarea — constantele, tipurile de calcul, scutirea, calculul lunii, rândurile de mână, tiparul."""
from datetime import date
from decimal import Decimal

import pytest

from apps.leave.models import SickLeave
from apps.leave import services as leave_services
from apps.org.models import Occupation, Subdivision
from apps.payroll import engine
from apps.payroll.models import EmployeePayItem, ExemptionRequest, PayConstant, Payment, Payroll, PayType
from apps.staff import services as staff
from apps.staff.models import Employee, PriorExperience
from apps.worktime import services as worktime
from apps.worktime.models import Timesheet

from .test_orders import make_order, set_params, sign


@pytest.fixture
def org(seeded):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1")
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția ATI")
    return {"tr1": tr1, "ati": ati, "doctor": Occupation.objects.get(name_ro="Medic traumatolog-ortoped"),
            "anest": Occupation.objects.get(name_ro="Medic anesteziolog-reanimatolog"),
            "nurse": Occupation.objects.get(name_ro="Asistent medical de secție")}


def person(org, last, first, occ="doctor", sub="tr1", salary="14660", hired=date(2020, 1, 1), **extra):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first)
    job = staff.hire(e, kind=extra.pop("kind", "main"), subdivision=org[sub], occupation=org[occ], rate=Decimal(extra.pop("rate", "1")),
                     base_salary=Decimal(salary), date_from=hired, **extra)
    return e, job


def items_of(line):
    return {i.pay_type.code: i for i in line.items.select_related("pay_type")}


# --- constantele și tipurile ---------------------------------------------------------------------------------------
def test_constants_history_and_type_validation(admin_client, seeded):
    assert PayConstant.objects.get(code="income_tax_pct").value == 12
    r = admin_client.post("/api/payroll/constants/", {"code": "income_tax_pct", "name": "Impozitul", "value": "13", "date_from": "2027-01-01"},
                          format="json")
    assert r.status_code == 201
    assert engine.Constants(date(2026, 12, 31))("income_tax_pct") == 12 and engine.Constants(date(2027, 1, 1))("income_tax_pct") == 13
    bad = admin_client.post("/api/payroll/types/", {"code": "X", "name_ro": "x", "formula": "scale", "scale": [{"pct": 5}]}, format="json")
    assert bad.status_code == 400
    # treptele pe categoria de calificare nu mai există: doar ani de vechime și procentul
    bad = admin_client.post("/api/payroll/types/", {"code": "X", "name_ro": "x", "formula": "scale", "scale": [{"category": "first", "pct": 5}]},
                            format="json")
    assert bad.status_code == 400
    bad = admin_client.post("/api/payroll/types/", {"code": "X", "name_ro": "x", "formula": "scale", "scale": [{"from": "doi", "pct": 5}]},
                            format="json")
    assert bad.status_code == 400
    # sporurile HG 837/2016 (vechimea, categoria) și gărzile nu se mai preîncarcă; NOCIV rămâne (Codul muncii, art. 139)
    assert not PayType.objects.filter(code__in=("VECH", "CATEG", "GARDA")).exists() and PayType.objects.filter(code="NOCIV").exists()
    assert PayType.objects.get(code="SINDICAT").base_codes == ["SAL", "SPOR", "CUMUL", "NOCIV", "NOAPTE", "SARB", "SUPL", "CO", "PREMIU"]
    ok = admin_client.post("/api/payroll/types/", {"code": "TRANSP", "name_ro": "Compensație transport", "formula": "fixed",
                                                   "taxable": False, "cas": False, "cnam": False}, format="json")
    assert ok.status_code == 201 and PayType.objects.get(code="TRANSP").is_system is False


# --- calculul lunii ---------------------------------------------------------------------------------------------------
def test_monthly_calculation_tax_exemption_scales_and_approval(admin_client, org):
    ion, _job = person(org, "Popescu", "Ion")
    # sporul pentru vechime din contractul colectiv al firmei: trepte pe vechimea totală (stagiul anterior + aici)
    PayType.objects.create(code="SPVECH", name_ro="Spor pentru vechime (contractul colectiv)", category="accrual", formula="scale",
                           base_codes=["SAL"], scale=[{"from": 3, "pct": 5}, {"from": 10, "pct": 10}, {"from": 20, "pct": 15}], sort=40)
    PriorExperience.objects.create(employee=ion, organization="„Alfa” SRL", date_from=date(2014, 1, 1), date_to=date(2019, 12, 31),
                                   in_specialty=False)  # 6 ani înainte + 6 ani aici = 12 ani → 10 %
    ExemptionRequest.objects.create(employee=ion, year=2026, kind="personal", dependents=[{"name": "Popescu Maria", "idnp": "", "disabled": False}])
    r = admin_client.post("/api/payroll/payrolls/", {"year": 2026, "month": 3, "date": "2026-04-02"}, format="json")
    assert r.status_code == 201, r.data
    doc = Payroll.objects.get(pk=r.data["id"])
    assert doc.number and doc.lines.count() == 1
    line = doc.lines.get()
    it = items_of(line)
    assert it["SAL"].amount == Decimal("14660") and it["SAL"].quantity == Decimal("154")  # fără pontaj: norma întreagă (22 × 7)
    assert it["SPVECH"].percent == 10 and it["SPVECH"].amount == Decimal("1466")
    gross = Decimal("14660") + 1466
    assert line.gross == gross == Decimal("16126")
    # calculul: bazele și CAS; impozitul, scutirea și CNAM nu sunt aici
    assert (line.taxable, line.cnam_base, line.deductions, line.net) == (gross, gross, 0, gross)
    assert set(it) == {"SAL", "SPVECH", "CAS"}
    assert line.cas == Decimal("3870.24") and it["CAS"].pay_type.category == "employer"
    assert doc.totals["net"] == 16126 and doc.totals["cas"] == 3870.24 and doc.totals["lines"] == 1
    # rând de mână: premiu unic; rămâne la recalculare și intră în impozit
    r = admin_client.post("/api/payroll/items/", {"line": line.id, "pay_type": PayType.objects.get(code="ALTE").id, "amount": "1000",
                                                  "note": "premiu unic"}, format="json")
    assert r.status_code == 201, r.data
    line.refresh_from_db()
    assert line.gross == Decimal("17126") and items_of(line)["ALTE"].manual
    admin_client.post(f"/api/payroll/payrolls/{doc.id}/calculate/")
    line.refresh_from_db()
    assert line.gross == Decimal("17126")
    # impozitul pe venit, scutirea și CNAM nu se corectează în calcul (se rețin la plată)
    r = admin_client.post("/api/payroll/items/", {"line": line.id, "pay_type": PayType.objects.get(code="IMPOZIT").id, "amount": "1"},
                          format="json")
    assert r.status_code == 400 and "plată" in str(r.data)
    assert admin_client.post(f"/api/payroll/payrolls/{doc.id}/approve/").data["status"] == "approved"
    assert admin_client.post(f"/api/payroll/payrolls/{doc.id}/calculate/").status_code == 400
    # îndreptarea spre plată în baza calculului: CNAM 9 %, scutirea lunii (29 700 + 9 900) / 12 și impozitul 12 % din rest
    r = admin_client.post("/api/payroll/payments/", {"payroll": doc.id, "kind": "salary", "date": "2026-04-05"}, format="json")
    assert r.status_code == 201, r.data
    assert (r.data["year"], r.data["month"], r.data["payroll"]) == (2026, 3, doc.id)
    pl = Payment.objects.get(pk=r.data["id"]).lines.get()
    assert (pl.gross, pl.cnam, pl.exemption) == (Decimal("17126"), Decimal("1541.34"), Decimal("3300"))
    assert pl.income_tax == engine.q((Decimal("17126") - Decimal("1541.34") - 3300) * Decimal("0.12")) == Decimal("1474.16")
    assert pl.amount == Decimal("17126") - pl.cnam - pl.income_tax
    # calculul cu o îndreptare aprobată în baza lui nu se redeschide
    admin_client.post(f"/api/payroll/payments/{pl.payment_id}/approve/")
    r = admin_client.post(f"/api/payroll/payrolls/{doc.id}/reopen/")
    assert r.status_code == 400 and "îndreptări" in r.data["detail"]
    html = admin_client.get(f"/api/payroll/payrolls/{doc.id}/print/").content.decode()
    assert "STAT DE CALCUL" in html and "Popescu Ion" in html and "15" in html
    # fluturașul — din îndreptarea pe salariu (din calcul nu se mai face)
    assert admin_client.get(f"/api/payroll/payrolls/{doc.id}/payslip/").status_code == 404
    slip = admin_client.get(f"/api/payroll/payments/{pl.payment_id}/payslip/", {"employee": line.employee_id}).content.decode()
    assert "Fișa de calcul" in slip and "Spor pentru vechime" in slip and "Impozitul pe venit" in slip and "1 474,16" in slip


def test_timesheet_sick_bonus_union_cumul_and_contract(admin_client, org):
    ana, job = person(org, "Rusu", "Ana", occ="nurse", salary="9200", hired=date(2024, 3, 1))
    cumul = staff.hire(ana, kind="internal", subdivision=org["ati"], occupation=org["anest"], rate=Decimal("0.25"),
                       base_salary=Decimal("15200"), combination_pct=Decimal("30"), date_from=date(2025, 1, 1))
    dan, _ = person(org, "Ceban", "Dan", kind="contractor", sub="ati", occ="anest", salary="0", rate="0.5", hired=date(2026, 1, 1))
    EmployeePayItem.objects.create(employee=dan, pay_type=PayType.objects.get(code="CONTRACT"), amount=Decimal("6000"), date_from=date(2026, 1, 1))
    EmployeePayItem.objects.create(employee=ana, pay_type=PayType.objects.get(code="SINDICAT"), date_from=date(2026, 1, 1))
    sick = SickLeave(employee=ana, series="A", number="1", kind="illness", date_from=date(2026, 3, 10), date_to=date(2026, 3, 19))
    leave_services.save_sick_leave(sick)
    bonus = make_order(admin_client, "bonus", [ana], date_="2026-03-20")
    set_params(admin_client, bonus, {"amount": "500", "note": "pentru martie"})
    sign(admin_client, bonus)
    for sub in ("tr1", "ati"):
        worktime.fill_timesheet(Timesheet.objects.create(subdivision=org[sub], year=2026, month=3))
    doc = Payroll.objects.create(year=2026, month=3)
    engine.calculate(doc)
    lines = {(ln.employee.last_name, ln.employment.kind): ln for ln in doc.lines.select_related("employee", "employment")}
    main = lines[("Rusu", "main")]
    it = items_of(main)
    # 8 zile lucrătoare de boală din 22: 14 zile × 7 ore = 98 ore din norma 154
    assert it["SAL"].quantity == Decimal("98") and it["SAL"].amount == Decimal("5854.55")
    assert it["BOALA"].quantity == 5 and it["BOALA"].percent == 75 and it["BOALA"].amount == Decimal("1150.01")  # 9 200 / 30 zile × 5 × 75 %
    assert it["PREMIU"].amount == Decimal("500") and "pentru martie" in it["PREMIU"].note
    assert it["SINDICAT"].percent == 1 and it["SINDICAT"].amount == engine.q((it["SAL"].amount + it["PREMIU"].amount) / 100)
    assert main.deductions == it["SINDICAT"].amount and main.net == main.gross - main.deductions
    assert main.taxable == main.cnam_base == main.gross  # boala: fără CAS, dar cu impozit și CNAM
    second = lines[("Rusu", "internal")]
    it2 = items_of(second)
    # 15 200 × 0,25 = 3 800 pe lună, pro-rata la orele lucrate (boala ține și la cumul): 24,5 din 38,5 ore; + 30 % cumul
    assert it2["SAL"].amount == Decimal("2418.18") and it2["CUMUL"].amount == Decimal("725.45")
    assert "BOALA" not in it2 and "PREMIU" not in it2 and "SINDICAT" not in it2  # cele pe persoană merg la raportul de bază
    contract = lines[("Ceban", "contractor")]
    it3 = items_of(contract)
    assert set(it3) == {"CONTRACT", "CAS"} and it3["CONTRACT"].amount == Decimal("6000")
    assert (contract.taxable, contract.cnam_base, contract.cas) == (Decimal("6000"), Decimal("6000"), Decimal("1440"))
    assert doc.totals["lines"] == 3
    # media pentru concediu din luna aprobată: aprilie cu 14 zile de concediu
    doc.status = "approved"
    doc.save()
    from apps.leave.models import Absence

    Absence.objects.create(employee=ana, employment=job, kind="annual", date_from=date(2026, 4, 1), date_to=date(2026, 4, 16), days=14)
    worktime.fill_timesheet(Timesheet.objects.create(subdivision=org["tr1"], year=2026, month=4))
    april = Payroll.objects.create(year=2026, month=4, subdivision=org["tr1"])
    engine.calculate(april)
    co = items_of(april.lines.get(employment=job))["CO"]
    assert co.quantity == 14 and co.base > 0 and "1 luni" in co.note  # media pe luna martie (aprobată)


def test_department_head_cannot_see_whole_institution_payroll(org, admin_client, make_user, client_for):
    person(org, "Popescu", "Ion")
    Payroll.objects.create(year=2026, month=3)
    head = make_user("sef", ["department_head"])
    org["tr1"].users.add(head)
    api = client_for(head)
    assert api.get("/api/payroll/payrolls/").status_code == 403  # șeful de secție nu are drept la salarizare
    acc = make_user("contabil", ["accountant"])
    api = client_for(acc)
    assert api.get("/api/payroll/payrolls/").data["count"] == 1
    r = api.post("/api/payroll/exemptions/", {"employee": Employee.objects.get().id, "year": 2026, "kind": "major", "spouse": True,
                                              "dependents": [{"name": "A", "disabled": True}]}, format="json")
    assert r.status_code == 201 and r.data["code"] == "MSH1"
