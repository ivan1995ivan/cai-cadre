"""S3: formula în tipurile de calcul — evaluatorul sigur, verificarea la salvare, dependențele, ordinea în motor, explicația
rândului, „Încearcă pe un angajat”, baza vizibilă („how”).

Angajatul de test: 35 de ore pe săptămână; martie 2026 — 22 de zile lucrătoare, norma 154 de ore; salariul 15 400 lei →
tariful orar 100 lei."""
from datetime import date
from decimal import Decimal

import pytest

from apps.payroll import engine, formula
from apps.payroll.models import EmployeePayItem, PayrollItem, PayrollLine, Payroll, PayType
from apps.staff.models import PriorExperience
from apps.worktime import services as worktime

from .test_payroll import items_of, org, person  # noqa: F401 — fixtura și ajutoarele comune
from .test_payroll_2026 import calc, line_of, timesheet

D = Decimal


def values(extra=None):
    v = {"TarifOrar": D("37.28"), "OreNoapte": D("16"), "VechimeIntreprindereAni": D("6"), "SalariuFunctie": D("6300"),
         "Suma": D("9000"), "SalariuMinim": D("6300"), "Baza": D("10000"), "Procent": D("1"), "Norma": D("168"),
         "Cantitate": D("8"), **(extra or {})}

    def resolve(kind, name):
        if kind == "var":
            return v[name]
        if kind == "const":
            return {"night_pct": D("50")}[name]
        return {"PREMIU": D("500")}[name]
    return resolve


# --- evaluatorul ------------------------------------------------------------------------------------------------------
def test_formula_ro_syntax_semicolons_and_decimal_commas():
    r = values()
    assert formula.evaluate("1,5 * 2", r).value == D("3.0")
    assert formula.evaluate("max(1,5; 2.25; 2)", r).value == D("2.25")
    assert formula.evaluate("round(10,555; 2)", r).value == D("10.56")  # rotunjirea comercială (nu „la par”)
    assert formula.evaluate("round(2,5)", r).value == D("3")
    assert formula.evaluate("daca(Norma > 0 și Suma <> 0; 1; 2)", r).value == 1
    assert formula.evaluate("if(Norma = 168 sau 0; 7; 8)", r).value == 7
    assert formula.evaluate("DACA(norma >= 200; 1; abs(-4))", r).value == 4  # literele mari / mici nu contează
    assert formula.evaluate("[PREMIU] * 10 / 100", r).value == D("50")
    # daca evaluează doar ramura aleasă: împărțirea la 0 din ramura neluată nu oprește formula
    assert formula.evaluate("daca(Norma > 200; 1 / 0; 5)", r).value == 5


@pytest.mark.parametrize("text, words", [
    ("__import__('os')", "„_”"),
    ("SalariuFunctie.real", "Atributele"),
    ("C.night_pct.real", "Atributele"),
    ("lambda: 1", "„lambda” nu există"),
    ("max(1, 2)", "„;”"),
    ("open(1)", "„open” nu există"),
    ("1 ** 2", "nu este permisă"),
    ("Norma[0]", "nu este permisă"),
    ("'text'", "„'”"),
    ("(1 + 2", "paranteza"),
    ("1 +", "nu este scrisă corect"),
    ("min", "paranteza"),
    ("round(1; 2; 3)", "1–2 argumente"),
])
def test_formula_rejects_code_with_position(text, words):
    with pytest.raises(formula.FormulaError) as exc:
        formula.evaluate(text, values())
    assert words in exc.value.text() and exc.value.position


def test_formula_division_by_zero_is_a_clear_error():
    with pytest.raises(formula.FormulaError) as exc:
        formula.evaluate("SalariuFunctie / (Norma - 168)", values())
    assert "Împărțire la zero" in exc.value.message and "Norma 168 − 168" in exc.value.message
    assert exc.value.position == 19  # „Norma”, începutul împărțitorului


