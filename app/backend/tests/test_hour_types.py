"""S4b: tipurile de ore, remunerarea pe funcție (tarifele pe tipuri de ore cu orele garantate), pontajul cu orele pe tipuri,
importul din Excel, variabilele `Ore.COD` în formule, cumularea funcțiilor (CM art. 156) separat de cumul.

Luna de probă: martie 2026 — 22 de zile lucrătoare (2–6, 9–13, 16–20, 23–27, 30–31; 8 martie e duminică), 7 ore pe zi
(funcțiile de test au 35 h pe săptămână), norma 154 de ore."""
from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.leave.models import Absence
from apps.payroll import engine
from apps.payroll.models import Payroll, PayType
from apps.staff import services as staff
from apps.staff.models import FunctionCombination
from apps.worktime import services as worktime
from apps.worktime.models import HourType, JobHourRate, OccupationHourRate, Timesheet

from .test_orders import cancel, emp, make_order, set_params, sign
from .test_payroll import org, person  # noqa: F401 — fixtura și ajutoarele comune
from .test_staff import xlsx

D = Decimal


def hour_type(api, code="ZBOR", entry="month", **extra):
    r = api.post("/api/worktime/hour-types/", {"code": code, "name_ro": f"Ore {code.lower()}", "group": "flight",
                                               "work_time": "within", "entry": entry, **extra}, format="json")
    assert r.status_code == 201, r.data
    return HourType.objects.get(code=code)


def add_rate(api, job, ht, rate, guaranteed=None, date_from="2026-01-01", ok=True, **extra):
    r = api.post("/api/worktime/job-hour-rates/", {"employment": job.id, "hour_type": ht.id, "rate": rate,
                                                   "guaranteed_hours": guaranteed, "date_from": date_from, **extra}, format="json")
    if ok:
        assert r.status_code == 201, r.data
    return r


def timesheet(org, sub="tr1"):  # noqa: F811
    ts = Timesheet.objects.create(subdivision=org[sub], year=2026, month=3)
    worktime.fill_timesheet(ts)
    return ts


def set_hours(api, ts, job, code, **values):
    line = ts.lines.get(employment=job)
    r = api.post(f"/api/worktime/timesheets/{ts.id}/set-hours/", {"line": line.id, "code": code, **values}, format="json")
    assert r.status_code == 200, r.data
    return r.data


def march():
    doc = Payroll.objects.create(year=2026, month=3)
    engine.calculate(doc)
    return doc


def rows(doc, job, code):
    return list(doc.lines.get(employment=job).items.filter(pay_type__code=code).order_by("id"))


# --- garanția: un minim plătit ---------------------------------------------------------------------------------------------
def test_guaranteed_hours_are_a_paid_minimum(admin_client, org):  # noqa: F811
    _pilot, job = person(org, "Lungu", "Petru", pay_mode="mixed")
    zbor = hour_type(admin_client)
    add_rate(admin_client, job, zbor, "300", "50")
    ts = timesheet(org)
    row = set_hours(admin_client, ts, job, "ZBOR", month=34)
    s = row["hour_types"]["ZBOR"]
    assert (s["hours"], s["guaranteed"], s["available_days"], s["total_days"], s["paid"]) == (34, 50, 22, 22, 50)
    doc = march()
    [ore] = rows(doc, job, "ORE")
    # 50 garantate × 300 lei; salariul lunar rămâne (modalitatea „mixt”)
    assert (ore.quantity, ore.base, ore.amount) == (D("50"), D("300"), D("15000"))
    assert "garantat 50; efectiv 34 → plătit 50 × 300 lei = 15 000 lei" in ore.note
    assert rows(doc, job, "SAL")[0].amount == D("14660")
    set_hours(admin_client, ts, job, "ZBOR", month=54)
    doc.delete()
    [ore] = rows(march(), job, "ORE")
    assert (ore.quantity, ore.amount) == (D("54"), D("16200"))  # peste garanție — orele efective


