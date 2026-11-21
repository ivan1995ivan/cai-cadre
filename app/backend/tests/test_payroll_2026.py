"""S2: cifrele și regulile salariului pentru 2026, pe exemple calculate de mână.

Angajatul de test: funcția cu 35 de ore pe săptămână (7 pe zi); martie 2026 are 22 de zile lucrătoare → norma 154 de ore;
salariul 15 400 lei → 100 lei pe oră. 8 martie (duminică) e sărbătoare, 7 martie — sâmbătă (repaus după grafic)."""
from datetime import date
from decimal import Decimal

import pytest

from apps.leave import services as leave_services
from apps.leave.models import Absence, SickLeave
from apps.payroll import engine
from apps.payroll.exemptions import month_parts
from apps.payroll.models import ExemptionRequest, PayConstant, Payroll, PayrollLine, PayType
from apps.payroll.payments import monthly_exemptions
from apps.staff import services as staff
from apps.worktime import services as worktime
from apps.worktime.models import Timesheet

from .test_orders import make_order, set_params
from .test_payroll import items_of, org, person  # noqa: F401 — fixtura și ajutoarele comune

D = Decimal


def timesheet(org, cells=(), month=3):  # noqa: F811
    """Pontajul lunii pentru subdiviziunea TR1, cu celulele scrise de mână: (angajatul, ziua, codul, orele)."""
    ts = Timesheet.objects.create(subdivision=org["tr1"], year=2026, month=month)
    worktime.fill_timesheet(ts)
    for emp, day, code, hours in cells:
        line = ts.lines.get(employment__employee=emp)
        worktime.set_cell(line, day, code, hours)
    return ts


def calc(month=3, approve=False):
    doc = Payroll.objects.create(year=2026, month=month)
    engine.calculate(doc)
    if approve:
        doc.status = "approved"
        doc.save()
    return doc


def line_of(doc, emp):
    return doc.lines.get(employee=emp, employment__kind__in=("main", "internal", "external"))


# --- constantele ------------------------------------------------------------------------------------------------------
def test_constants_2026_and_adopted_2027(seeded):
    c26, c27 = engine.Constants(date(2026, 12, 31)), engine.Constants(date(2027, 1, 1))
    assert (c26("min_salary"), c26("min_salary_hours"), c26("avg_salary")) == (6300, 169, 17400)
    assert [c26(k) for k in ("exemption_personal", "exemption_major", "exemption_spouse", "exemption_dependent",
                             "exemption_dependent_disabled", "exemption_dependent_income", "exemption_income_limit")] == [
        29700, 34620, 21780, 9900, 21780, 12400, 360000]
    assert [c26(k) for k in ("sick_employer_days", "sick_employer_year_days", "sick_accident_days", "sick_employer_pct",
                             "sick_avg_months", "sick_avg_cap_salaries", "leave_avg_months")] == [5, 15, 20, 75, 12, 5, 3]
    assert [c26(k) for k in ("overtime_first_hours", "overtime_first_pct", "overtime_next_pct", "holiday_pct",
                             "holiday_over_norm_pct", "holiday_hourly_pct", "cas_min_part_pct")] == [2, 150, 200, 100, 200, 200, 25]
    # 2027: doar ce e adoptat (Legea nr. 247 din 22.10.2026); restul rămâne valoarea din 2026
    assert (c27("exemption_personal"), c27("exemption_major"), c27("exemption_dependent")) == (40020, 46680, 11040)
    assert c27("exemption_spouse") == 21780 and c27("min_salary") == 6300
    assert PayConstant.objects.get(code="leave_avg_months").source == "HG nr. 426/2004"
    assert "de verificat" in PayConstant.objects.get(code="sick_accident_days").source
    assert not PayConstant.objects.filter(code="overtime_pct").exists()
    # seed-ul pe (cod, dată): rulat încă o dată nu dublează, dar valoarea 2027 se adaugă și unde lipsea
    from apps.payroll import seed

    PayConstant.objects.filter(code="exemption_personal", date_from=date(2027, 1, 1)).delete()
    PayConstant.objects.filter(code="min_salary").update(value=D("6500"))  # schimbată de utilizator — rămâne
    seed.run()
    seed.run()
    assert PayConstant.objects.filter(code="exemption_personal").count() == 2
    assert PayConstant.objects.get(code="min_salary").value == 6500