def test_documented_examples_work():
    """Exemplele din documentație (docs/ro/salarizare-formule.md) — cu valorile calculate de mână."""
    r = values()
    res = formula.evaluate("TarifOrar * OreNoapte * C.night_pct / 100", r)
    assert res.value == D("298.24") and res.explanation == "TarifOrar 37,28 × OreNoapte 16 × C.night_pct 50 / 100 = 298,24"
    assert formula.evaluate("daca(VechimeIntreprindereAni >= 5; SalariuFunctie * 10 / 100; 0)", r).value == 630
    assert formula.evaluate("min(Suma; SalariuMinim)", r).value == 6300
    assert formula.evaluate("Baza * Procent / 100", r).value == 100
    # 6300 × 2/3 / 168 = 25 < 6300 / 169 = 37,2781… → × 8 ore = 298,22
    res = formula.evaluate("max(SalariuFunctie * 2/3 / Norma; SalariuMinim / 169) * Cantitate", r)
    assert engine.q(res.value) == D("298.22")
    assert list(res.used) == ["SalariuFunctie", "Norma", "SalariuMinim", "Cantitate"]


# --- verificarea la salvare -------------------------------------------------------------------------------------------
def post_type(api, code, expression="", formula_="expr", **extra):
    return api.post("/api/payroll/types/", {"code": code, "name_ro": code, "formula": formula_, "expression": expression, **extra},
                    format="json")


def test_save_checks_syntax_codes_and_cycles(admin_client, seeded):
    bad = post_type(admin_client, "F1", "TarifOrar * OreNoapte * C.nu_exista / 100")
    assert bad.status_code == 400 and "C.nu_exista nu există" in bad.data["expression"][0] and "poziția 25" in bad.data["expression"][0]
    bad = post_type(admin_client, "F1", "[NUEXISTA] + 1")
    assert bad.status_code == 400 and "[NUEXISTA] nu există" in bad.data["expression"][0]
    bad = post_type(admin_client, "F1", "SalariuFunctie *")
    assert bad.status_code == 400 and "poziția" in bad.data["expression"][0]
    bad = post_type(admin_client, "F1", "")
    assert bad.status_code == 400
    # CAS se calculează după formule: nu poate intra într-o formulă
    bad = post_type(admin_client, "F1", "[CAS] * 2")
    assert bad.status_code == 400 and "după formule" in bad.data["expression"][0]
    # „pentru toți” — nu la suma fixă
    bad = post_type(admin_client, "F1", formula_="fixed", applies_to="all")
    assert bad.status_code == 400 and "applies_to" in bad.data
    # ciclul A → B → A: A se salvează, B (care îl folosește pe A) se salvează, apoi A care îl folosește pe B — respins
    assert post_type(admin_client, "A", "SalariuFunctie * 0,1").status_code == 201
    assert post_type(admin_client, "B", "[A] * 2").status_code == 201
    a = PayType.objects.get(code="A")
    r = admin_client.patch(f"/api/payroll/types/{a.id}/", {"expression": "[B] + 1"}, format="json")
    assert r.status_code == 400 and r.data["expression"][0] == "Dependență circulară: A → B → A"
    # și prin baza de calcul
    r = admin_client.patch(f"/api/payroll/types/{a.id}/", {"expression": "Baza", "base_codes": ["B"]}, format="json")
    assert r.status_code == 400 and "Dependență circulară" in r.data["expression"][0]
    # un tip nu se poate baza pe el însuși
    r = admin_client.patch(f"/api/payroll/types/{a.id}/", {"expression": "[A] + 1"}, format="json")
    assert r.status_code == 400 and "A → A" in r.data["expression"][0]
    # codul lui A e folosit de B: nu se redenumește și nu se marchează pentru ștergere
    r = admin_client.patch(f"/api/payroll/types/{a.id}/", {"code": "A2"}, format="json")
    assert r.status_code == 400 and "B" in r.data["code"][0]
    r = admin_client.delete(f"/api/payroll/types/{a.id}/")
    assert r.status_code == 400 and "B" in r.data["detail"]
    assert PayType.objects.get(code="A").deletion_mark is False
    # verificarea pe loc din editor
    ok = admin_client.post("/api/payroll/types/check/", {"expression": "TarifOrar * OreNoapte * C.night_pct / 100"}, format="json")
    assert ok.data["ok"] and ok.data["variables"] == ["TarifOrar", "OreNoapte"] and ok.data["constants"] == ["night_pct"]
    err = admin_client.post("/api/payroll/types/check/", {"expression": "max(1, 2)"}, format="json")
    assert err.data["ok"] is False and err.data["position"] == 6
    v = admin_client.get("/api/payroll/types/variables/").data
    assert {"SalariuFunctie", "OreSarbatoarePesteNorma", "VechimeIntreprindereAni"} <= {x["name"] for x in v["variables"]}
    assert all(x["ro"] and x["ru"] and x["en"] for x in v["variables"])