def test_guarantee_reduced_for_hire_in_the_month(admin_client, org):  # noqa: F811
    zbor = hour_type(admin_client)
    _p, job = person(org, "Lungu", "Petru", pay_mode="hour_types", salary="0", hired=date(2026, 3, 11))
    add_rate(admin_client, job, zbor, "300", "50", date_from="2026-03-11")
    ts = timesheet(org)
    set_hours(admin_client, ts, job, "ZBOR", month=20)
    doc = march()
    [ore] = rows(doc, job, "ORE")
    # angajat la 11: 15 zile lucrătoare din 22 (11–13, 16–20, 23–27, 30–31) → 50 × 15 / 22 = 34,09 > 20 efective
    assert (ore.quantity, ore.amount) == (D("34.09"), D("10227"))
    assert "garantat 50 × 15 / 22 zile disponibile (7 zile fără raport / fără tarif) = 34,09; efectiv 20 → plătit 34,09" in ore.note
    assert not rows(doc, job, "SAL")  # „pe tipuri de ore”: fără salariu lunar


def test_guarantee_reduced_by_leave_not_by_travel(admin_client, org):  # noqa: F811
    zbor = hour_type(admin_client)
    pilot, job = person(org, "Lungu", "Petru", pay_mode="mixed")
    add_rate(admin_client, job, zbor, "300", "50")
    Absence.objects.create(employee=pilot, employment=job, kind="annual", date_from=date(2026, 3, 16), date_to=date(2026, 3, 20), days=5)
    Absence.objects.create(employee=pilot, employment=job, kind="travel", date_from=date(2026, 3, 23), date_to=date(2026, 3, 27), days=5)
    ts = timesheet(org)
    row = set_hours(admin_client, ts, job, "ZBOR", month=30)
    assert row["hour_types"]["ZBOR"]["available_days"] == 17  # concediul (5 zile) reduce, deplasarea nu
    [ore] = rows(march(), job, "ORE")
    # 50 × 17 / 22 = 38,64 > 30 → 38,64 × 300 = 11 592
    assert (ore.quantity, ore.amount) == (D("38.64"), D("11592"))
    assert "50 × 17 / 22 zile disponibile (5 zile C) = 38,64" in ore.note
    # setarea: fără concediul de odihnă în listă — garanția întreagă
    r = admin_client.put("/api/worktime/settings/", {"guarantee_absences": {"kinds": ["sick", "unpaid"], "suspension": True}}, format="json")
    assert r.status_code == 200, r.data
    assert admin_client.put("/api/worktime/settings/", {"guarantee_absences": {"kinds": ["travel"]}}, format="json").status_code == 400
    Payroll.objects.all().delete()
    [ore] = rows(march(), job, "ORE")
    assert ore.quantity == D("50")


