"""S5b — fabrica: timpul fără producție. Staționarea și șomajul tehnic din ordin (CM art. 80, 80¹), garanția la neîndeplinirea
normei în acord (CM art. 161), sporul pentru condiții vătămătoare din subdiviziune / funcție, evidența globală a timpului de
muncă (CM art. 99), borderoul tichetelor de masă (Legea 166/2017, HG 227/2018) și partea impozabilă în salariu; plus salariul
celui angajat în lună (partea din norma lunii întregi).

Luna de probă: martie 2026 — 22 de zile lucrătoare, funcțiile de test au 35 h pe săptămână (7 ore pe zi), norma 154 de ore;
salariul 15 400 lei → 100 lei pe oră."""
from datetime import date, time
from decimal import Decimal

import pytest

from apps.leave.models import Absence
from apps.payroll import engine
from apps.payroll.models import EmployeePayItem, PayConstant, Payroll, PayType
from apps.worktime import services as worktime
from apps.worktime.models import JobSchedule, ShiftType, Timesheet, WorkSchedule

from .test_orders import make_order, set_params, sign
from .test_payroll import org, person  # noqa: F401 — fixtura și ajutoarele comune
from .test_production import approve, factory, grid, operation, report, worker  # noqa: F401

D = Decimal


def items(doc, job):
    return {i.pay_type.code: i for i in doc.lines.get(employment=job).items.select_related("pay_type")}


def calc(year=2026, month=3):
    Payroll.objects.filter(year=year, month=month).delete()
    doc = Payroll.objects.create(year=year, month=month)
    engine.calculate(doc)
    return doc


def timesheet(sub, year=2026, month=3):
    ts, _ = Timesheet.objects.get_or_create(subdivision=sub, year=year, month=month)
    worktime.fill_timesheet(ts)
    return ts


# --- salariul celui angajat în lună -------------------------------------------------------------------------------------------
def test_mid_month_hire_gets_the_share_of_the_full_month(org):  # noqa: F811
    _e, job = person(org, "Nou", "Ion", salary="15400", hired=date(2026, 3, 16))
    pay = items(calc(), job)
    # 16–31 martie: 12 zile × 7 ore = 84 din norma lunii întregi 154 → 15 400 × 84 / 154 = 8 400 (nu salariul întreg)
    assert pay["SAL"].amount == D("8400")
    line = calc().lines.get(employment=job)
    assert line.info["month_norm"] == 154.0 and line.info["hourly"] == 100.0