def test_how_shows_the_base_for_every_type(admin_client, seeded):
    types = {t["code"]: t for t in admin_client.get("/api/payroll/types/").data}
    assert all(set(t["how"]) == {"ro", "ru", "en"} and t["how"]["ro"] for t in types.values())
    # regula motorului, cu valorile constantelor în vigoare
    assert types["SUPL"]["how"]["ro"] == "tariful orar × (primele 2 ore pe zi × 150 % + restul × 200 %), CM art. 157"
    assert "SAL Salariul de funcție + MINIM Completare până la salariul minim" in types["SINDICAT"]["how"]["ro"]
    assert "1 %" in types["SINDICAT"]["how"]["ro"] and "база" in types["SINDICAT"]["how"]["ru"]
    post_type(admin_client, "NOAPTE2", "TarifOrar * OreNoapte * C.night_pct / 100", applies_to="all")
    t = admin_client.get("/api/payroll/types/", {"category": "accrual"}).data
    how = next(x for x in t if x["code"] == "NOAPTE2")["how"]
    assert how["ro"] == "formula: TarifOrar * OreNoapte * C.night_pct / 100; pentru toți angajații"


# --- motorul ----------------------------------------------------------------------------------------------------------
def test_engine_topological_order_explanation_and_general_types(org):  # noqa: F811
    ion, job = person(org, "Popescu", "Ion", salary="15400")
    ana, _ = person(org, "Rusu", "Ana", salary="15400")
    ts = timesheet(org)
    for emp, day in ((ion, 2), (ana, 3)):  # 4 ore de noapte din tura de 7 ore
        worktime.set_cell(ts.lines.get(employment__employee=emp), day, "", "7", night="4")
    # A (sortat primul) folosește [B]; B e calculat din formulă pe rândul angajatului; ambele trebuie să iasă corect
    PayType.objects.create(code="A", name_ro="Prima A", category="accrual", formula="expr", expression="[B] * 10 / 100", sort=1,
                           applies_to="all")
    b = PayType.objects.create(code="B", name_ro="Spor B", category="accrual", formula="expr", sort=99,
                               expression="TarifOrar * Cantitate * C.night_pct / 100")
    EmployeePayItem.objects.create(employee=ion, employment=job, pay_type=b, quantity=D("16"), date_from=date(2026, 1, 1),
                                   document="Cererea nr. 5")
    # tip general: noaptea după formulă pentru toți (aici — fără rânduri), cu un rezultat negativ oprit la 0
    PayType.objects.create(code="NEG", name_ro="Test negativ", category="accrual", formula="expr", applies_to="all",
                           expression="OreNoapte - 10", sort=50)
    doc = calc()
    it = items_of(line_of(doc, ion))
    assert it["B"].amount == D("800") and it["A"].amount == D("80")  # 100 × 16 × 50 % = 800; 10 % din B
    assert it["B"].note == "TarifOrar 100 × Cantitate 16 × C.night_pct 50 / 100 = 800; Cererea nr. 5"
    assert it["B"].quantity == 16 and it["A"].note == "[B] 800 × 10 / 100 = 80"
    assert it["NEG"].amount == 0 and it["NEG"].note.startswith("formula a dat −6 — se ia 0;")
    other = items_of(line_of(doc, ana))
    assert "B" not in other and "A" not in other  # Ana n-are rândul B: A (pentru toți) = 10 % din 0 → fără rând
    assert other["NEG"].amount == 0
    # completarea până la minim și rândul de mână intră în baza tipurilor dependente (SINDICAT are MINIM în bază)
    sind = PayType.objects.get(code="SINDICAT")
    EmployeePayItem.objects.create(employee=ion, employment=job, pay_type=sind, date_from=date(2026, 1, 1))
    ln = line_of(doc, ion)
    PayrollItem.objects.create(line=ln, pay_type=PayType.objects.get(code="SAL"), amount=D("10000"), manual=True)
    engine.calculate(doc, employee_id=ion.pk)
    it = items_of(line_of(doc, ion))
    # SAL 10 000 (de mână) + NOAPTE 200 (4 h × 100 × 50 %) + B 800 + A 80 → sindicatul 1 % din SAL + NOAPTE = 102
    assert it["SAL"].amount == 10000 and it["SINDICAT"].base == D("10200") and it["SINDICAT"].amount == D("102")