def test_two_hour_types_with_different_rates_and_rate_change(admin_client, org):  # noqa: F811
    zbor = hour_type(admin_client)
    instr = HourType.objects.get(code="INSTR")  # livrat: pe zile
    _p, job = person(org, "Lungu", "Petru", pay_mode="mixed")
    add_rate(admin_client, job, zbor, "300", "50")
    add_rate(admin_client, job, instr, "150", date_to="2026-03-15")
    add_rate(admin_client, job, instr, "180", date_from="2026-03-16")
    # două rânduri în vigoare în aceeași zi — nu
    assert add_rate(admin_client, job, instr, "200", date_from="2026-03-20", ok=False).status_code == 400
    ts = timesheet(org)
    set_hours(admin_client, ts, job, "ZBOR", month=60)
    set_hours(admin_client, ts, job, "INSTR", days={"3": 2, "4": 3, "17": 4})
    doc = march()
    ore = rows(doc, job, "ORE")
    by_note = {i.note.split(":")[0]: i for i in ore}
    assert by_note["ZBOR"].amount == D("18000")  # 60 × 300
    # INSTR pe zile: 5 ore până la 15.03 × 150 + 4 ore din 16.03 × 180 = 750 + 720
    assert by_note["INSTR"].amount == D("1470") and by_note["INSTR"].quantity == D("9")
    assert "01.03–15.03: efectiv 5 × 150 lei = 750 lei; 16.03–31.03: efectiv 4 × 180 lei = 720 lei" in by_note["INSTR"].note
    # ziua pe un tip „doar total pe lună” — nu
    line = ts.lines.get(employment=job)
    r = admin_client.post(f"/api/worktime/timesheets/{ts.id}/set-hours/", {"line": line.id, "code": "ZBOR", "days": {"3": 2}}, format="json")
    assert r.status_code == 400
    # coloanele pontajului: tipurile cu tarif și cele scrise
    report = admin_client.get(f"/api/worktime/timesheets/{ts.id}/report/").data
    assert [c["code"] for c in report["hour_types"]] == ["ZBOR", "INSTR"]  # după ordinea din clasificator (ZBOR — 0, INSTR — 10)
    # tiparul și exportul au coloanele tipurilor de ore
    html = admin_client.get(f"/api/worktime/timesheets/{ts.id}/print/").content.decode()
    assert ">ZBOR</th>" in html and ">INSTR</th>" in html and ">60</td>" in html and "salariu + tarife" in html
    from io import BytesIO

    from openpyxl import load_workbook

    exp = admin_client.get("/api/worktime/timesheets/export/", {"year": 2026, "month": 3})
    assert exp.status_code == 200, exp.content[:3000]
    wb = load_workbook(BytesIO(exp.content))
    head = [c.value for c in wb["Pontaj"][1]]
    assert "ZBOR — Ore zbor (de plată)" in head and "INSTR — Ore de instruire (efective)" in head
    values = dict(zip(head, [c.value for c in wb["Pontaj"][2]]))
    assert (values["ZBOR — Ore zbor (efective)"], values["ZBOR — Ore zbor (garantate)"], values["INSTR — Ore de instruire (de plată)"]) == (60, 50, 9)
    assert [c.value for c in wb["Ore pe tipuri"][2]][3:6] == ["INSTR", 9, None]
    # recompletarea tabelei păstrează orele pe tipuri
    worktime.fill_timesheet(ts)
    assert ts.lines.get(employment=job).typed_hours["INSTR"]["days"] == {"3": 2.0, "4": 3.0, "17": 4.0}


def test_rates_need_a_pay_mode_that_pays_them(admin_client, org):  # noqa: F811
    zbor = hour_type(admin_client)
    _p, job = person(org, "Lungu", "Petru")  # salariu lunar
    r = add_rate(admin_client, job, zbor, "300", "50", ok=False)
    assert r.status_code == 400 and "„Pe tipuri de ore” sau „Mixt”" in str(r.data)
    staff.change(job, date(2026, 1, 1), pay_mode="mixed")
    add_rate(admin_client, job, zbor, "300", "50")
    r = admin_client.post(f"/api/staff/employments/{job.id}/change/", {"date": "2026-04-01", "pay_mode": "salary"}, format="json")
    assert r.status_code == 400 and "ZBOR" in str(r.data)


