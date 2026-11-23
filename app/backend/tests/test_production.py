"""S5a — producția: grila tarifară, lucrările în acord cu normele lor, raportul de producție (individual și pe brigadă, cu
rebutul pe vinovați, CM art. 162), acordul progresiv pe trepte, legătura cu calculul salariului și importul din Excel.

Luna de probă: martie 2026 — 22 de zile lucrătoare, 7 ore pe zi (funcțiile de test au 35 h pe săptămână), norma 154 de ore.
Fără tabelă de pontaj, calculul ia norma întreagă (partea lucrată 100 %)."""
from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.payroll import engine
from apps.payroll.models import Payroll, PayType
from apps.production.models import Brigade, Operation, ProductionReport
from apps.staff import services as staff
from apps.staff.models import Employee

from .test_payroll import org, person  # noqa: F401 — fixtura și ajutoarele comune
from .test_staff import xlsx

D = Decimal


@pytest.fixture
def factory(org):  # noqa: F811
    """Modulul pornit și o grilă: categoria I — 40 lei/oră, a III-a — × 1,2 = 48 lei/oră, a IV-a — 55 lei/oră scris direct."""
    company = Company.get()
    company.production_enabled = True
    company.save(update_fields=["production_enabled"])
    return org


def grid(api, code="G1", base="40", date_from="2026-01-01", ranks=None):
    r = api.post("/api/production/tariff-grids/", {"code": code, "name": "Grila muncitorilor", "date_from": date_from,
                                                   "base_rate": base, "ranks": ranks if ranks is not None else [
                                                       {"rank": 1, "coefficient": "1"}, {"rank": 3, "coefficient": "1.2"},
                                                       {"rank": 4, "coefficient": "1.3", "rate": "55"}]}, format="json")
    assert r.status_code == 201, r.data
    return r.data


def operation(api, code, rate=None, *, norm_kind="time", norm="0.25", grid_code="G1", rank=3, progressive=False,
              date_from="2026-01-01", unit="buc"):
    r = api.post("/api/production/operations/", {"code": code, "name_ro": f"Lucrarea {code}", "unit": unit,
                                                 "progressive": progressive}, format="json")
    assert r.status_code == 201, r.data
    add_rate(api, r.data["id"], rate=rate, norm_kind=norm_kind, norm=norm, grid_code=grid_code, rank=rank, date_from=date_from)
    return Operation.objects.get(pk=r.data["id"])


def add_rate(api, op_id, *, rate=None, norm_kind="time", norm="0.25", grid_code="G1", rank=3, date_from="2026-01-01", ok=True):
    body = {"operation": op_id, "date_from": date_from, "norm_kind": norm_kind, "norm_value": norm, "piece_rate": rate,
            "grid_code": grid_code if rate is None else "", "rank": rank if rate is None else None}
    r = api.post("/api/production/operation-rates/", body, format="json")
    if ok:
        assert r.status_code == 201, r.data
    return r


def report(api, lines, *, kind="individual", brigade=None, members=None, day="2026-03-15", ok=True):
    body = {"date": day, "kind": kind, "brigade": brigade, "lines": lines, "members": members or []}
    r = api.post("/api/production/reports/", body, format="json")
    if ok:
        assert r.status_code == 201, r.data
    return r.data


def approve(api, doc, ok=True):
    r = api.post(f"/api/production/reports/{doc['id']}/approve/")
    if ok:
        assert r.status_code == 200, r.data
    return r


def march():
    doc = Payroll.objects.create(year=2026, month=3)
    engine.calculate(doc)
    return doc


def items(doc, job):
    return {i.pay_type.code: i for i in doc.lines.get(employment=job).items.select_related("pay_type")}


def worker(org, last="Rusu", first="Vasile", rate="40", **extra):  # noqa: F811
    return person(org, last, first, salary="0", pay_mode="piece", hourly_rate=D(rate), **extra)


# --- modulul, grila, tariful ----------------------------------------------------------------------------------------------
def test_module_off_by_default_and_switch(admin_client, org):  # noqa: F811
    assert Company.get().production_enabled is False
    assert admin_client.get("/api/production/operations/").status_code == 403
    assert admin_client.get("/api/public/branding/").data["production_enabled"] is False
    r = admin_client.patch("/api/company/", {"production_enabled": True}, format="json")
    assert r.status_code == 200 and r.data["production_enabled"] is True