def test_engine_formula_error_stops_the_calculation_with_the_employee(org):  # noqa: F811
    ion, job = person(org, "Popescu", "Ion", salary="15400")
    t = PayType.objects.create(code="DIV", name_ro="Împărțire", category="accrual", formula="expr", expression="Suma / Cantitate")
    EmployeePayItem.objects.create(employee=ion, employment=job, pay_type=t, amount=D("100"), date_from=date(2026, 1, 1))
    with pytest.raises(Exception) as exc:
        calc()
    assert "DIV" in str(exc.value.detail) and "Popescu Ion" in str(exc.value.detail) and "Împărțire la zero" in str(exc.value.detail)


def test_seniority_variables(org):  # noqa: F811
    ion, job = person(org, "Popescu", "Ion", salary="15400", hired=date(2020, 1, 1))
    PriorExperience.objects.create(employee=ion, organization="„Alfa” SRL", date_from=date(2014, 1, 1), date_to=date(2019, 12, 31))
    PayType.objects.create(code="FIDEL", name_ro="Spor de fidelitate", category="accrual", formula="expr", applies_to="all",
                           expression="daca(VechimeIntreprindereAni >= 5; SalariuFunctie * 10 / 100; 0) + VechimeAni")
    it = items_of(line_of(calc(), ion))
    # aici: 6 ani (2020–martie 2026) → 1 540; vechimea totală 12 ani → + 12
    assert it["FIDEL"].amount == D("1552")
    assert "VechimeIntreprindereAni 6 ≥ 5" in it["FIDEL"].note and "VechimeAni 12" in it["FIDEL"].note


# --- „Încearcă pe un angajat” --------------------------------------------------------------------------------------------
def test_try_on_employee_saves_nothing(admin_client, org):  # noqa: F811
    ion, job = person(org, "Popescu", "Ion", salary="15400")
    counts = lambda: (Payroll.objects.count(), PayrollLine.objects.count(), PayrollItem.objects.count(),  # noqa: E731
                      EmployeePayItem.objects.count(), PayType.objects.count())
    before = counts()
    r = admin_client.post("/api/payroll/types/try/", {"code": "NOU1", "name_ro": "Nou", "category": "accrual", "formula": "expr",
                                                      "expression": "max(SalariuFunctie * 2/3 / Norma; SalariuMinim / 169) * Cantitate",
                                                      "employee": ion.id, "year": 2026, "month": 3, "quantity": "8"}, format="json")
    assert r.status_code == 200 and r.data["errors"] == []
    ln = r.data["lines"][0]
    # 15 400 × 2/3 / 154 = 66,67 > 6 300 / 169 = 37,28 → × 8 = 533,33
    assert ln["result"] == D("533.33")
    names = {v["name"]: v for v in ln["traces"][0]["variables"]}
    assert names["Norma"]["value"] == 154 and names["Cantitate"]["value"] == 8 and names["SalariuFunctie"]["description"]
    assert any(i["code"] == "SAL" for i in ln["items"])
    assert counts() == before
    # tipul salvat; o formulă cu eroare se arată, nu oprește
    t = PayType.objects.create(code="T2", name_ro="T2", category="accrual", formula="expr", expression="Suma / Cantitate")
    before = counts()
    r = admin_client.post(f"/api/payroll/types/{t.id}/try/", {"employee": ion.id, "year": 2026, "month": 3, "amount": "100"},
                          format="json")
    assert r.status_code == 200 and "Împărțire la zero" in r.data["errors"][0]
    # formula nesalvată, greșită: eroarea verificării, cu poziția
    r = admin_client.post("/api/payroll/types/try/", {"code": "X", "name_ro": "X", "formula": "expr", "expression": "1 +",
                                                      "employee": ion.id, "year": 2026, "month": 3}, format="json")
    assert "poziția" in r.data["errors"][0]
    assert counts() == before