# --- importul din Excel --------------------------------------------------------------------------------------------------
def test_excel_import_of_typed_hours(admin_client, org):  # noqa: F811
    hour_type(admin_client)  # ZBOR — doar total pe lună
    pilot, job = person(org, "Lungu", "Petru")
    ana, ana_main = person(org, "Rusu", "Ana", occ="nurse")
    ana_cumul = staff.hire(ana, kind="internal", subdivision=org["tr1"], occupation=org["anest"], rate=D("0.25"),
                           base_salary=D("15200"), date_from=date(2025, 1, 1))
    ts = timesheet(org)
    url = f"/api/worktime/timesheets/{ts.id}/import/hours/"
    assert admin_client.get(url + "template/").status_code == 200
    head = ["Nr. tabel", "Raportul de muncă", "Tipul de ore (codul)", "Ziua (gol — total pe lună)", "Ore"]
    bad = admin_client.post(url, {"file": xlsx([head, [pilot.tab_number, "", "ZBOR", 5, 3], [ana.tab_number, "", "INSTR", 2, 1],
                                                [pilot.tab_number, "", "NIMIC", None, 3]]), "dry_run": "1"}, format="multipart").data
    errors = {e["row"]: e["error"] for e in bad["errors"]}
    assert "doar ca total pe lună" in errors[2] and "completați „Raportul de muncă”" in errors[3] and "„NIMIC” nu există" in errors[4]
    rows_ = [head, [pilot.tab_number, "", "ZBOR", None, 41.5], [pilot.tab_number, "", "INSTR", 3, 2],
             [pilot.tab_number, "", "INSTR", 4, 1.5], [ana.tab_number, "Cumul intern", "EXAM", 10, 2],
             [ana.tab_number, "Asistent medical de secție", "INSTR", None, 6]]
    trial = admin_client.post(url, {"file": xlsx(rows_), "dry_run": "1"}, format="multipart").data
    assert trial["ok"] and trial["created"] == 5 and not trial["saved"]
    assert not ts.lines.get(employment=job).typed_hours  # încercarea nu scrie nimic
    done = admin_client.post(url, {"file": xlsx(rows_), "dry_run": "0"}, format="multipart").data
    assert done["saved"], done
    assert ts.lines.get(employment=job).typed_hours == {"ZBOR": {"days": {}, "month": 41.5},
                                                        "INSTR": {"days": {"3": 2.0, "4": 1.5}, "month": None}}
    assert ts.lines.get(employment=ana_cumul).typed_hours == {"EXAM": {"days": {"10": 2.0}, "month": None}}
    assert ts.lines.get(employment=ana_main).typed_hours == {"INSTR": {"days": {}, "month": 6.0}}
    # în același fișier zilele și totalul aceluiași tip — nu
    mixed = admin_client.post(url, {"file": xlsx([head, [pilot.tab_number, "", "INSTR", 3, 2], [pilot.tab_number, "", "INSTR", None, 5]]),
                                    "dry_run": "1"}, format="multipart").data
    assert mixed["errors"][0]["row"] == 3


# --- formula ---------------------------------------------------------------------------------------------------------------
def test_formula_with_typed_hours_variables(admin_client, org):  # noqa: F811
    _p, job = person(org, "Lungu", "Petru", pay_mode="mixed")
    zbor = hour_type(admin_client)
    add_rate(admin_client, job, zbor, "300", "50")
    bad = admin_client.post("/api/payroll/types/", {"code": "INSTRS", "name_ro": "x", "formula": "expr", "expression": "Ore.NIMIC * 2"},
                            format="json")
    assert bad.status_code == 400 and "Tipul de ore „NIMIC” nu există" in str(bad.data["expression"])
    check = admin_client.post("/api/payroll/types/check/", {"expression": "ore.instr * 10"}, format="json").data
    assert check["ok"] and check["variables"] == ["Ore.INSTR"]
    r = admin_client.post("/api/payroll/types/", {
        "code": "INSTRS", "name_ro": "Spor pentru instruire", "formula": "expr", "applies_to": "all",
        "expression": "Ore.INSTR * 10 + (OrePlatite.ZBOR - Ore.ZBOR) * 0 + Garantat.ZBOR * 0 + Tarif.ZBOR * 0"}, format="json")
    assert r.status_code == 201, r.data
    ts = timesheet(org)
    set_hours(admin_client, ts, job, "INSTR", days={"5": 2, "6": 3})
    set_hours(admin_client, ts, job, "ZBOR", month=40)
    [spor] = rows(march(), job, "INSTRS")
    assert spor.amount == D("50")  # 5 ore × 10
    assert "Ore.INSTR 5 × 10" in spor.note and "OrePlatite.ZBOR 50" in spor.note and "Garantat.ZBOR 50" in spor.note
    catalog = admin_client.get("/api/payroll/types/variables/").data
    assert [v["name"] for v in catalog["hour_variables"]] == ["Ore", "OrePlatite", "Garantat", "Tarif"]
    assert {"INSTR", "EXAM", "ZBOR"} <= {h["code"] for h in catalog["hour_types"]}