# --- orele suplimentare, sărbătorile ------------------------------------------------------------------------------------
def test_overtime_three_hours_in_one_day(admin_client, org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="15400")
    timesheet(org, [(ion, 2, "", "10")])  # 2 martie: tura de 7 ore, lucrate 10
    ln = line_of(calc(), ion)
    it = items_of(ln)
    t = ln.info["timesheet"]
    assert (t["overtime_2"], t["overtime_over"], t["overtime_days"]) == (2, 1, {"2": [2, 1]})
    # 100 lei/oră × (2 × 150 % + 1 × 200 %) = 500; salariul — întreg (orele suplimentare nu intră în normă)
    assert it["SUPL"].amount == D("500") and it["SUPL"].quantity == 3 and it["SAL"].amount == D("15400")
    assert "2 ore × 150 % + 1 ore × 200 %" in it["SUPL"].note


def test_overtime_beyond_monthly_norm_on_shifts_is_split_too(org):  # noqa: F811
    """Graficul pe ture planificat peste normă: orele peste norma lunii — suplimentare pe perioadă (2 × 150 %, restul 200 %)."""
    ion, _ = person(org, "Popescu", "Ion", salary="15400")
    timesheet(org, [(ion, 7, "8", "5")])  # sâmbătă, zi de repaus: munca de repaus, nu suplimentară
    t = line_of(calc(), ion).info["timesheet"]
    assert t["rest_work"] == 5 and t["overtime"] == 0 and t["holiday_over_norm"] == 5


def test_holiday_within_and_beyond_monthly_norm(admin_client, org):  # noqa: F811
    ana, _ = person(org, "Rusu", "Ana", salary="15400")
    ion, _ = person(org, "Popescu", "Ion", salary="15400")
    # Ana lipsește 31 martie (7 ore) și lucrează 7 ore pe 8 martie → în limita normei: +100 % peste salariu
    # Ion lucrează toată luna, plus 8 martie (7 ore, sărbătoare) și 7 martie (4 ore, repaus) → peste normă: +200 %
    timesheet(org, [(ana, 31, "A", None), (ana, 8, "", "7"), (ion, 8, "", "7"), (ion, 7, "", "4")])
    doc = calc()
    a, i = items_of(line_of(doc, ana)), items_of(line_of(doc, ion))
    ta = line_of(doc, ana).info["timesheet"]
    assert (ta["holiday_in_norm"], ta["holiday_over_norm"], ta["regular"]) == (7, 0, 147)
    assert a["SARB"].amount == D("700") and a["SAL"].amount == D("15400")  # 147 + 7 ore din 154 = salariul întreg
    ti = line_of(doc, ion).info["timesheet"]
    assert (ti["holiday"], ti["rest_work"], ti["holiday_in_norm"], ti["holiday_over_norm"]) == (7, 4, 0, 11)
    assert i["SARB"].amount == D("2200") and i["SAL"].amount == D("15400")  # 11 ore × 100 × 200 %


def test_hourly_tariff_row_gets_double_on_holidays_and_overtime_premium(org):  # noqa: F811
    """Tariful pe oră (rândul „tarif orar × ore”): ora simplă e plătită de rând; sărbătoarea — încă 100 % (dublu),
    suplimentarele — sporul 50 % / 100 %."""
    from apps.payroll.models import EmployeePayItem

    dan, _ = person(org, "Ceban", "Dan", salary="6300")
    hourly = PayType.objects.create(code="TARIF", name_ro="Tarif pe oră", formula="hourly", sort=12)
    EmployeePayItem.objects.create(employee=dan, pay_type=hourly, amount=D("50"), date_from=date(2026, 1, 1))
    timesheet(org, [(dan, 8, "", "6"), (dan, 2, "", "10")])
    it = [i for i in line_of(calc(), dan).items.select_related("pay_type") if i.pay_type.code in ("SARB", "SUPL")]
    by_note = {i.note.split(" ")[0] + i.pay_type.code: i.amount for i in it}
    assert by_note["6SARB"] == D("300")  # 6 ore × 50 × 100 % în plus (dublu)
    assert by_note["2SUPL"] == D("100")  # 50 × (2 × 50 % + 1 × 100 %)


