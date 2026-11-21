"""S4: regimul fiscal IT Park, pe exemple calculate de mână.

Regimul: general până în iunie 2026, IT Park din iulie 2026 (statutul obținut în iunie — CF art. 375). Fără pontaj, luna se
socotește lucrată întreagă. Constantele 2026: salariul mediu 17 400 → minimul pe angajat 30 % = 5 220 lei, venitul asigurat
68 % = 11 832 lei; CAS 24 %, CNAM 9 %, impozitul 12 %, scutirea personală 29 700 / 12 = 2 475 lei pe lună."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from xml.etree import ElementTree as ET

import pytest
from openpyxl import load_workbook

from apps.leave import services as leave_services
from apps.leave.models import Absence, SickLeave
from apps.payroll import engine, it_park
from apps.payroll.exemptions import month_parts
from apps.payroll.models import (EmployeePayItem, ExemptionRequest, FiscalRegime, ItParkMonth, Payment, PaymentLine, Payroll,
                                 PayrollLine, PayType)

from .test_payroll import items_of, org, person  # noqa: F401 — fixtura și ajutoarele comune

D = Decimal


@pytest.fixture
def regime(seeded):
    """IT Park din iulie 2026: dat cu data obținerii statutului (15.06.2026) → luna următoare."""
    FiscalRegime.objects.create(regime="general", date_from=date(2020, 1, 1))
    return FiscalRegime.objects.create(regime="it_park", status_date=date(2026, 6, 15), document="Certificatul de rezident nr. 1")


def calc(month, approve=True):
    doc = Payroll.objects.create(year=2026, month=month)
    engine.calculate(doc)
    if approve:
        doc.status = "approved"
        doc.save()
    return doc


def pay(client, month, paid_on, kind="salary"):
    r = client.post("/api/payroll/payments/", {"year": 2026, "month": month, "kind": kind, "date": paid_on}, format="json")
    assert r.status_code == 201, r.data
    p = Payment.objects.get(pk=r.data["id"])
    assert client.post(f"/api/payroll/payments/{p.id}/approve/").status_code == 200
    assert client.post(f"/api/payroll/payments/{p.id}/pay/", {"paid_on": paid_on}, format="json").status_code == 200
    return p


def union(emp, pct="1"):
    EmployeePayItem.objects.create(employee=emp, pay_type=PayType.objects.get(code="SINDICAT"), percent=D(pct), date_from=date(2026, 1, 1))


def contractor(org, amount="10000"):  # noqa: F811
    e, job = person(org, "Ceban", "Dan", salary="0", kind="contractor")
    EmployeePayItem.objects.create(employee=e, employment=job, pay_type=PayType.objects.get(code="CONTRACT"), amount=D(amount),
                                   date_from=date(2026, 1, 1))
    return e, job


# --- regimul pe luni --------------------------------------------------------------------------------------------------
def test_regime_history_month_after_status(admin_client, regime):
    assert regime.date_from == date(2026, 7, 1)  # din luna următoare obținerii statutului (CF art. 375)
    assert not it_park.is_it_park(2026, 6) and it_park.is_it_park(2026, 7) and it_park.is_it_park(2027, 3)
    # retragerea statutului în martie 2027 → regimul general din aprilie; lunile vechi rămân în regimul lor
    r = admin_client.post("/api/payroll/fiscal-regimes/", {"regime": "general", "status_date": "2027-03-10"}, format="json")
    assert r.status_code == 201 and r.data["date_from"] == "2027-04-01"
    assert it_park.is_it_park(2027, 3) and not it_park.is_it_park(2027, 4) and it_park.is_it_park(2026, 12)
    # luna dată înainte de luna următoare statutului — refuzată; aceeași lună de două ori — refuzată
    bad = admin_client.post("/api/payroll/fiscal-regimes/", {"regime": "it_park", "status_date": "2027-05-20", "date_from": "2027-05-01"},
                            format="json")
    assert bad.status_code == 400
    bad = admin_client.post("/api/payroll/fiscal-regimes/", {"regime": "it_park", "date_from": "2027-04-15"}, format="json")
    assert bad.status_code == 400
    assert it_park.it_park_months(date(2026, 5, 1), date(2027, 5, 1)) == {(2026, m) for m in range(7, 13)} | {(2027, m) for m in (1, 2, 3)}
    # constantele IT Park, cu cele neconfirmate marcate
    c = engine.Constants(date(2026, 7, 31))
    assert (c("it_park_tax_pct"), c("it_park_min_pct"), c("it_park_insured_pct"), c("it_park_sick_covered")) == (7, 30, 68, 1)
    assert it_park.insured_income(c) == D("11832.00")
    from apps.payroll.models import PayConstant

    assert "de verificat" in PayConstant.objects.get(code="it_park_sick_covered").source


# --- calculul lunii și plata --------------------------------------------------------------------------------------------
def test_month_in_regime_salary_net_equals_gross_minus_union_contractor_taxed(admin_client, org, regime):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="30000")
    union(ion)
    ExemptionRequest.objects.create(employee=ion, date=date(2025, 12, 20), kind="personal")  # P — nu se acordă în regim
    dan, _ = contractor(org)
    doc = calc(7)
    ln = doc.lines.get(employee=ion)
    it = items_of(ln)
    # salariul impozitat final: fără bazele impozitului / CNAM, fără CAS și CASMIN; sindicatul 1 % × 30 000 = 300
    assert ln.it_park and (ln.gross, ln.taxable, ln.cnam_base, ln.cas) == (D("30000"), 0, 0, 0)
    assert "CAS" not in it and "CASMIN" not in it and it["SINDICAT"].amount == D("300") and ln.net == D("29700")
    assert ln.info["regime_note"].startswith("Impozitat final")
    # prestatorul de servicii rămâne în regimul general: CAS 24 % = 2 400, bazele impozitului și CNAM = 10 000
    lc = doc.lines.get(employee=dan)
    assert not lc.it_park and (lc.taxable, lc.cnam_base, lc.cas) == (D("10000"), D("10000"), D("2400"))
    p = pay(admin_client, 7, "2026-08-05")
    li, ld = p.lines.get(employee=ion), p.lines.get(employee=dan)
    # angajatul: nimic reținut, net = 30 000 − 300; tot venitul plătit e impozitat final
    assert (li.cnam, li.income_tax, li.exemption, li.deductions, li.amount, li.final_gross) == (0, 0, 0, D("300"), D("29700"), D("30000"))
    # prestatorul: CNAM 9 % = 900, impozitul 12 % × (10 000 − 900) = 1 092, fără scutire
    assert (ld.cnam, ld.income_tax, ld.amount, ld.final_gross) == (D("900"), D("1092"), D("8008"), 0)
    # scutirile în luna din regim: nimic (CF art. 377 alin. (2)), cu explicația în cerere
    assert month_parts(2026, 7, engine.Constants(date(2026, 7, 31)), {ion.pk: D("0")})[ion.pk]["P"] == 0
    r = admin_client.get("/api/payroll/exemptions/", {"employee": ion.pk})
    assert any("IT Park" in w and "art. 377" in w for w in r.data[0]["warnings"])


def test_minimum_wage_completion_stays_in_regime(org, regime):  # noqa: F811
    low, _ = person(org, "Rusu", "Ana", salary="5000")
    it = items_of(calc(7).lines.get(employee=low))
    assert it["MINIM"].amount == D("1300") and "CASMIN" not in it  # 6 300 − 5 000; baza minimă CAS nu se aplică


def test_advance_in_regime_is_paid_whole(admin_client, org, regime):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="30000")
    adv = pay(admin_client, 7, "2026-07-20", kind="advance")
    a = adv.lines.get(employee=ion)
    assert (a.gross, a.cnam, a.income_tax, a.amount, a.final_gross) == (D("12000"), 0, 0, D("12000"), D("12000"))  # 40 %
    calc(7)
    s = pay(admin_client, 7, "2026-08-05").lines.get(employee=ion)
    assert (s.gross, s.cnam, s.income_tax, s.final_gross, s.amount) == (D("18000"), 0, 0, D("18000"), D("18000"))


# --- schimbarea regimului ------------------------------------------------------------------------------------------------
def test_regime_change_june_general_july_it_and_june_salary_paid_in_july(admin_client, org, regime):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="30000")
    ion.idnp = "2001000123456"
    ion.save()
    ExemptionRequest.objects.create(employee=ion, date=date(2025, 12, 20), kind="personal")
    june = calc(6).lines.get(employee=ion)
    assert not june.it_park and june.taxable == D("30000") and june.cas == D("7200")  # regimul general: 24 %
    july = calc(7).lines.get(employee=ion)
    assert july.it_park and july.taxable == 0 and july.cas == 0
    # salariul lui iunie plătit în iulie: regimul lui iunie (CF art. 375) — CNAM 2 700, scutirea 2 475,
    # impozitul 12 % × (30 000 − 2 700 − 2 475) = 2 979
    pj = pay(admin_client, 6, "2026-07-10").lines.get(employee=ion)
    assert (pj.cnam, pj.exemption, pj.income_tax, pj.final_gross) == (D("2700"), D("2475"), D("2979"), 0)
    pay(admin_client, 7, "2026-07-31")  # salariul din regim plătit tot în iulie
    # IPC21 iulie: bifa de rezident; tabelul 1 doar cu salariul lui iunie (regimul general)
    r = admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 7})
    assert r.data["it_park"] and r.data["table1"] == {"income": 30000.0, "tax": 2979.0, "cnam": 2700.0}
    assert r.data["final_income"] == 30000.0
    x = ET.fromstring(admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 7, "export": "xml"}).content)
    assert x.findtext("table1/it/flag1") == "1" and x.findtext("table1/row/r11c4") == "30000.00"
    x6 = ET.fromstring(admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 6, "export": "xml"}).content)
    assert x6.findtext("table1/it/flag1") == "0"
    # IALS21 — doar lunile generale; ISAPTI17 și nota anuală — lunile din regim
    ials = admin_client.get("/api/payroll/tax-reports/ials21/", {"year": 2026}).data
    row = next(x for x in ials["rows"] if x["idnp"] == "2001000123456")
    assert (row["income"], row["P"], row["tax"]) == (30000.0, 2475.0, 2979.0)
    isa = admin_client.get("/api/payroll/tax-reports/isapti17/", {"year": 2026}).data
    assert [(x["idnp"], x["income"], x["months"]) for x in isa["rows"]] == [("2001000123456", 30000.0, 1)]
    # fișa personală (anexa 8): fără plata din regim
    card = admin_client.get(f"/api/payroll/annual-card/{ion.pk}/", {"year": 2026}).data
    assert [r["gross"] for r in card["rows"]] == [30000.0] and card["final_income"] == 30000.0
    # tiparul: ISAPTI17, nota anuală (anexa 5), Excel
    html = admin_client.get("/api/payroll/tax-reports/isapti17/", {"year": 2026, "print": 1}).content.decode()
    assert "ISAPTI17" in html and "30 000,00" in html and "Popescu Ion" in html
    note = admin_client.get("/api/payroll/tax-reports/isapti17/", {"year": 2026, "print": "notes", "employee": ion.pk}).content.decode()
    assert "anexa nr. 5" in note and "30 000,00" in note and "iulie" in note
    wb = load_workbook(BytesIO(admin_client.get("/api/payroll/tax-reports/isapti17/", {"year": 2026, "export": "xlsx"}).content))
    assert wb["ISAPTI17"]["D2"].value == 30000.0 and wb["ISAPTI17"]["E2"].value == 1


def test_no_exemptions_in_regime_months_and_pro_rata_in_general(admin_client, org, regime):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="30000")
    ExemptionRequest.objects.create(employee=ion, date=date(2025, 12, 20), kind="personal")
    for m in (5, 6, 7, 8):
        calc(m)
    c = engine.Constants(date(2026, 8, 31))
    got = {m: month_parts(2026, m, c, {ion.pk: D("1")})[ion.pk]["P"] for m in (5, 6, 7, 8)}
    assert got == {5: D("29700"), 6: D("29700"), 7: 0, 8: 0}  # suma anuală; pe lună / 12 — doar în lunile generale


# --- impozitul unic ------------------------------------------------------------------------------------------------------
def test_single_tax_minimum_and_seven_percent(admin_client, org, regime):  # noqa: F811
    person(org, "Popescu", "Ion", salary="30000")
    person(org, "Rusu", "Ana", salary="20000", rate="0.5")  # timp parțial — se numără întreg
    contractor(org)  # prestatorul nu se numără
    r = admin_client.get("/api/payroll/it-park/2026/7/")
    assert r.status_code == 200 and r.data["employees"] == 2 and r.data["per_employee"] == 5220.0
    assert r.data["minimum"] == 10440.0 and r.data["due"] == 10440.0 and not r.data["sales_entered"]
    # venit mic: 7 % × 50 000 = 3 500 < 2 × 5 220 → minimul
    r = admin_client.put("/api/payroll/it-park/2026/7/", {"sales_income": "50000"}, format="json")
    assert r.status_code == 200 and r.data["by_sales"] == 3500.0 and r.data["due"] == 10440.0 and r.data["rule"] == "minimum"
    assert [(x["code"], x["amount"]) for x in r.data["rows"]] == [("010", 3500.0), ("020", 10440.0), ("030", 10440.0)]
    # venit mare: 7 % × 1 000 000 = 70 000
    r = admin_client.put("/api/payroll/it-park/2026/7/", {"sales_income": "1000000"}, format="json")
    assert r.data["due"] == 70000.0 and r.data["rule"] == "sales"
    assert ItParkMonth.objects.get(year=2026, month=7).sales_income == D("1000000")
    assert admin_client.put("/api/payroll/it-park/2026/7/", {"sales_income": "-1"}, format="json").status_code == 400
    # lista anului, Excel, tiparul
    y = admin_client.get("/api/payroll/it-park/", {"year": 2026}).data
    # lunile în regim până la luna curentă (cele viitoare nu apar)
    from django.utils import timezone

    today = timezone.localdate()
    last = 12 if today.year > 2026 else today.month
    assert [m["month"] for m in y["months"]] == list(range(7, last + 1)) and y["months"][0]["due"] == 70000.0
    wb = load_workbook(BytesIO(admin_client.get("/api/payroll/it-park/2026/7/", {"export": "xlsx"}).content))
    assert wb["IU17 (calculul)"]["E4"].value == 70000.0 and wb["Angajații (rd. 020)"].max_row == 3
    html = admin_client.get("/api/payroll/it-park/2026/7/", {"print": 1}).content.decode()
    assert "70 000,00" in html and "Popescu Ion" in html


def test_headcount_one_day_counts_unpaid_month_does_not_maternity_counts(org, regime):  # noqa: F811
    person(org, "Ceban", "Dan", hired=date(2026, 7, 31))  # vineri 31 iulie — o zi lucrată
    away, away_job = person(org, "Rusu", "Ana")
    Absence.objects.create(employee=away, employment=away_job, kind="unpaid", date_from=date(2026, 7, 1), date_to=date(2026, 7, 31), days=31)
    mom, mom_job = person(org, "Lungu", "Maria")
    Absence.objects.create(employee=mom, employment=mom_job, kind="maternity", date_from=date(2026, 6, 1), date_to=date(2026, 10, 15), days=137)
    people = {p["name"]: p for p in it_park.headcount(2026, 7)}
    assert people["Ceban Dan"]["counted"] and people["Ceban Dan"]["worked_days"] == 1
    assert not people["Rusu Ana"]["counted"] and people["Rusu Ana"]["reason"] == "nicio zi lucrată în lună"
    assert people["Lungu Maria"]["counted"] and "maternitate" in people["Lungu Maria"]["reason"]
    assert it_park.month_tax(2026, 7)["employees"] == 2
    from apps.payroll.models import PayConstant

    PayConstant.objects.filter(code="it_park_count_maternity").update(value=0)
    assert it_park.month_tax(2026, 7)["employees"] == 1


def test_sales_alert_after_the_20th(org, regime):  # noqa: F811
    from apps.payroll.alerts import _it_park_sales

    assert _it_park_sales(date(2026, 8, 19), 0, {}) == []
    got = _it_park_sales(date(2026, 8, 20), 0, {})
    assert [a.key for a in got] == ["itsales:2026-07"] and got[0].due == date(2026, 8, 25)
    ItParkMonth.objects.create(year=2026, month=7, sales_income=D("0"))  # zero scris — e scris
    assert _it_park_sales(date(2026, 8, 20), 0, {}) == []


# --- IPC21: venitul asigurat ---------------------------------------------------------------------------------------------
def test_ipc21_category_162_insured_income_split_with_leave(admin_client, org, regime):  # noqa: F811
    ion, job = person(org, "Popescu", "Ion", salary="30000")
    ion.idnp = "2001000123456"
    ion.save()
    dan, _ = contractor(org)
    # concediul de odihnă 20–31 iulie: 12 zile calendaristice din 31
    Absence.objects.create(employee=ion, employment=job, kind="annual", date_from=date(2026, 7, 20), date_to=date(2026, 7, 31), days=12)
    calc(7)
    data = admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 7}).data
    mine = [(r["category"], r["base"], r["tariff"], r["cas"]) for r in data["rows"] if r["idnp"] == "2001000123456"]
    # 11 832 × 19 / 31 = 7 251,87 (muncă) și restul 4 580,13 (concediul) — o dată pe persoană, fără CAS
    assert mine == [("162", 7251.87, 0.0, 0.0), ("160", 4580.13, 0.0, 0.0)]
    contr = [r for r in data["rows"] if r["name"] == "Ceban Dan"]
    assert [(r["category"], r["base"], r["cas"]) for r in contr] == [("105", 10000.0, 2400.0)]


def test_ipc21_sick_days_share_and_sick_pay_on_insured_income(admin_client, org, regime):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="30000", hired=date(2026, 7, 1))
    calc(7)  # iulie în regim: venitul asigurat 11 832 intră în media pentru boală
    s = SickLeave(employee=ion, series="A", number="1", kind="illness", date_from=date(2026, 8, 3), date_to=date(2026, 8, 7))
    leave_services.save_sick_leave(s)
    it = items_of(calc(8).lines.get(employee=ion))
    # media: 11 832 / 31 zile (august) = 381,68 pe zi; 75 % × 5 zile = 1 431,30 (nu salariul de 30 000)
    assert it["BOALA"].base == D("381.68") and it["BOALA"].amount == D("1431.30")
    rows = [(r["category"], r["base"], r["sick"]) for r in
            admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 8}).data["rows"]]
    # 11 832 × 5 / 31 = 1 908,39 pe zilele de boală ale angajatorului (15311), restul 9 923,61 — muncă (162)
    assert rows == [("162", 9923.61, 0.0), ("15311", 1908.39, 1431.3)]


def test_ipc21_unpaid_whole_month_is_159_without_insured_income(admin_client, org, regime):  # noqa: F811
    away, job = person(org, "Rusu", "Ana")
    Absence.objects.create(employee=away, employment=job, kind="unpaid", date_from=date(2026, 7, 1), date_to=date(2026, 7, 31), days=31)
    calc(7)
    rows = admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 7}).data["rows"]
    assert [(r["category"], r["base"]) for r in rows] == [("159", 0.0)]


# --- formele ---------------------------------------------------------------------------------------------------------------
def test_payslip_and_sheet_say_final_taxation_without_empty_tax_columns(admin_client, org, regime):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="30000")
    doc = calc(7)
    p = pay(admin_client, 7, "2026-08-05")
    sheet = admin_client.get(f"/api/payroll/payrolls/{doc.id}/print/").content.decode()
    assert "Impozitat final — impozit unic IT Park" in sheet and "Baza impozitului" not in sheet and "CAS angajator" not in sheet
    slip = admin_client.get(f"/api/payroll/payments/{p.id}/payslip/").content.decode()
    assert "impozitul pe venit și prima CNAM nu se rețin" in slip and "Prima de asigurare medicală (CNAM)" not in slip
    # cartea privind salariul: lunile din regim în rezumat
    r = admin_client.get("/api/reports/salary_book/", {"date_from": "2026-07-01", "date_to": "2026-07-31"})
    assert r.status_code == 200, r.data
    assert any("07.2026" in str(s["value"]) and "art. 377" in str(s["value"]) for s in r.data["summary"])
    assert PaymentLine.objects.get(payment=p).final_gross == D("30000")
    assert PayrollLine.objects.get(payroll=doc).it_park