# --- cumulul ≠ cumularea --------------------------------------------------------------------------------------------------
def test_combination_30_pct_versus_internal_cumul_with_own_pay(admin_client, org):  # noqa: F811
    ana, main = person(org, "Rusu", "Ana", occ="nurse", salary="9200")
    # cumul intern (raport separat, CIM, normă, pontaj): examinator cu tarif orar
    cumul = staff.hire(ana, kind="internal", subdivision=org["tr1"], occupation=org["anest"], rate=D("0.25"), base_salary=D("0"),
                       pay_mode="hourly", hourly_rate=D("100"), date_from=date(2025, 1, 1))
    # cumularea funcției de instructor pe același contract (CM art. 156): 30 % din salariul propriu, din 16.03
    order = make_order(admin_client, "combination", [ana], date_="2026-03-13")
    set_params(admin_client, order, {"occupation": org["doctor"].id, "pay_mode": "pct_own", "value": "30",
                                     "date_from": "2026-03-16", "date_to": "2026-06-30"})
    signed = sign(admin_client, order).data
    rec = main.combinations.get()
    assert (rec.kind, rec.value, rec.order_item_id is not None) == ("combination", D("30"), True)
    timesheet(org)
    doc = march()
    line_main = doc.lines.get(employment=main)
    [cumulare] = rows(doc, main, "CUMUL")
    # 9 200 × partea lucrată 100 % × 12 / 22 zile × 30 % = 1 505,45
    assert cumulare.amount == D("1505.45") and cumulare.percent == 30
    assert "Cumularea funcțiilor (profesiilor): Medic traumatolog-ortoped — 30 % din salariul propriu 9 200" in cumulare.note
    assert "zilele 12 / 22" in cumulare.note
    assert rows(doc, main, "SAL")[0].amount == D("9200")
    # cumulul intern: tariful orar × orele lui (0,25 × 7 ore × 22 zile = 38,5 ore), fără plată de cumulare
    [sal] = rows(doc, cumul, "SAL")
    assert (sal.quantity, sal.base, sal.amount) == (D("38.5"), D("100"), D("3850"))
    assert not rows(doc, cumul, "CUMUL")
    assert line_main.info["pay_mode"] == "salary" and doc.lines.get(employment=cumul).info["pay_mode"] == "hourly"
    # anularea ordinului scoate cumularea
    doc.delete()
    cancel(admin_client, signed)
    assert not FunctionCombination.objects.filter(employment=main).exists()