# --- salariul minim -------------------------------------------------------------------------------------------------------
def test_salary_below_minimum_is_completed_pro_rata_and_warned(admin_client, org):  # noqa: F811
    ion, job = person(org, "Popescu", "Ion", salary="5000")
    half, _ = person(org, "Rusu", "Ana", salary="5000", rate="0.5")
    timesheet(org, [(ion, 31, "A", None)])  # 147 din 154 de ore
    doc = calc()
    it = items_of(line_of(doc, ion))
    # 6 300 × 147 / 154 = 6 013,64; salariul 5 000 × 147 / 154 = 4 772,73 → completarea 1 240,91 (fără sporuri / premii)
    assert it["SAL"].amount == D("4772.73") and it["MINIM"].amount == D("1240.91") and it["MINIM"].base == D("6013.64")
    assert items_of(line_of(doc, half))["MINIM"].amount == D("650")  # 6 300 × 0,5 − 5 000 × 0,5
    # completarea e salariu: intră în impozit, CNAM și CAS
    ln = line_of(doc, ion)
    assert ln.taxable == ln.cnam_base == items_of(ln)["CAS"].base == D("6013.64")
    # avertismentul: în dosar (raportul de muncă) și la ordinul de salariu
    jobs = admin_client.get("/api/staff/employments/", {"employee": ion.id}).data
    jobs = jobs["results"] if isinstance(jobs, dict) else jobs
    assert "sub salariul minim" in jobs[0]["warnings"][0]
    order = make_order(admin_client, "hire", [ion], date_="2026-03-02")
    item = set_params(admin_client, order, {"kind": "main", "subdivision": org["tr1"].id, "occupation": org["doctor"].id, "rate": "1",
                                            "base_salary": "6000", "date_from": "2026-03-03"})
    assert "6000 lei" in item["warnings"][0]
    item = set_params(admin_client, order, {"kind": "main", "base_salary": "6300", "date_from": "2026-03-03"})
    assert item["warnings"] == []
    # alerta din „Termene și alerte”
    from apps.alerts import engine as alerts

    assert any(a.kind == "min_wage" and a.employee == ion.id for a in alerts.collect(date(2026, 3, 10)))


# --- baza minimă CAS --------------------------------------------------------------------------------------------------------
def test_minimum_cas_base_full_time_half_time_part_time_and_exceptions(org):  # noqa: F811
    PayType.objects.filter(code="MINIM").update(is_active=False)  # fără completare: salariul rămâne sub minim
    full, _ = person(org, "Ababii", "Ion", salary="5000")
    half, _ = person(org, "Botnaru", "Ana", salary="5000", rate="0.5")
    small, _ = person(org, "Ciobanu", "Dan", salary="6300", rate="0.1")
    away, away_job = person(org, "Dodon", "Eva", salary="5000")
    Absence.objects.create(employee=away, employment=away_job, kind="unpaid", date_from=date(2026, 3, 1), date_to=date(2026, 3, 31), days=31)
    contractor, _ = person(org, "Esanu", "Vlad", kind="contractor", salary="0", rate="0.5")
    timesheet(org)
    doc = calc()
    f = items_of(line_of(doc, full))
    # normă întreagă: baza 5 000 < 6 300 → CAS pe diferență 1 300 × 24 % = 312
    assert (f["CASMIN"].base, f["CASMIN"].amount) == (D("1300"), D("312"))
    assert "baza reală 5000.00, baza minimă 6300.00" in f["CASMIN"].note
    full_line = line_of(doc, full)
    assert full_line.cas == f["CAS"].amount + D("312") and full_line.info["cas_min"]["minimum"] == 6300
    # jumătate de normă: 6 300 × 0,5 = 3 150 (peste 25 %) − 2 500 = 650 → 156
    assert items_of(line_of(doc, half))["CASMIN"].amount == D("156")
    # 0,1 normă: 630 lei < 25 % din salariul minim (1 575) → diferența 945 × 24 % = 226,80
    s = items_of(line_of(doc, small))["CASMIN"]
    assert (s.base, s.amount) == (D("945"), D("226.80")) and "timp parțial" in s.note
    # excepțiile: concediu neplătit toată luna (fără timp lucrat), contractul de prestări servicii
    assert "CASMIN" not in items_of(line_of(doc, away)) and not doc.lines.get(employee=away).items.filter(pay_type__code="CAS").exists()
    assert "CASMIN" not in items_of(doc.lines.get(employee=contractor))
    # IPC21: diferența intră în baza de calcul CAS a persoanei
    from apps.payroll.xml_export import ipc21_rows

    doc.status = "approved"
    doc.save()
    row = next(r for r in ipc21_rows(2026, 3)["rows"] if r["c2"] == full.full_name())
    assert row["c9"] == D("6300") and row["c11"] == D("1512")


def test_minimum_cas_base_does_not_apply_when_salary_is_enough(org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="15400")
    timesheet(org)
    assert "CASMIN" not in items_of(line_of(calc(), ion))


