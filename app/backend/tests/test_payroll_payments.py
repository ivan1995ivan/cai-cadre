"""Etapa 4b (partea 2): plata salariului, avansul, banca, datoriile, fișa personală anuală, IPC21, IALS21, IRM19."""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook

from apps.payroll import engine
from apps.payroll.models import ExemptionRequest, Payment, PaymentLine, Payroll
from apps.payroll.payments import settlement
from apps.staff.models import Employee

from .test_orders import make_order, set_params, sign
from .test_payroll import org, person  # noqa: F401 — fixtura și ajutorul comun


def approved_payroll(month=3):
    doc = Payroll.objects.create(year=2026, month=month)
    engine.calculate(doc)
    doc.status = "approved"
    doc.save()
    return doc


def paid_salary(client, month, paid_on, **extra):
    """Îndreptarea pe salariu a lunii (pe sold, dacă nu se dă `payroll`), aprobată și achitată la `paid_on`."""
    r = client.post("/api/payroll/payments/", {"year": 2026, "month": month, "kind": "salary", **extra}, format="json")
    assert r.status_code == 201, r.data
    pay = Payment.objects.get(pk=r.data["id"])
    assert client.post(f"/api/payroll/payments/{pay.id}/approve/").status_code == 200
    assert client.post(f"/api/payroll/payments/{pay.id}/pay/", {"paid_on": paid_on}, format="json").status_code == 200
    return pay