def test_combination_other_salary_fixed_hourly_stop_and_termination(admin_client, org):  # noqa: F811
    ion, main = person(org, "Popescu", "Ion")
    absent, absent_job = person(org, "Ceban", "Dan", occ="anest", salary="18000")
    order = make_order(admin_client, "substitution", [ion], date_="2026-03-01")
    item = set_params(admin_client, order, {"occupation": org["anest"].id, "pay_mode": "pct_other", "value": "50",
                                            "substitutes": absent_job.id, "date_from": "2026-03-02"})
    assert "suplinirea temporară a funcției de Medic anesteziolog-reanimatolog" in item["text"]
    assert "pe durata absenței Ceban Dan" in item["text"] and "cu plata de 50% din salariul funcției cumulate" in item["text"]
    sign(admin_client, order)
    rec = main.combinations.get()
    assert (rec.kind, rec.other_salary, rec.substituted_name) == ("substitution", D("18000"), "Ceban Dan")
    timesheet(org)
    [sup] = rows(march(), main, "CUMUL")
    assert sup.amount == D("9000")  # 50 % din 18 000, toată luna
    # încheierea mai devreme, prin ordin („action: stop”), și anularea ei
    stop = make_order(admin_client, "substitution", [ion], date_="2026-03-13")
    set_params(admin_client, stop, {"action": "stop", "combination": rec.id, "date_to": "2026-03-13"})
    stopped = sign(admin_client, stop).data
    rec.refresh_from_db()
    assert rec.date_to == date(2026, 3, 13)
    Payroll.objects.all().delete()
    [sup] = rows(march(), main, "CUMUL")
    assert sup.amount == D("4090.91") and "zilele 10 / 22" in sup.note  # 18 000 × 50 % × 10 / 22 zile (2–6, 9–13 martie)
    cancel(admin_client, stopped)
    rec.refresh_from_db()
    assert rec.date_to is None
    # încetarea raportului suplinit încheie suplinirea; anularea încetării o redeschide
    term = make_order(admin_client, "terminate", [absent], date_="2026-03-20")
    set_params(admin_client, term, {"date_from": "2026-03-20"})
    t_signed = sign(admin_client, term).data
    rec.refresh_from_db()
    assert rec.date_to == date(2026, 3, 20)
    cancel(admin_client, t_signed)
    rec.refresh_from_db()
    assert rec.date_to is None
    # sumă fixă și pe ore (de mână, din fila „Raporturi de muncă”)
    r = admin_client.post("/api/staff/combinations/", {"employment": main.id, "kind": "acting", "occupation": org["doctor"].id,
                                                       "pay_mode": "fixed", "value": "2200", "date_from": "2026-03-02",
                                                       "date_to": "2026-03-13"}, format="json")
    assert r.status_code == 201, r.data
    bad = admin_client.post("/api/staff/combinations/", {"employment": main.id, "occupation": org["doctor"].id, "pay_mode": "hourly",
                                                         "value": "120", "date_from": "2026-03-02"}, format="json")
    assert bad.status_code == 400 and "hour_type" in bad.data
    instr = HourType.objects.get(code="INSTR")
    r = admin_client.post("/api/staff/combinations/", {"employment": main.id, "occupation": org["doctor"].id, "pay_mode": "hourly",
                                                       "value": "120", "hour_type": instr.id, "date_from": "2026-03-02"}, format="json")
    assert r.status_code == 201, r.data
    ts = Timesheet.objects.get()
    set_hours(admin_client, ts, main, "INSTR", month=6)
    Payroll.objects.all().delete()
    amounts = sorted(i.amount for i in rows(march(), main, "CUMUL"))
    # 2 200 × 10 / 22 zile = 1 000; 6 ore × 120 = 720; suplinirea 9 000
    assert amounts == [D("720"), D("1000"), D("9000")]
    # cea din ordin nu se schimbă de mână
    assert admin_client.patch(f"/api/staff/combinations/{rec.id}/", {"value": "60"}, format="json").status_code == 400
    assert admin_client.delete(f"/api/staff/combinations/{rec.id}/").status_code == 400


# --- ordinul de angajare cu tarife ----------------------------------------------------------------------------------------
def test_hire_order_with_hour_rates_sign_and_cancel(admin_client, org):  # noqa: F811
    zbor = hour_type(admin_client)
    instr = HourType.objects.get(code="INSTR")
    dan = emp("Ceban", "Dan")
    order = make_order(admin_client, "hire", [dan])
    item = set_params(admin_client, order, {
        "kind": "main", "subdivision": org["tr1"].id, "occupation": org["doctor"].id, "rate": "1", "base_salary": "12000",
        "pay_mode": "mixed", "date_from": "2026-03-02",
        "hour_rates": [{"hour_type": zbor.id, "action": "add", "rate": "300", "guaranteed_hours": "50"},
                       {"hour_type": instr.id, "action": "add", "rate": "150", "date_to": "2026-12-31", "document": "CIM, anexa 1"}]})
    assert "Modalitatea de remunerare: salariu lunar și tarife pe tipuri de ore." in item["text"]
    assert "Tarife pe tipuri de ore: se stabilește tariful pentru ore zbor — 300 lei pe oră, garantat 50 ore pe lună" in item["text"]
    signed = sign(admin_client, order).data
    job = dan.employments.get()
    assert job.pay_mode == "mixed" and job.history.get().pay_mode == "mixed"
    got = [(r.hour_type.code, r.rate, r.guaranteed_hours, r.date_from, r.date_to, r.order_item_id is not None)
           for r in JobHourRate.objects.filter(employment=job).order_by("hour_type__code")]
    assert got == [("INSTR", D("150"), None, date(2026, 3, 2), date(2026, 12, 31), True),
                   ("ZBOR", D("300"), D("50"), date(2026, 3, 2), None, True)]
    card = admin_client.get("/api/staff/employments/", {"employee": dan.id}).data[0]
    assert card["pay_mode_label"].startswith("Mixt") and {r["hour_type_code"] for r in card["hour_rates"]} == {"ZBOR", "INSTR"}
    assert card["hour_rates"][0]["source"]["kind"] == "order"
    # tariful din ordin nu se schimbă de mână
    rid = card["hour_rates"][0]["id"]
    assert admin_client.patch(f"/api/worktime/job-hour-rates/{rid}/", {"rate": "1"}, format="json").status_code == 400
    assert admin_client.delete(f"/api/worktime/job-hour-rates/{rid}/").status_code == 400
    cancel(admin_client, signed)
    assert not dan.employments.exists() and not JobHourRate.objects.exists()