# --- boala ---------------------------------------------------------------------------------------------------------------
def sick(emp, number, start, end, kind="illness"):
    s = SickLeave(employee=emp, series="A", number=str(number), kind=kind, date_from=start, date_to=end)
    leave_services.save_sick_leave(s)
    return s


def test_sick_employer_days_capped_at_15_per_year(org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="15500")
    sick(ion, 1, date(2026, 1, 12), date(2026, 1, 21))  # 5 zile ale angajatorului
    sick(ion, 2, date(2026, 2, 9), date(2026, 2, 11))  # 3 zile (certificatul e scurt) → 8
    sick(ion, 3, date(2026, 2, 23), date(2026, 3, 4))  # 5 zile (23–27.02) → 13
    sick(ion, 4, date(2026, 3, 16), date(2026, 3, 25))  # doar 2 zile până la plafonul de 15 (16–17.03)
    sick(ion, 5, date(2026, 4, 6), date(2026, 4, 10))  # plafonul atins: nimic din partea angajatorului
    doc = calc(3)
    b = items_of(line_of(doc, ion))["BOALA"]
    # fără istoric aprobat: 15 500 / 31 = 500 lei pe zi × 2 zile × 75 % = 750
    assert (b.quantity, b.base, b.amount) == (2, D("500"), D("750")) and "plafonul de 15 zile" in b.note
    assert "BOALA" not in items_of(line_of(calc(4), ion))
    feb = items_of(line_of(calc(2), ion))["BOALA"]
    assert feb.quantity == 8  # 3 + 5 zile în februarie


def test_work_accident_paid_20_days_outside_the_yearly_cap(org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="15500")
    sick(ion, 1, date(2026, 3, 2), date(2026, 3, 31), kind="work_accident")
    it = items_of(line_of(calc(3), ion))
    a = it["BOALAACC"]
    # 20 de zile × 500 lei × 100 % (Legea 756/1999 — de verificat); nu intră în plafonul de 15
    assert (a.quantity, a.percent, a.amount) == (20, 100, D("10000")) and "BOALA" not in it