def test_piece_rate_from_grid_norms_and_history(admin_client, factory):
    g = grid(admin_client)
    assert [(x["rank"], D(str(x["hourly"]))) for x in g["ranks"]] == [(1, D("40")), (3, D("48")), (4, D("55"))]
    # norma de timp: 48 lei/oră × 0,25 ore = 12 lei / buc; norma de producție: 48 lei/oră ÷ 8 buc pe oră = 6 lei / buc
    op1 = operation(admin_client, "OP1")
    op2 = operation(admin_client, "OP2", norm_kind="output", norm="8")
    op3 = operation(admin_client, "OP3", rate="2.3456", norm="0.1")
    rates = {o["code"]: o["current"] for o in admin_client.get("/api/production/operations/").data}
    assert D(str(rates["OP1"]["rate"])) == D("12") and "48 lei/oră × norma de timp 0,25 ore = 12 lei / bucăți" in rates["OP1"]["how"]
    assert D(str(rates["OP2"]["rate"])) == D("6") and "÷ 8 bucăți pe oră" in rates["OP2"]["how"]
    assert D(str(rates["OP3"]["rate"])) == D("2.3456")
    # categoria a IV-a are tariful scris direct
    op4 = operation(admin_client, "OP4", rank=4, norm="0.5")
    assert D(str(admin_client.get("/api/production/operations/").data[3]["current"]["rate"])) == D("27.5")
    # grila nouă din aprilie: martie rămâne pe cea veche
    grid(admin_client, base="50", date_from="2026-04-01", ranks=[{"rank": 3, "coefficient": "1.2"}])
    from apps.production import services

    assert services.price(op1, date(2026, 3, 31))["rate"] == D("12") and services.price(op1, date(2026, 4, 1))["rate"] == D("15")
    # aprilie nu are categoria a IV-a în grila nouă
    with pytest.raises(Exception, match="nu are categoria 4"):
        services.price(op4, date(2026, 4, 1))
    # o normă nouă a lucrării (din mai) — fără grilă, cu tarif direct
    add_rate(admin_client, op2.id, rate="7", norm="8", norm_kind="output", date_from="2026-05-01")
    assert services.price(op2, date(2026, 5, 2))["rate"] == D("7")
    # verificările: fără tarif și fără categorie; grila care nu există; aceeași dată de două ori; norma 0
    assert add_rate(admin_client, op3.id, rate=None, grid_code="", rank=None, date_from="2026-06-01", ok=False).status_code == 400
    assert add_rate(admin_client, op3.id, grid_code="NU", date_from="2026-06-01", ok=False).status_code == 400
    assert add_rate(admin_client, op3.id, rate="3", date_from="2026-01-01", ok=False).status_code == 400
    assert add_rate(admin_client, op3.id, rate="3", norm="0", date_from="2026-06-01", ok=False).status_code == 400


# --- raportul individual și calculul ---------------------------------------------------------------------------------------
def test_individual_report_defects_and_payroll(admin_client, factory):
    grid(admin_client)
    op1 = operation(admin_client, "OP1")  # 12 lei / buc, 0,25 ore
    op2 = operation(admin_client, "OP2", norm_kind="output", norm="8")  # 6 lei / buc, 0,125 ore
    _e, job = worker(factory)
    doc = report(admin_client, [
        {"employment": job.id, "operation": op1.id, "quantity": "500", "defect_nofault": "10", "defect_partial": "20",
         "defect_partial_pct": "50", "defect_worker": "5", "hours": "120"},
        {"employment": job.id, "operation": op2.id, "quantity": "200", "hours": "25"},
    ])
    # OP1: (500 + 10) × 12 + 20 × 12 × 50 % = 6 240; orele normate 510 × 0,25 = 127,5; rebutul din vină (5) — neplătit
    l1, l2 = doc["lines"]
    assert (D(l1["amount"]), D(l1["normed_hours"]), D(l1["rate"])) == (D("6240"), D("127.5"), D("12"))
    assert "rebut din vina lucrătorului 5 — neplătit" in l1["how"] and "rebut parțial 20 × 12 × 50 %" in l1["how"]
    assert (D(l2["amount"]), D(l2["normed_hours"])) == (D("1200"), D("25"))
    assert doc["totals"] == {"amount": 7440.0, "normed_hours": 152.5, "hours": 145.0, "lines": 2} and doc["problems"] == []
    # ciorna nu intră în calcul
    assert "ACORD" not in items(march(), job)
    Payroll.objects.all().delete()
    approve(admin_client, doc)
    calc = items(march(), job)
    # în acord: fără salariul de funcție; suma lucrărilor, cu orele normate ca și cantitate; îndeplinirea normei 152,5 / 145
    assert "SAL" not in calc and "MINIM" not in calc
    assert (calc["ACORD"].amount, calc["ACORD"].quantity) == (D("7440"), D("152.5"))
    assert f"{doc['number']}" in calc["ACORD"].note and "îndeplinirea normei 105,17 %" in calc["ACORD"].note
    assert "orele din rapoarte" in calc["ACORD"].note
    # aprobatul nu se mai modifică; anularea aprobării îl scoate din calcul
    assert admin_client.patch(f"/api/production/reports/{doc['id']}/", {"note": "x"}, format="json").status_code == 400
    assert admin_client.post(f"/api/production/reports/{doc['id']}/unapprove/").status_code == 200
    Payroll.objects.all().delete()
    assert "ACORD" not in items(march(), job)