def test_advance_then_salary_payment_bank_and_debts(admin_client, org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion")
    ion.iban = "MD24AG000225100013104168"
    ion.save()
    ana, _ = person(org, "Rusu", "Ana", occ="nurse", salary="9200")  # fără IBAN → numerar
    # avansul: 40 % din salariul de funcție × norma (brut), cu impozitul reținut la achitare: CNAM 9 %, apoi 12 % din rest
    r = admin_client.post("/api/payroll/payments/", {"year": 2026, "month": 3, "kind": "advance", "date": "2026-03-15"}, format="json")
    assert r.status_code == 201, r.data
    adv = Payment.objects.get(pk=r.data["id"])
    lines = {ln.employee.last_name: ln for ln in adv.lines.select_related("employee")}
    p = lines["Popescu"]
    assert (p.gross, p.cnam, p.income_tax, p.amount) == (Decimal("5864"), Decimal("527.76"), Decimal("640.35"), Decimal("4695.89"))
    assert p.method == "card"
    assert lines["Rusu"].gross == Decimal("3680") and lines["Rusu"].amount == Decimal("2946.94") and lines["Rusu"].method == "cash"
    assert r.data["totals"] == {"card": 4695.89, "cash": 2946.94, "total": 7642.83, "gross": 9544.0, "exemption": 0.0, "cnam": 858.96,
                                "income_tax": 1042.21, "deductions": 0.0, "count": 2}
    assert admin_client.post(f"/api/payroll/payments/{adv.id}/pay/").status_code == 400  # întâi se aprobă
    admin_client.post(f"/api/payroll/payments/{adv.id}/approve/")
    paid = admin_client.post(f"/api/payroll/payments/{adv.id}/pay/", {"paid_on": "2026-03-16", "reference": "OP nr. 12"}, format="json")
    assert paid.data["status"] == "paid" and paid.data["reference"] == "OP nr. 12"
    csv = admin_client.get(f"/api/payroll/payments/{adv.id}/bank-file/").content.decode("utf-8-sig")
    assert "MD24AG000225100013104168" in csv and "4695.89" in csv and "Rusu" not in csv  # doar cardurile
    # calculul lunii nu scade avansul și nu are impozite: brutul, bazele, CAS
    doc = approved_payroll()
    ion_line = doc.lines.get(employee=ion)
    assert not ion_line.items.filter(pay_type__code__in=("AVANS", "IMPOZIT", "CNAM")).exists()
    assert ion_line.deductions == 0 and ion_line.net == ion_line.gross
    # avansul nu se face în baza unui calcul; salariul — doar în baza unui calcul aprobat
    r = admin_client.post("/api/payroll/payments/", {"payroll": doc.id, "kind": "advance"}, format="json")
    assert r.status_code == 400 and "payroll" in r.data
    draft = Payroll.objects.create(year=2026, month=2)
    r = admin_client.post("/api/payroll/payments/", {"payroll": draft.id, "kind": "salary"}, format="json")
    assert r.status_code == 400 and "aprobat" in str(r.data)
    r = admin_client.post("/api/payroll/payments/", {"payroll": doc.id, "kind": "salary", "method": "card"}, format="json")
    sal = Payment.objects.get(pk=r.data["id"])
    assert [ln.employee_id for ln in sal.lines.all()] == [ion.id]  # doar cardurile, la cerere
    sal_line = sal.lines.get()
    # la salariu: restul brutului lunii; CNAM și impozitul pe tot venitul lunii, minus cele reținute din avans
    assert sal_line.gross + p.gross == ion_line.gross
    cnam = engine.q(ion_line.cnam_base * Decimal("0.09"))
    assert sal_line.cnam + p.cnam == cnam
    assert sal_line.income_tax + p.income_tax == engine.q((ion_line.taxable - cnam) * Decimal("0.12"))
    assert sal_line.amount == sal_line.gross - sal_line.cnam - sal_line.income_tax
    # soldul e înainte de impozit: brutul calculat minus brutul achitat (Ion — doar avansul încă; Ana — la fel)
    debts = {d["name"]: d for d in admin_client.get("/api/payroll/debts/", {"year": 2026, "month": 3}).data["rows"]}
    assert debts["Popescu Ion"]["debt"] == float(ion_line.gross - p.gross)
    ana_line = doc.lines.get(employee=ana)
    assert debts["Rusu Ana"]["debt"] == float(ana_line.gross - lines["Rusu"].gross)
    admin_client.post(f"/api/payroll/payments/{sal.id}/approve/")
    admin_client.post(f"/api/payroll/payments/{sal.id}/pay/", {"paid_on": "2026-04-05"}, format="json")
    debts = {d["name"]: d for d in admin_client.get("/api/payroll/debts/", {"year": 2026, "month": 4}).data["rows"]}
    assert "Popescu Ion" not in debts and "Rusu Ana" in debts
    # decontarea lunii (fluturașul): Ion plătit tot — impozitele reținute; Ana — impozitele pe toată luna, restul de primit
    st = settlement(2026, 3)
    i, a = st[ion.id], st[ana.id]
    assert i["final"] and i["rest"] == 0 and i["net"] == p.amount + sal_line.amount and i["paid_advance"] == p.amount
    assert i["cnam"] == cnam and i["income_tax"] == sal_line.income_tax + p.income_tax
    ana_cnam = engine.q(ana_line.cnam_base * Decimal("0.09"))
    assert not a["final"] and a["cnam"] == ana_cnam and a["income_tax"] == engine.q((ana_line.taxable - ana_cnam) * Decimal("0.12"))
    assert a["rest"] == a["net"] - lines["Rusu"].amount
    html = admin_client.get(f"/api/payroll/payments/{sal.id}/print/").content.decode()
    assert "STAT DE PLATĂ" in html and "Popescu Ion" in html
    bank = admin_client.get(f"/api/payroll/payments/{adv.id}/bank-list/").content.decode()
    assert "LISTA PENTRU BANCĂ" in bank and "MD24AG000225100013104168" in bank and "Rusu Ana" not in bank
    # a doua plată de salariu pe aceeași lună nu mai găsește nimic pentru Ion
    again = admin_client.post("/api/payroll/payments/", {"year": 2026, "month": 3, "kind": "salary"}, format="json")
    assert [ln["employee_name"] for ln in admin_client.get(f"/api/payroll/payments/{again.data['id']}/lines/").data] == ["Rusu Ana"]
    line = PaymentLine.objects.get(payment_id=again.data["id"])
    assert admin_client.patch(f"/api/payroll/payment-lines/{line.id}/", {"amount": "100"}, format="json").status_code == 200


def test_annual_card_ipc21_ials21_and_irm19(admin_client, org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion")
    ion.idnp = "2001000123456"
    ion.save()
    ExemptionRequest.objects.create(employee=ion, date=date(2025, 12, 20), kind="personal")
    approved_payroll(3)
    approved_payroll(4)
    paid_salary(admin_client, 3, "2026-04-05")
    paid_salary(admin_client, 4, "2026-05-05")
    card = admin_client.get(f"/api/payroll/annual-card/{ion.id}/", {"year": 2026}).data
    assert [r["month"] for r in card["rows"]] == [3, 4] and card["exemption_code"] == "P"
    assert card["rows"][1]["cum_tax"] == pytest.approx(card["rows"][0]["tax"] + card["rows"][1]["tax"], abs=0.01)
    html = admin_client.get(f"/api/payroll/annual-card/{ion.id}/", {"year": 2026, "print": 1}).content.decode()
    assert "Anexa nr. 8" in html and "05.04.2026" in html and "05.05.2026" in html  # pe datele achitării
    ipc = admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 3}).data
    assert ipc["total"]["persons"] == 1 and ipc["rows"][0]["idnp"] == "2001000123456" and ipc["rows"][0]["category"] == "101"
    assert ipc["rows"][0]["tariff"] == 24 and "codul CNAS" in ipc["header_missing"]
    x = admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 3, "export": "xlsx"})
    wb = load_workbook(BytesIO(x.content))
    assert wb.sheetnames == ["Tabelul 1", "Tabelul 2"] and wb["Tabelul 2"].cell(row=2, column=3).value == "2001000123456"
    ials = admin_client.get("/api/payroll/tax-reports/ials21/", {"year": 2026}).data
    assert ials["rows"][0]["P"] == ials["rows"][0]["exemption"] > 0 and ials["rows"][0]["income"] == pytest.approx(card["total"]["gross"])
    # IRM19: angajarea prin ordin în perioadă, cu termenul de 10 zile lucrătoare
    dan = Employee.objects.create(tab_number="99", last_name="Ceban", first_name="Dan", idnp="2002000123457")
    order = make_order(admin_client, "hire", [dan], date_="2026-03-02")
    set_params(admin_client, order, {"kind": "main", "subdivision": org["tr1"].id, "occupation": org["doctor"].id,
                                     "rate": "1", "base_salary": "14000", "date_from": "2026-03-03"})
    sign(admin_client, order)
    irm = admin_client.get("/api/payroll/tax-reports/irm19/", {"date_from": "2026-03-01", "date_to": "2026-03-31"}).data
    assert len(irm["rows"]) == 1 and irm["rows"][0]["code"] == "01" and irm["rows"][0]["deadline"] == "2026-03-16"
    x = admin_client.get("/api/payroll/tax-reports/irm19/", {"date_from": "2026-03-01", "date_to": "2026-03-31", "export": "xlsx"})
    assert load_workbook(BytesIO(x.content))["IRM19"].cell(row=2, column=2).value == "Ceban Dan"