def test_hire_order_fills_rates_from_occupation_and_salary_order_modifies(admin_client, org):  # noqa: F811
    zbor = hour_type(admin_client)
    OccupationHourRate.objects.create(occupation=org["doctor"], hour_type=zbor, rate=D("280"), guaranteed_hours=D("45"), sort=10)
    assert [x["hour_type_code"] for x in admin_client.get("/api/worktime/occupation-hour-rates/", {"occupation": org["doctor"].id}).data] == ["ZBOR"]
    dan = emp("Ceban", "Dan")
    order = make_order(admin_client, "hire", [dan])
    set_params(admin_client, order, {"kind": "main", "subdivision": org["tr1"].id, "occupation": org["doctor"].id, "pay_mode": "mixed",
                                     "base_salary": "12000", "date_from": "2026-03-02"})  # tabelul n-a fost atins
    signed = sign(admin_client, order).data
    job = dan.employments.get()
    old = JobHourRate.objects.get(employment=job)
    assert (old.rate, old.guaranteed_hours) == (D("280"), D("45"))
    assert signed["items"][0]["params"]["hour_rates"][0]["hour_type"] == zbor.id
    # modificarea salariului: tariful nou din 01.04 (garanția rămâne), apoi trecerea la salariu lunar cu oprirea tarifului
    raise_ = make_order(admin_client, "salary_set", [dan], date_="2026-03-25")
    set_params(admin_client, raise_, {"date_from": "2026-04-01", "hour_rates": [{"hour_type": zbor.id, "action": "modify", "rate": "320"}]})
    r_signed = sign(admin_client, raise_).data
    old.refresh_from_db()
    new = JobHourRate.objects.get(employment=job, date_from=date(2026, 4, 1))
    assert old.date_to == date(2026, 3, 31) and (new.rate, new.guaranteed_hours) == (D("320"), D("45"))
    back = make_order(admin_client, "salary_set", [dan], date_="2026-04-25")
    set_params(admin_client, back, {"date_from": "2026-05-01", "pay_mode": "salary",
                                    "hour_rates": [{"hour_type": zbor.id, "action": "stop"}]})
    b_signed = sign(admin_client, back).data
    job.refresh_from_db()
    new.refresh_from_db()
    assert job.pay_mode == "salary" and staff.values_on(job, date(2026, 5, 1))["pay_mode"] == "salary"
    assert staff.values_on(job, date(2026, 4, 30))["pay_mode"] == "mixed"
    assert new.date_to == date(2026, 4, 30)
    cancel(admin_client, b_signed)
    new.refresh_from_db()
    job.refresh_from_db()
    assert new.date_to is None and staff.values_on(job, date(2026, 5, 1))["pay_mode"] == "mixed" and job.pay_mode == "mixed"
    cancel(admin_client, r_signed)
    old.refresh_from_db()
    assert old.date_to is None and JobHourRate.objects.filter(employment=job).count() == 1