def test_approved_report_keeps_its_rates_and_closed_month(admin_client, factory):
    grid(admin_client)
    op1 = operation(admin_client, "OP1")
    _e, job = worker(factory)
    doc = report(admin_client, [{"employment": job.id, "operation": op1.id, "quantity": "100", "hours": "20"}])
    approve(admin_client, doc)
    # tariful lucrării se schimbă din aceeași lună: raportul aprobat rămâne cu tariful fixat la aprobare
    r = admin_client.patch(f"/api/production/operation-rates/{op1.rates.get().id}/", {"piece_rate": "20", "grid_code": "", "rank": None},
                           format="json")
    assert r.status_code == 200, r.data
    pay = march()
    assert items(pay, job)["ACORD"].amount == D("1200")
    # cu calculul lunii aprobat, raportul nu se mai anulează (și nu se aprobă altul pentru același angajat)
    pay.status = "approved"
    pay.save(update_fields=["status"])
    blocked = admin_client.post(f"/api/production/reports/{doc['id']}/unapprove/")
    assert blocked.status_code == 400 and "redeschideți-l" in str(blocked.data)
    other = report(admin_client, [{"employment": job.id, "operation": op1.id, "quantity": "10", "hours": "2"}])
    assert approve(admin_client, other, ok=False).status_code == 400


def test_approval_checks(admin_client, factory):
    grid(admin_client)
    op1 = operation(admin_client, "OP1")
    prog = operation(admin_client, "PRG", rate="5", norm="0.1", progressive=True)
    bare = Operation.objects.create(code="FARA", name_ro="Fără normă")
    _e, job = worker(factory)
    # rebutul parțial fără procent; lucrarea fără normă; rândul fără angajat; progresivul fără ore
    doc = report(admin_client, [
        {"employment": job.id, "operation": op1.id, "quantity": "10", "defect_partial": "2"},
        {"employment": job.id, "operation": bare.id, "quantity": "1"},
        {"employment": None, "operation": op1.id, "quantity": "1"},
        {"employment": job.id, "operation": prog.id, "quantity": "5"},
    ])
    text = " ".join(doc["problems"])
    assert "procentul de plată" in text and "FARA nu are normă" in text and "alegeți angajatul" in text and "cere orele lucrate" in text
    r = approve(admin_client, doc, ok=False)
    assert r.status_code == 400 and ProductionReport.objects.get(pk=doc["id"]).status == "draft"
    # cantitățile negative — respinse de la salvare
    bad = report(admin_client, [{"employment": job.id, "operation": op1.id, "quantity": "-1"}], ok=False)
    assert "nu pot fi negative" in str(bad)


def test_minimum_wage_top_up_in_piece(admin_client, factory):
    grid(admin_client)
    op1 = operation(admin_client, "OP1")  # 12 lei / buc
    _e, job = worker(factory)
    approve(admin_client, report(admin_client, [{"employment": job.id, "operation": op1.id, "quantity": "300", "hours": "154"}]))
    calc = items(march(), job)
    # 300 × 12 = 3 600 < salariul minim 6 300 × norma 1 × 100 % lucrat → completarea 2 700 (CM art. 131)
    assert calc["ACORD"].amount == D("3600") and calc["MINIM"].amount == D("2700")