def test_sick_average_uses_twelve_months_and_five_average_salaries_cap(org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion", salary="100000")
    for m in (1, 2):
        timesheet(org, month=m)
        calc(m, approve=True)
    sick(ion, 1, date(2026, 3, 2), date(2026, 3, 6))
    b = items_of(line_of(calc(3), ion))["BOALA"]
    # media lunară 100 000 > 5 × 17 400 = 87 000 → plafonul; pe zi 87 000 / 31 = 2 806,45
    assert b.base == D("2806.45") and "2 luni" in b.note and "plafonul 87000" in b.note


# --- scutirile ------------------------------------------------------------------------------------------------------------
def test_child_from_april_gives_n_from_may(org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion")
    req = ExemptionRequest.objects.create(employee=ion, date=date(2025, 12, 15), kind="personal")
    req.dependents.create(name="Popescu Matei", relation="child", date_from=date(2026, 4, 10), document="certificatul de naștere")
    c = engine.Constants(date(2026, 5, 31))
    income = {ion.id: D("20000")}
    assert monthly_exemptions(2026, 4, c, income)[ion.id] == D("2475")  # doar P: 29 700 / 12
    assert monthly_exemptions(2026, 5, c, income)[ion.id] == D("3300")  # P + N: 2 475 + 825
    assert month_parts(2026, 5, c, income)[ion.id]["N"] == 9900
    assert req.code() == "PN1" and req.code(date(2026, 4, 1)) == "P"
    # cererea se aplică din luna următoare depunerii; o cerere nouă o închide pe cea veche
    assert req.date_from == date(2026, 1, 1)
    new = ExemptionRequest.objects.create(employee=ion, date=date(2026, 6, 20), kind="major", major_category="b")
    new.replace_previous()
    req.refresh_from_db()
    assert new.date_from == date(2026, 7, 1) and req.date_to == date(2026, 6, 30)
    assert monthly_exemptions(2026, 7, c, income)[ion.id] == D("2885")  # M 34 620 / 12, fără copil (nu e în cererea nouă)
    # venitul întreținutului peste plafon: fără N
    req.dependents.update(income_ok=False)
    assert monthly_exemptions(2026, 5, c, income)[ion.id] == D("2475")


def test_exemption_request_api_with_family_dependents_and_validation(admin_client, org):  # noqa: F811
    from apps.org.models import DictItem
    from apps.staff.models import FamilyMember

    ion, _ = person(org, "Popescu", "Ion")
    son = FamilyMember.objects.create(employee=ion, relation=DictItem.objects.get(kind="family", code="son"), full_name="Popescu Matei",
                                      idnp="2015000123456", birth_date=date(2015, 5, 1), dependent=True)
    body = {"employee": ion.id, "date": "2026-01-15", "kind": "personal",
            "dependents": [{"family_member": son.id}, {"name": "Popescu Vera", "relation": "sibling"}]}
    r = admin_client.post("/api/payroll/exemptions/", body, format="json")
    assert r.status_code == 400 and "dizabilitate" in str(r.data)  # fratele / sora — doar cu dizabilitate
    body["dependents"][1]["disability"] = "childhood"
    r = admin_client.post("/api/payroll/exemptions/", body, format="json")
    assert r.status_code == 201, r.data
    d = r.data["dependents"]
    assert (d[0]["name"], d[0]["idnp"], d[0]["relation"], d[0]["code"]) == ("Popescu Matei", "2015000123456", "child", "N")
    assert d[1]["code"] == "H" and r.data["code"] == "PN1H1" and r.data["date_from"] == "2026-02-01"
    bad = admin_client.post("/api/payroll/exemptions/", {"employee": ion.id, "kind": "major"}, format="json")
    assert bad.status_code == 400 and "major_category" in bad.data
    html = admin_client.get(f"/api/payroll/exemptions/{r.data['id']}/print/").content.decode()
    assert "PRIVIND ACORDAREA SCUTIRILOR" in html and "Anexa nr. 6" in html and "Popescu Matei" in html and "PN1H1" in html
    assert "61 380,00" in html  # suma anuală cerută: P 29 700 + N 9 900 + H 21 780


def test_waiver_and_income_limit_stop_p_without_touching_past_months(org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion")
    req = ExemptionRequest.objects.create(employee=ion, date=date(2025, 12, 15), kind="personal", waiver_date=date(2026, 6, 15))
    req.dependents.create(name="Popescu Matei")
    c = engine.Constants(date(2026, 7, 31))
    income = {ion.id: D("20000")}
    assert monthly_exemptions(2026, 6, c, income)[ion.id] == D("3300")  # luna cererii de renunțare: încă P
    assert monthly_exemptions(2026, 7, c, income)[ion.id] == D("825")  # din luna următoare: doar N
    assert req.code(date(2026, 7, 1)) == "N1"
    # plafonul la angajator: venitul anului de aici (cu luna) peste 360 000 → P cade din luna aceea, lunile trecute rămân
    rich, _ = person(org, "Rusu", "Ana", salary="120000")
    ExemptionRequest.objects.create(employee=rich, date=date(2025, 12, 15), kind="personal")
    for m in (1, 2, 3):
        timesheet(org, month=m)
        calc(m, approve=True)
    assert monthly_exemptions(2026, 3, c, {rich.id: D("0")})[rich.id] == D("2475")  # 240 000 până în martie
    assert monthly_exemptions(2026, 3, c, {rich.id: D("119999.99")})[rich.id] == D("2475")  # sub plafon: P rămâne
    assert monthly_exemptions(2026, 3, c, {rich.id: D("120000")})[rich.id] == 0  # exact 360 000: nu e „mai mic” — fără P
    assert monthly_exemptions(2026, 4, c, {rich.id: D("120000")})[rich.id] == 0  # 360 000 + 120 000 > 360 000
    from apps.alerts import engine as alerts

    found = [a for a in alerts.collect(date(2026, 4, 10)) if a.kind == "exemption_limit"]
    assert [a.employee for a in found] == [rich.id] and "360 000" in found[0].text  # 360 000 ≥ 90 % din plafon


def test_ials21_with_spouse_dependent_and_disabled_dependent(admin_client, org):  # noqa: F811
    from xml.etree import ElementTree as ET

    from .test_payroll_payments import paid_salary

    ion, _ = person(org, "Popescu", "Ion", salary="30000")
    ion.idnp = "2001000123456"
    ion.save()
    req = ExemptionRequest.objects.create(employee=ion, date=date(2025, 12, 15), kind="personal", spouse_major=True,
                                          spouse_name="Popescu Ana", spouse_idnp="2002000111222", spouse_category="b")
    req.dependents.create(name="Popescu Matei", idnp="2015000123456")
    req.dependents.create(name="Popescu Vera", idnp="1990000123456", relation="sibling", disability="severe")
    timesheet(org)
    calc(3, approve=True)
    paid_salary(admin_client, 3, "2026-03-31")
    data = admin_client.get("/api/payroll/tax-reports/ials21/", {"year": 2026}).data
    row = data["rows"][0]
    # scutirea lunii (29 700 + 21 780 + 9 900 + 21 780) / 12 = 6 930, împărțită pe coduri după sumele anuale
    assert (row["P"], row["Sm"], row["N"], row["H"], row["exemption"]) == (2475, 1815, 825, 1815, 6930)
    assert row["spouse_idnp"] == "2002000111222"
    assert data["dependents"] == [{"employee": "2001000123456", "N": "2015000123456", "H": "", "name": "Popescu Matei"},
                                  {"employee": "2001000123456", "N": "", "H": "1990000123456", "name": "Popescu Vera"}]
    root = ET.fromstring(admin_client.get("/api/payroll/tax-reports/ials21/", {"year": 2026, "export": "xml"}).content)
    r = root.find("dinamicTable/row")
    assert (r.findtext("sumscpcur"), r.findtext("sumscsmcur"), r.findtext("sumscncur"), r.findtext("sumschcur")) == (
        "2475.00", "1815.00", "825.00", "1815.00")
    assert r.findtext("tinsotcds") == "2002000111222"
    annex = [(x.findtext("tinpin"), x.findtext("tinpih")) for x in root.findall("dinamicTable2/row")]
    assert annex == [("2015000123456", ""), ("", "1990000123456")]


# --- migrația ----------------------------------------------------------------------------------------------------------
PAY_BEFORE, PAY_AFTER = ("payroll", "0010_payroll_subdivision_label"), ("payroll", "0011_exemption_dependents_and_2026_rules")


def migrate_payroll(target):
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate([target])
    return executor.loader.project_state(target).apps


@pytest.fixture
def before_s2(transactional_db):
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    yield migrate_payroll(PAY_BEFORE)
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


def test_migration_moves_dependents_to_rows_and_fixes_shipped_values(before_s2):
    apps = before_s2
    from apps.staff.models import Employee  # tabela dosarului e la zi (doar salarizarea e dată înapoi)

    Request, Constant = apps.get_model("payroll", "ExemptionRequest"), apps.get_model("payroll", "PayConstant")
    e = Employee.objects.create(tab_number="1", last_name="Popescu", first_name="Ion")
    old = Request.objects.create(employee_id=e.pk, year=2025, date=date(2025, 1, 10), kind="personal",
                                 dependents=[{"name": "Matei", "idnp": "2015000123456", "disabled": False}])
    cur = Request.objects.create(employee_id=e.pk, year=2026, date=date(2026, 1, 10), kind="personal", spouse=True, spouse_name="Ana",
                                 dependents=[{"name": "Vera", "idnp": "", "disabled": True}])
    Constant.objects.create(code="min_salary", name="Salariul minim", value=D("5500"), date_from=date(2026, 1, 1), source="HG anuală (de verificat)")
    Constant.objects.create(code="avg_salary", name="Salariul mediu", value=D("17250"), date_from=date(2026, 1, 1), source="scris de mână")
    Constant.objects.create(code="overtime_pct", name="Spor", value=D("60"), date_from=date(2026, 1, 1))
    apps = migrate_payroll(PAY_AFTER)
    Request, Dependent = apps.get_model("payroll", "ExemptionRequest"), apps.get_model("payroll", "ExemptionDependent")
    Constant = apps.get_model("payroll", "PayConstant")
    old, cur = Request.objects.get(pk=old.pk), Request.objects.get(pk=cur.pk)
    assert (old.date_from, old.date_to, old.needs_review) == (date(2025, 1, 1), date(2025, 12, 31), False)
    assert (cur.date_from, cur.date_to, cur.needs_review, cur.spouse_major) == (date(2026, 1, 1), None, True, False)
    assert "abrogat" in cur.review_note
    assert list(Dependent.objects.filter(request=old).values_list("name", "idnp", "disability")) == [("Matei", "2015000123456", "")]
    assert Dependent.objects.get(request=cur).disability == "severe"
    c = {x.code: x for x in Constant.objects.all()}
    assert c["min_salary"].value == 6300 and c["min_salary"].source == "HG nr. 771 din 17.12.2025"
    assert c["avg_salary"].value == 17250  # schimbată de utilizator: rămâne
    assert c["overtime_first_pct"].value == 160 and "overtime_pct" not in c