# --- declarațiile electronice XML (schemele SFS din dosarul „xml file”) ---------------------------------------------------
XSD_DIR = __import__("pathlib").Path(__file__).resolve().parents[2] / "xml file"


def _validate(content: bytes, xsd_name: str):
    """Validarea după schema oficială, dacă lxml e instalat (în mediul de dezvoltare)."""
    try:
        from lxml import etree
    except ImportError:
        return None
    text = (XSD_DIR / xsd_name).read_text(encoding="utf-8")
    schema = etree.XMLSchema(etree.fromstring(text[text.index("<xs:schema"):].encode("utf-8")))
    ok = schema.validate(etree.fromstring(content))
    return ok, [e.message for e in schema.error_log]


def test_xml_declarations_follow_the_sfs_schemas(admin_client, org):  # noqa: F811
    from xml.etree import ElementTree as ET

    from apps.core.models import Company
    from apps.org.models import DictItem

    c = Company.get()
    c.idno, c.name_ro, c.director, c.chief_accountant = "1003600012345", "IMSP Spitalul Clinic", "Director", "Contabil"
    c.caem = "8610"  # din Constante (nu mai e în setările declarațiilor)
    c.save()
    admin_client.put("/api/payroll/tax-reports/settings/", {"cnas_code": "1234567", "sfs_code": "01", "cuatm": "0100",
                                                           "email": "hr@spital.md", "phone": "022000000"}, format="json")
    ion, job = person(org, "Popescu", "Ion")
    ion.idnp = "2001000123456"
    ion.save()
    org["doctor"].code = "221201"
    org["doctor"].save()
    ana, _ = person(org, "Rusu", "Ana", occ="nurse", salary="9200")
    ana.idnp = "2001000654321"
    ana.save()
    req = ExemptionRequest.objects.create(employee=ion, date=date(2025, 12, 20), kind="personal", spouse_major=True,
                                          spouse_name="Popescu Ana", spouse_idnp="2002000111222", spouse_category="b")
    req.dependents.create(name="Copil", idnp="2015000123456")
    approved_payroll(3)
    paid_salary(admin_client, 3, "2026-03-31")  # tabelul 1: venitul achitat în lună
    r = admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 3, "export": "xml"})
    assert r.status_code == 200 and r["Content-Disposition"].endswith('IPC21-2026-03.xml"')
    root = ET.fromstring(r.content)
    assert root.get("TypeName") == "IPC21" and root.findtext("peroidnalog/datefisc") == "L/03/2026"
    assert root.findtext("fiscCod/caem") == "8610"
    gross = sum(ln.gross for ln in Payroll.objects.get(month=3).lines.all())
    assert root.findtext("table1/row/r11c4") == f"{gross:.2f}" == root.findtext("table1/row/r61c4")
    assert root.findtext("summContr") == root.findtext("table1/row/r11c5")
    rows = root.findall("dinamicTable2/row")
    ion_row = next(x for x in rows if x.findtext("c3") == "2001000123456")
    assert (ion_row.get("line"), ion_row.findtext("c7"), ion_row.findtext("c71"), ion_row.findtext("c8")) == ("1", "101", "24", "221201")
    assert root.findtext("table2/row/r11bc9") == root.findtext("dinamicTable2/total/tot2c9")
    if (v := _validate(r.content, "ipc21.txt")) is not None:
        assert v[0], v[1]
    r = admin_client.get("/api/payroll/tax-reports/ials21/", {"year": 2026, "export": "xml"})
    root = ET.fromstring(r.content)
    row = next(x for x in root.findall("dinamicTable/row") if x.findtext("tinsalcds") == "2001000123456")
    p, sm, n = (Decimal(row.findtext(t)) for t in ("sumscpcur", "sumscsmcur", "sumscncur"))
    assert row.findtext("tinsotcds") == "2002000111222" and p > sm > n > 0
    assert Decimal(row.findtext("sumsctotcur")) == p + sm + n
    assert root.findtext("GroupsummContr/summContr") == root.findtext("dinamicTable/totalRow/impreticur")
    assert root.findtext("dinamicTable2/row/tinpin") == "2015000123456" and root.findtext("nrinscr") == "2"
    if (v := _validate(r.content, "ials21.txt")) is not None:
        assert v[0], v[1]
    # IRM19: angajare (01), încetare la cerere (02 / 114), concediu de îngrijire a copilului (157 cu perioada)
    dan = Employee.objects.create(tab_number="99", last_name="Ceban", first_name="Dan", idnp="2002000123457")
    hire = make_order(admin_client, "hire", [dan], date_="2026-03-02")
    set_params(admin_client, hire, {"kind": "main", "subdivision": org["tr1"].id, "occupation": org["doctor"].id, "rate": "1",
                                    "base_salary": "14000", "date_from": "2026-03-03", "date_to": "2026-12-31"})
    sign(admin_client, hire)
    end = make_order(admin_client, "terminate", [dan], date_="2026-03-20")
    set_params(admin_client, end, {"date_from": "2026-03-31", "reason": DictItem.objects.get(kind="termination", code="resignation").id})
    sign(admin_client, end)
    care = make_order(admin_client, "leave_childcare", [ana], date_="2026-03-10")
    set_params(admin_client, care, {"date_from": "2026-03-11", "date_to": "2028-01-10"})
    sign(admin_client, care)
    r = admin_client.get("/api/payroll/tax-reports/irm19/", {"date_from": "2026-03-01", "date_to": "2026-03-31", "export": "xml"})
    root = ET.fromstring(r.content)
    got = [(x.findtext("c3"), x.findtext("c5"), x.findtext("c6"), x.findtext("c8"), x.findtext("c9"), x.findtext("c10"))
           for x in root.findall("dinamicTable/row")]
    assert got == [("2002000123457", "", "", "05", "", "2026-03-03"), ("2001000654321", "157", "2026-03-11", "", "", ""),
                   ("2002000123457", "", "", "02", "114", "2026-03-31")]
    assert root.get("TypeName") == "IRM19" and root.findtext("fiscCod/cnas") == "1234567"