# --- acordul progresiv -------------------------------------------------------------------------------------------------------
def test_progressive_piece_rate_steps(admin_client, factory):
    acordp = PayType.objects.get(code="ACORDP")
    assert acordp.scale == []  # treptele le scrie întreprinderea (contractul colectiv)
    r = admin_client.patch(f"/api/payroll/types/{acordp.id}/", {"scale": [{"from": 100, "pct": 50}, {"from": 110, "pct": 100}]},
                           format="json")
    assert r.status_code == 200, r.data
    prog = operation(admin_client, "PRG", rate="50", norm="1", progressive=True)  # 50 lei / buc, 1 oră
    _e, job = worker(factory)
    approve(admin_client, report(admin_client, [{"employment": job.id, "operation": prog.id, "quantity": "150", "hours": "120"}]))
    calc = items(march(), job)
    # îndeplinirea 150 / 120 = 125 %: (110 − 100) / 125 × 7 500 × 50 % + (125 − 110) / 125 × 7 500 × 100 % = 300 + 900
    assert calc["ACORD"].amount == D("7500") and calc["ACORDP"].amount == D("1200")
    assert "peste 100 %: 10 p.p. × 50 %; peste 110 %: 15 p.p. × 100 %" in calc["ACORDP"].note
    # sub prima treaptă — fără spor
    Payroll.objects.all().delete()
    ProductionReport.objects.all().update(status="draft")
    approve(admin_client, report(admin_client, [{"employment": job.id, "operation": prog.id, "quantity": "100", "hours": "120"}],
                                 day="2026-03-20"))
    assert "ACORDP" not in items(march(), job)


def test_formula_variables_for_piece_work(admin_client, factory):
    op = operation(admin_client, "OPX", rate="10", norm="0.5")
    PayType.objects.create(code="PRNORMA", name_ro="Premiu pentru îndeplinirea normei", category="accrual", formula="expr",
                           applies_to="all", expression="daca(IndeplinireNorma >= 105; [ACORD] * 10 / 100; 0)")
    _e, job = worker(factory)
    # 330 × 0,5 = 165 ore normate / 154 ore din pontaj (rândul fără ore) = 107,14 %
    approve(admin_client, report(admin_client, [{"employment": job.id, "operation": op.id, "quantity": "330"}]))
    calc = items(march(), job)
    assert calc["ACORD"].amount == D("3300") and "orele lucrate din pontaj" in calc["ACORD"].note
    assert calc["PRNORMA"].amount == D("330")


# --- brigada -----------------------------------------------------------------------------------------------------------------
def brigade(api, members, distribution="hours", code="B1"):
    r = api.post("/api/production/brigades/", {"code": code, "name": f"Brigada {code}", "distribution": distribution,
                                               "members": members}, format="json")
    assert r.status_code == 201, r.data
    return r.data


def test_brigade_split_by_hours_and_coefficient(admin_client, factory):
    op = operation(admin_client, "ASM", rate="10", norm="0.5")  # 10 lei / buc, 0,5 ore
    _a, ja = worker(factory, "Ababii", "Ana")
    _b, jb = worker(factory, "Botnari", "Ion")
    _c, jc = worker(factory, "Ciobanu", "Maria")
    b = brigade(admin_client, [{"employment": ja.id, "coefficient": "1.2", "date_from": "2026-01-01"},
                               {"employment": jb.id, "coefficient": "1", "date_from": "2026-01-01"},
                               {"employment": jc.id, "coefficient": "1", "date_from": "2026-01-01"}])
    doc = report(admin_client, [{"operation": op.id, "quantity": "1000"}], kind="brigade", brigade=b["id"])
    # membrii din componența brigăzii (coeficienții), apoi orele
    filled = admin_client.post(f"/api/production/reports/{doc['id']}/fill-members/").data
    assert [(m["employee_name"], D(m["coefficient"])) for m in filled["members"]] == [
        ("Ababii Ana", D("1.2")), ("Botnari Ion", D("1")), ("Ciobanu Maria", D("1"))]
    members = [{"id": m["id"], "employment": m["employment"], "hours": h, "coefficient": m["coefficient"]}
               for m, h in zip(filled["members"], ("160", "160", "80"))]
    doc = admin_client.patch(f"/api/production/reports/{doc['id']}/", {"members": members}, format="json").data
    # ponderile 192 / 160 / 80 din 432: 10 000 → 4 444,44 (+0,01 din rotunjire, la ponderea cea mai mare) / 3 703,70 / 1 851,85
    shares = {m["employee_name"]: (D(m["amount"]), D(m["normed_hours"])) for m in doc["members"]}
    assert shares == {"Ababii Ana": (D("4444.45"), D("222.22")), "Botnari Ion": (D("3703.70"), D("185.19")),
                      "Ciobanu Maria": (D("1851.85"), D("92.59"))}
    assert sum(v[0] for v in shares.values()) == D("10000")
    approve(admin_client, doc)
    calc = march()
    assert items(calc, ja)["ACORD"].amount == D("4444.45") and "(brigada)" in items(calc, ja)["ACORD"].note
    assert items(calc, jc)["ACORD"].amount == D("1851.85")