# --- migrația „plata pentru cumul (%)” ---------------------------------------------------------------------------------------
STAFF_BEFORE, STAFF_AFTER = ("staff", "0006_pay_mode_function_combination"), ("staff", "0007_combination_pct_to_records")


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.fixture
def before_s4b(transactional_db):
    apps = _migrate([STAFF_BEFORE])
    yield apps
    _migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def test_migration_moves_combination_pct_to_records(before_s4b):
    apps = before_s4b
    Employee, Employment = apps.get_model("staff", "Employee"), apps.get_model("staff", "Employment")
    History = apps.get_model("staff", "EmploymentHistory")
    Subdivision, Occupation = apps.get_model("org", "Subdivision"), apps.get_model("org", "Occupation")
    sub = Subdivision.objects.create(code="S", name_ro="Secția")
    occ = Occupation.objects.create(name_ro="Contabil")
    other = Occupation.objects.create(name_ro="Casier")
    e = Employee.objects.create(tab_number="1", last_name="Rusu", first_name="Ana")
    main = Employment.objects.create(employee=e, kind="main", subdivision=sub, occupation=occ, base_salary=9000,
                                     combination_pct=20, date_from=date(2024, 1, 1), hire_order="5-p din 01.01.2024")
    History.objects.create(employment=main, event="hire", date=date(2024, 1, 1), subdivision=sub, occupation=occ, rate=1,
                           base_salary=9000, combination_pct=0)
    History.objects.create(employment=main, event="salary", date=date(2025, 3, 1), subdivision=sub, occupation=occ, rate=1,
                           base_salary=9000, combination_pct=30, order="12-p din 25.02.2025")
    History.objects.create(employment=main, event="salary", date=date(2025, 9, 1), subdivision=sub, occupation=occ, rate=1,
                           base_salary=9000, combination_pct=20, order="40-p din 20.08.2025")
    subst = Employment.objects.create(employee=e, kind="substitute", subdivision=sub, occupation=other, base_salary=7000, rate=0.5,
                                      combination_pct=50, date_from=date(2026, 1, 10), date_to=date(2026, 2, 28),
                                      status="ended", end_date=date(2026, 2, 28))  # fără istoric (bază veche)
    plain = Employment.objects.create(employee=e, kind="internal", subdivision=sub, occupation=other, date_from=date(2025, 1, 1))
    apps = _migrate([STAFF_AFTER])
    Combination = apps.get_model("staff", "FunctionCombination")
    got = [(c.employment_id, c.kind, c.pay_mode, c.value, c.date_from, c.date_to, c.order, c.occupation_id)
           for c in Combination.objects.order_by("employment_id", "date_from")]
    assert got == [
        (main.id, "combination", "pct_own", D("30"), date(2025, 3, 1), date(2025, 8, 31), "12-p din 25.02.2025", occ.id),
        (main.id, "combination", "pct_own", D("20"), date(2025, 9, 1), None, "40-p din 20.08.2025", occ.id),
        (subst.id, "substitution", "pct_own", D("50"), date(2026, 1, 10), date(2026, 2, 28), "", other.id),
    ]
    assert not Combination.objects.filter(employment_id=plain.id).exists()
    assert "combination_pct" not in {f.name for f in apps.get_model("staff", "Employment")._meta.get_fields()}


def test_cumul_type_renamed_and_hour_type_seeded(seeded):
    cumul = PayType.objects.get(code="CUMUL")
    assert cumul.name_ro == "Plata pentru cumularea funcțiilor / suplinire" and cumul.auto == "combination"
    ore = PayType.objects.get(code="ORE")
    assert (ore.formula, ore.auto, ore.in_average) == ("auto", "hour_types", True)
    assert set(HourType.objects.filter(is_system=True).values_list("code", flat=True)) == {"INSTR", "EXAM"}