def test_tax_reports_need_their_permission(org, make_user, client_for):  # noqa: F811
    hr = make_user("insp", ["hr_inspector"])
    assert client_for(hr).get("/api/payroll/tax-reports/ipc21/").status_code == 403
    acc = make_user("contabil", ["accountant"])
    assert client_for(acc).get("/api/payroll/tax-reports/ipc21/").status_code == 200


def test_salary_certificate_for_bank(admin_client, org, make_user, client_for):  # noqa: F811
    from apps.staff.printing import salary_period

    ion, _ = person(org, "Popescu", "Ion")
    ion.idnp = "2001000123456"
    ion.save()
    for m in (3, 4):
        approved_payroll(m)
    paid_salary(admin_client, 3, "2026-04-05")
    url = f"/api/staff/employees/{ion.id}/print/"
    r = admin_client.get(url, {"doc": "certificate_salary", "from": "2026-02", "to": "2026-04", "purpose": "BC „Moldindconbank” SA"})
    assert r.status_code == 200
    html = r.content.decode()
    assert "ADEVERINȚĂ PRIVIND SALARIUL" in html and "2001000123456" in html and "pe durată nedeterminată" in html
    assert "<td>martie 2026</td>" in html and "<td>aprilie 2026</td>" in html and "<td>februarie 2026</td>" not in html  # doar lunile cu calcul aprobat
    assert "perioada februarie 2026 – aprilie 2026" in html
    st = {m: settlement(2026, m)[ion.id] for m in (3, 4)}
    lei = lambda v: f"{v:,.2f}".replace(",", " ").replace(".", ",")  # noqa: E731
    assert lei(st[3]["net"]) in html and lei(st[4]["net"]) in html
    assert lei(st[3]["gross"] + st[4]["gross"]) in html and lei((st[3]["net"] + st[4]["net"]) / 2) in html  # totalul, media
    assert "Media lunară (2 luni)" in html and "Moldindconbank" in html and "Contabil-șef" in html
    # ultimele N luni încheiate, fără luna curentă; perioada greșită — mesaj
    assert salary_period({"months": "3"}, today=date(2026, 5, 20)) == ((2026, 2), (2026, 4))
    assert salary_period({}, today=date(2026, 1, 10)) == ((2025, 7), (2025, 12))
    # luna trecută încă neaprobată: tot 3 luni de salariu, până la ultima lună aprobată
    assert salary_period({"months": "3"}, today=date(2026, 5, 20), last_paid=(2026, 3)) == ((2026, 1), (2026, 3))
    assert salary_period({"from": "2026-01", "to": "2026-04"}, last_paid=(2026, 3)) == ((2026, 1), (2026, 4))  # intervalul ales rămâne
    assert admin_client.get(url, {"doc": "certificate_salary", "from": "2026-05", "to": "2026-03"}).status_code == 400
    # salariul îl vede doar cine are salarizarea
    hr = make_user("insp", ["hr_inspector"])
    assert client_for(hr).get(url, {"doc": "certificate_salary"}).status_code == 403