def test_brigade_split_by_tariff(admin_client, factory):
    op = operation(admin_client, "ASM", rate="10", norm="0.5")
    _a, ja = worker(factory, "Ababii", "Ana", rate="50")
    _b, jb = worker(factory, "Botnari", "Ion", rate="40")
    _c, jc = worker(factory, "Ciobanu", "Maria", rate="40")
    b = brigade(admin_client, [], distribution="tariff")
    doc = report(admin_client, [{"operation": op.id, "quantity": "1000"}], kind="brigade", brigade=b["id"], members=[
        {"employment": ja.id, "hours": "160", "coefficient": "1.2"}, {"employment": jb.id, "hours": "160", "coefficient": "1"},
        {"employment": jc.id, "hours": "80", "coefficient": "1"}])
    # ponderile 160 × 1,2 × 50 = 9 600; 160 × 40 = 6 400; 80 × 40 = 3 200 — din 19 200
    assert [D(m["amount"]) for m in doc["members"]] == [D("5000"), D("3333.33"), D("1666.67")]
    assert [D(m["hourly"]) for m in doc["members"]] == [D("50"), D("40"), D("40")]
    # raportul pe brigadă fără membri / cu același membru de două ori
    empty = report(admin_client, [{"operation": op.id, "quantity": "1"}], kind="brigade", brigade=b["id"])
    assert any("are nevoie de membri" in p for p in empty["problems"])
    twice = report(admin_client, [{"operation": op.id, "quantity": "1"}], kind="brigade", brigade=b["id"], ok=False, members=[
        {"employment": ja.id, "hours": "1", "coefficient": "1"}, {"employment": ja.id, "hours": "2", "coefficient": "1"}])
    assert "de două ori" in str(twice)
    assert Brigade.objects.count() == 1


# --- importul din Excel, tiparul ---------------------------------------------------------------------------------------------
def test_excel_import_lines_and_members(admin_client, factory):
    op = operation(admin_client, "OP1", rate="12", norm="0.25")
    e1, j1 = worker(factory, "Ababii", "Ana")
    e2, j2 = worker(factory, "Botnari", "Ion")
    doc = report(admin_client, [])
    url = f"/api/production/reports/{doc['id']}/import/lines/"
    assert admin_client.get(url + "template/").status_code == 200
    head = ["Nr. tabel", "Raportul de muncă", "Lucrarea (codul)", "Cantitatea bună", "Rebut fără vina lucrătorului",
            "Rebut parțial din vina lucrătorului", "Plata rebutului parțial (%)", "Rebut total din vina lucrătorului", "Ore lucrate"]
    bad = admin_client.post(url, {"file": xlsx([head, [e1.tab_number, "", "NIMIC", 5], ["", "", "OP1", 5],
                                                 [e2.tab_number, "", "OP1", 5, 0, 2]]), "dry_run": "1"}, format="multipart").data
    errors = {e["row"]: e["error"] for e in bad["errors"]}
    assert "„NIMIC” nu există" in errors[2] and "„Nr. tabel” este obligatoriu" in errors[3] and "procentul de plată" in errors[4]
    rows = [head, [e1.tab_number, "", "OP1", 100, 0, 0, None, 0, 25], [e2.tab_number, "", "op1", 50, 2, 4, 50, 1, 13]]
    trial = admin_client.post(url, {"file": xlsx(rows), "dry_run": "1"}, format="multipart").data
    assert trial["ok"] and trial["created"] == 2 and not ProductionReport.objects.get(pk=doc["id"]).lines.exists()
    done = admin_client.post(url, {"file": xlsx(rows), "dry_run": "0"}, format="multipart").data
    assert done["saved"], done
    lines = list(ProductionReport.objects.get(pk=doc["id"]).lines.order_by("sort"))
    # 100 × 12; (50 + 2) × 12 + 4 × 12 × 50 %
    assert [(ln.employment_id, ln.amount) for ln in lines] == [(j1.id, D("1200")), (j2.id, D("648"))]
    # membrii — doar în raportul pe brigadă
    b = brigade(admin_client, [{"employment": j1.id, "coefficient": "1.5", "date_from": "2026-01-01"}])
    br = report(admin_client, [{"operation": op.id, "quantity": "100"}], kind="brigade", brigade=b["id"])
    assert admin_client.post(f"/api/production/reports/{doc['id']}/import/members/",
                             {"file": xlsx([["Nr. tabel", "Ore lucrate"], [e1.tab_number, 10]]), "dry_run": "1"},
                             format="multipart").status_code == 400
    mdone = admin_client.post(f"/api/production/reports/{br['id']}/import/members/",
                              {"file": xlsx([["Nr. tabel", "Ore lucrate", "Coeficientul de participare (KTU)"], [e1.tab_number, 100, None],
                                             [e2.tab_number, 50, 1]]), "dry_run": "0"}, format="multipart").data
    assert mdone["saved"], mdone
    members = {m.employment_id: (m.hours, m.coefficient, m.amount) for m in ProductionReport.objects.get(pk=br["id"]).members.all()}
    # coeficientul gol — cel din brigadă (1,5); ponderile 150 / 50: 1 200 → 900 / 300
    assert members == {j1.id: (D("100"), D("1.5"), D("900")), j2.id: (D("50"), D("1"), D("300"))}
    # tiparul
    assert admin_client.get(f"/api/production/reports/{br['id']}/print/").status_code == 200