# --- staționarea și șomajul tehnic ------------------------------------------------------------------------------------------------
def test_idle_and_technical_unemployment_from_orders(admin_client, org):  # noqa: F811
    a_emp, a = person(org, "Arama", "Ana", salary="15400")
    b_emp, b = person(org, "Botnaru", "Bogdan", salary="15400")
    c_emp, c = person(org, "Cojocaru", "Ciprian", salary="3000")
    d_emp, d = person(org, "Dodon", "Dan", salary="15400", sub="ati", occ="anest")
    # staționarea atelierului: ordinul colectiv, primul punct cu perioada și cauza, apoi toată subdiviziunea
    order = make_order(admin_client, "idle", [a_emp])
    set_params(admin_client, order, {"date_from": "2026-03-02", "date_to": "2026-03-03", "cause": "employer"})
    r = admin_client.post(f"/api/orders/orders/{order['id']}/add-subdivision/", {"subdivision": org["tr1"].id}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["added"] == 2 and {i["employee"] for i in r.data["items"]} == {a_emp.id, b_emp.id, c_emp.id}
    assert all(i["params"]["cause"] == "employer" and i["params"]["date_to"] == "2026-03-03" for i in r.data["items"])
    order = r.data
    # B și C: fără vina părților; „Copiază parametrii” de la B la C
    set_params(admin_client, order, {**order["items"][1]["params"], "cause": "nobody"}, idx=1)
    cp = admin_client.post(f"/api/orders/items/{order['items'][1]['id']}/copy-params/")
    assert cp.status_code == 200 and cp.data["changed"] == 2
    set_params(admin_client, order, {**order["items"][0]["params"], "cause": "employer"}, idx=0)
    signed = sign(admin_client, order).data
    assert "din vina angajatorului" in signed["items"][0]["text"] and "integral" in signed["items"][0]["text"]
    assert "2/3 din salariul de bază" in signed["items"][1]["text"]
    assert Absence.objects.filter(kind="idle").count() == 3
    assert Absence.objects.get(employee=b_emp, kind="idle").cause == "nobody"
    # șomajul tehnic: fără procent — 50 % din Constante
    tech = make_order(admin_client, "tech_unemployment", [d_emp])
    set_params(admin_client, tech, {"date_from": "2026-03-09", "date_to": "2026-03-10"})
    assert "de cel puțin 50% din salariul de bază" in sign(admin_client, tech).data["items"][0]["text"]
    # verificările: procentul sub cel legal
    for code, params, text in (("idle", {"cause": "employer", "pay_pct": "80"}, "integral"),
                               ("idle", {"cause": "nobody", "pay_pct": "60"}, "2/3"),
                               ("tech_unemployment", {"pay_pct": "40"}, "50%")):
        bad = make_order(admin_client, code, [a_emp])
        set_params(admin_client, bad, {"date_from": "2026-03-20", "date_to": "2026-03-20", **params})
        resp = sign(admin_client, bad, ok=False)
        assert resp.status_code == 400 and text in str(resp.data)
    # pontajul: St / Șt cu orele planificate ale zilei
    tr1, ati = timesheet(org["tr1"]), timesheet(org["ati"])
    line = tr1.lines.get(employment=a)
    assert line.days["2"] == {"c": "St", "ph": 7.0} and line.totals["idle"] == {"St": 14.0}
    assert ati.lines.get(employment=d).days["9"]["c"] == "Șt"
    pay = calc()
    ia, ib, ic, idd = items(pay, a), items(pay, b), items(pay, c), items(pay, d)
    # A: 14 ore × 100 × 100 %; salariul — fără cele 14 ore: 15 400 × 140 / 154 = 14 000
    assert (ia["STATIONARE"].amount, ia["STATIONARE"].quantity, ia["SAL"].amount) == (D("1400"), D("14"), D("14000"))
    assert "din vina angajatorului" in ia["STATIONARE"].note and "ordinul" in ia["STATIONARE"].note
    # B: 2/3 — 14 × 100 × 66,6667 % = 933,33
    assert ib["STATIONARE"].amount == D("933.33")
    # C: salariul de 3 000 → 19,48 lei pe oră, 2/3 = 12,99 < salariul minim pe oră 6 300 / 169 = 37,28 → 37,28 × 14 = 521,89
    assert ic["STATIONARE"].amount == D("521.89") and "salariul minim pe oră" in ic["STATIONARE"].note
    # D: șomajul tehnic 14 × 100 × 50 %
    assert idd["SOMAJT"].amount == D("700") and "CM art. 80" in idd["SOMAJT"].note


def test_idle_skips_rest_days_and_worker_fault_is_unpaid(admin_client, org):  # noqa: F811
    e, job = person(org, "Ene", "Elena", salary="15400")
    order = make_order(admin_client, "idle", [e])
    # vineri 6 – luni 9 martie: sâmbăta, duminica 8 martie (sărbătoare) rămân repaus / sărbătoare
    set_params(admin_client, order, {"date_from": "2026-03-06", "date_to": "2026-03-09", "cause": "worker"})
    assert "nu se plătește" in sign(admin_client, order).data["items"][0]["text"]
    line = timesheet(org["tr1"]).lines.get(employment=job)
    assert [line.days[k]["c"] for k in ("6", "7", "8", "9")] == ["St", "R", "Sn", "St"]
    pay = items(calc(), job)
    assert "STATIONARE" not in pay and pay["SAL"].amount == D("14000")  # 2 zile × 7 ore lipsă din 154


# --- sporul pentru condiții vătămătoare -----------------------------------------------------------------------------------------
def test_harmful_allowance_from_subdivision_and_occupation(org):  # noqa: F811
    tr1, anest = org["tr1"], org["anest"]
    tr1.harmful, tr1.harmful_pct = True, D("10")
    tr1.save()
    anest.harmful, anest.harmful_pct = True, D("15")
    anest.save()
    _a, a = person(org, "Albu", "Andrei", salary="15400")
    _b, b = person(org, "Bivol", "Boris", salary="15400", occ="anest")  # tr1 10 % și funcția 15 % → 15 %
    _c, c = person(org, "Ceban", "Cezar", salary="15400", sub="ati")  # fără condiții
    n_emp, n = person(org, "Negru", "Nina", salary="15400")
    EmployeePayItem.objects.create(employee=n_emp, employment=n, pay_type=PayType.objects.get(code="NOCIV"), percent=D("5"),
                                   date_from=date(2026, 1, 1))
    pay = calc()
    # fără pontaj — orele planificate: 154 × 100 × 10 % = 1 540; 154 × 100 × 15 % = 2 310
    assert (items(pay, a)["VATAM"].amount, items(pay, a)["VATAM"].quantity) == (D("1540"), D("154"))
    assert items(pay, b)["VATAM"].amount == D("2310")
    assert "VATAM" not in items(pay, c)
    # sporul stabilit individual (NOCIV) îl înlocuiește pe cel din subdiviziune
    assert "VATAM" not in items(pay, n) and items(pay, n)["NOCIV"].amount == D("770")
    # cu pontajul: doar orele lucrate (2 zile de concediu neplătit scad 14 ore)
    from apps.leave.models import Absence as Abs

    Abs.objects.create(employee=_a, employment=a, kind="unpaid", date_from=date(2026, 3, 2), date_to=date(2026, 3, 3), days=2)
    timesheet(tr1)
    assert items(calc(), a)["VATAM"].amount == D("1400")


# --- evidența globală a timpului de muncă -------------------------------------------------------------------------------------
def test_summarized_accounting_overtime_at_period_end(org):  # noqa: F811
    ws = WorkSchedule.objects.create(name="6 × 8 h, evidența pe trimestru", kind="week", weekly_hours=D("40"),
                                     week=["8", "8", "8", "8", "8", "8", ""], holidays_off=False, accounting_months=3,
                                     accounting_start=date(2026, 1, 1))
    _e, job = person(org, "Sârbu", "Sergiu", salary="15400")
    JobSchedule.objects.create(employment=job, schedule=ws, date_from=date(2025, 1, 1))
    assert worktime.accounting_period(ws, 2026, 2) == (date(2026, 1, 1), date(2026, 3, 1))
    assert worktime.accounting_period(ws, 2026, 4) == (date(2026, 4, 1), date(2026, 6, 1))
    totals = {}
    for m in (1, 2, 3):
        totals[m] = timesheet(org["tr1"], 2026, m).lines.get(employment=job).totals
    # ianuarie, februarie: graficul peste normă, dar fără suplimentare pe lună
    for m in (1, 2):
        assert totals[m]["summarized"]["last"] is False and totals[m]["overtime_period"] == 0
        assert totals[m]["regular"] > totals[m]["norm"]
    s = totals[3]["summarized"]
    assert s["last"] is True and s["from"] == "01.2026" and s["to"] == "03.2026"
    expected = sum(totals[m]["regular"] for m in (1, 2)) + totals[3]["regular"] + totals[3]["overtime_period"] \
        - sum(totals[m]["norm"] for m in (1, 2, 3))
    assert totals[3]["overtime_period"] == pytest.approx(expected) and totals[3]["overtime_period"] > 0
    # salariul: în ianuarie întreg (graficul îndeplinit), fără suplimentare; în martie — suplimentarele perioadei
    jan = items(calc(2026, 1), job)
    assert jan["SAL"].amount == D("15400") and "SUPL" not in jan
    mar = items(calc(2026, 3), job)
    assert mar["SAL"].amount == D("15400") and mar["SUPL"].quantity == D(str(totals[3]["overtime_period"]))


# --- garanția la neîndeplinirea normei -----------------------------------------------------------------------------------------
def test_piece_guarantee_when_norm_not_met(admin_client, factory):  # noqa: F811
    grid(admin_client)
    op1 = operation(admin_client, "OP1")  # 12 lei / buc, 0,25 ore
    _e1, j1 = worker(factory)
    _e2, j2 = worker(factory, "Lungu", "Liviu")
    # fără ore, garanția nu se poate socoti: aprobarea se oprește
    bad = report(admin_client, [{"employment": j1.id, "operation": op1.id, "quantity": "50"}])
    admin_client.patch(f"/api/production/reports/{bad['id']}/", {"shortfall_cause": "nobody"}, format="json")
    assert approve(admin_client, bad, ok=False).status_code == 400
    admin_client.delete(f"/api/production/reports/{bad['id']}/")
    r1 = admin_client.post("/api/production/reports/", {"date": "2026-03-15", "kind": "individual", "shortfall_cause": "nobody",
                                                       "lines": [{"employment": j1.id, "operation": op1.id, "quantity": "50",
                                                                  "hours": "40"}]}, format="json")
    r2 = admin_client.post("/api/production/reports/", {"date": "2026-03-16", "kind": "individual", "shortfall_cause": "employer",
                                                       "lines": [{"employment": j2.id, "operation": op1.id, "quantity": "50",
                                                                  "hours": "40"}]}, format="json")
    assert r1.status_code == 201 and r2.data["shortfall_cause"] == "employer"
    approve(admin_client, r1.data)
    approve(admin_client, r2.data)
    pay = calc()
    p1, p2 = items(pay, j1), items(pay, j2)
    # fără vina părților: 40 ore × 40 × 2/3 = 1 066,67 − câștigul 600 = 466,67
    assert p1["ACORD"].amount == D("600") and p1["GARANT"].amount == D("466.67") and "CM art. 161" in p1["GARANT"].note
    # din vina angajatorului, fără istoric: 40 ore × tariful 40 = 1 600 − 600 = 1 000
    assert p2["GARANT"].amount == D("1000") and "fără istoric" in p2["GARANT"].note


# --- tichetele de masă ---------------------------------------------------------------------------------------------------------
def test_meal_vouchers_list_and_taxable_part(admin_client, org):  # noqa: F811
    # livrat cu 0 (nu se acordă): întreprinderea scrie valoarea din ordinul conducătorului
    assert PayConstant.objects.get(code="meal_voucher_value").value == 0
    PayConstant.objects.filter(code="meal_voucher_value").update(value=D("80"))
    _a, a = person(org, "Apostol", "Alina", salary="15400")
    ShiftType.objects.update_or_create(code="Z12", defaults={"name": "Zi 12", "hours": D("12"), "night_hours": D("0"), "start": time(8)})
    ShiftType.objects.update_or_create(code="N12", defaults={"name": "Noapte 12", "hours": D("12"), "night_hours": D("8"),
                                                             "start": time(20)})
    ws = WorkSchedule.objects.create(name="Ture 12 h", kind="cycle", weekly_hours=D("40"), cycle=["Z12", "N12", "", ""],
                                     cycle_start=date(2026, 3, 1))
    _s, s = person(org, "Stratan", "Silvia", salary="15400")
    JobSchedule.objects.create(employment=s, schedule=ws, date_from=date(2026, 1, 1))
    timesheet(org["tr1"])
    r = admin_client.post("/api/payroll/meal-vouchers/", {"date": "2026-04-03", "year": 2026, "month": 3}, format="json")
    assert r.status_code == 201, r.data
    doc = r.data
    lines = {ln["employment"]: ln for ln in doc["lines"]}
    assert D(doc["value"]) == D("80") and D(doc["cap"]) == D("70")
    # ziua lucrată = un tichet: 22 × 80 = 1 760, partea impozabilă 22 × 10 = 220
    assert (lines[a.id]["count"], D(lines[a.id]["amount"]), D(lines[a.id]["taxable"])) == (22, D("1760"), D("220"))
    # schimburile: 8 de zi × 12 h ÷ 8 + 8 de noapte × 12 h ÷ 7 = 12 + 13,71 = 25,71 → 26
    ls = lines[s.id]
    assert ls["shifts"] is True and (D(ls["day_hours"]), D(ls["night_hours"]), ls["count"]) == (D("96"), D("96"), 26)
    # numărul scris de mână; gol — înapoi la cel socotit
    m = admin_client.post(f"/api/payroll/meal-vouchers/{doc['id']}/set-count/", {"line": ls["id"], "count": 20}, format="json")
    assert m.status_code == 200 and {x["id"]: x for x in m.data["lines"]}[ls["id"]]["manual"] is True
    back = admin_client.post(f"/api/payroll/meal-vouchers/{doc['id']}/set-count/", {"line": ls["id"], "count": ""}, format="json")
    assert {x["id"]: x for x in back.data["lines"]}[ls["id"]]["count"] == 26
    assert admin_client.post(f"/api/payroll/meal-vouchers/{doc['id']}/approve/").status_code == 200
    # aprilie: partea impozabilă intră în calcul și se reține (tichetele sunt deja pe card)
    pay = calc(2026, 4)
    ia = items(pay, a)
    assert ia["TICHET"].amount == D("220") and ia["TICHETN"].amount == D("220") and ia["TICHET"].quantity == D("22")
    line = pay.lines.get(employment=a)
    assert line.deductions == D("220") and line.taxable == line.gross  # facilitate impozabilă
    # al doilea borderou pe aceeași lună lucrată nu se aprobă pentru aceiași oameni; valoarea sub minim e semnalată
    other = admin_client.post("/api/payroll/meal-vouchers/", {"date": "2026-04-10", "year": 2026, "month": 3, "value": "30"},
                              format="json").data
    assert any("sub minimul" in p for p in admin_client.get(f"/api/payroll/meal-vouchers/{other['id']}/").data["problems"])
    admin_client.patch(f"/api/payroll/meal-vouchers/{other['id']}/", {"value": "60"}, format="json")
    dup = admin_client.post(f"/api/payroll/meal-vouchers/{other['id']}/approve/")
    assert dup.status_code == 400 and "are deja tichetele" in str(dup.data)
    # aprobat — nu se mai modifică; tiparul
    assert admin_client.post(f"/api/payroll/meal-vouchers/{doc['id']}/fill/").status_code == 400
    assert admin_client.get(f"/api/payroll/meal-vouchers/{doc['id']}/print/").status_code == 200