def test_piece_pay_mode_needs_category_rate(factory):
    e = Employee.objects.create(tab_number=staff.next_tab_number(), last_name="Fără", first_name="Tarif")
    from rest_framework.exceptions import ValidationError

    with pytest.raises(ValidationError, match="tariful orar al categoriei"):
        staff.hire(e, subdivision=factory["tr1"], occupation=factory["doctor"], rate=D("1"), base_salary=D("0"),
                   date_from=date(2026, 1, 1), pay_mode="piece")


def test_overtime_and_holiday_in_piece_work(admin_client, factory):
    """În acord: suplimentarele — doar sporul (+50 % primele 2 ore, +100 % următoarele) din tariful orar al categoriei (CM art.
    157); sărbătoarea — încă o dată câștigul în acord pe oră (dublul tarifelor în acord, CM art. 158)."""
    from apps.worktime import services as worktime
    from apps.worktime.models import Timesheet

    op = operation(admin_client, "OPX", rate="10", norm="0.5")
    emp, job = worker(factory)  # tariful categoriei 40 lei/oră
    ts = Timesheet.objects.create(subdivision=factory["tr1"], year=2026, month=3)
    worktime.fill_timesheet(ts)
    line = ts.lines.get(employment=job)
    worktime.set_cell(line, 2, "", "10")  # 2 martie: 7 ore + 3 suplimentare (2 + 1)
    worktime.set_cell(line, 8, "", "7")  # 8 martie: sărbătoare, peste normă
    approve(admin_client, report(admin_client, [{"employment": job.id, "operation": op.id, "quantity": "400"}]))
    calc = items(march(), job)
    assert calc["ACORD"].amount == D("4000") and "SAL" not in calc
    assert calc["SUPL"].amount == D("80") and "2 ore × 50 % + 1 ore × 100 %" in calc["SUPL"].note  # 40 × (2 × 0,5 + 1 × 1)
    # câștigul în acord pe oră 4 000 / 154 (orele din pontaj — rândul n-are ore) × 7 ore × 100 %
    assert calc["SARB"].amount == D("181.82") and "dublul tarifelor în acord" in calc["SARB"].note


def test_default_roles_and_module_switch_for_users(make_user, client_for, factory):
    """Rolurile livrate primesc drepturile producției; cu modulul oprit nimeni nu le are (nici API-ul nu răspunde)."""
    acc = client_for(make_user("contabil", ["accountant"]))
    head = make_user("maistru", ["department_head"])
    assert acc.get("/api/production/reports/").status_code == 200
    assert acc.post("/api/production/operations/", {"code": "X1", "name_ro": "X", "unit": "buc"}, format="json").status_code == 201
    assert {"production.view", "production.create", "production.edit"} <= head.permission_codes()
    assert "production.approve" not in head.permission_codes() and head.data_scope("production") == "own"
    company = Company.get()
    company.production_enabled = False
    company.save(update_fields=["production_enabled"])
    other = client_for(make_user("contabil2", ["accountant"]))
    assert other.get("/api/production/reports/").status_code == 403
