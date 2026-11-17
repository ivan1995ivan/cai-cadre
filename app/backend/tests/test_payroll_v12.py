"""Versiunea 1.2: corectările de mână în calcul, impozitul reținut la achitare cu corectarea rândului din îndreptarea spre
plată, IPC21 și fișa anexa 8 din plăți, fluturașii în PDF și pe e-mail (ZIP cu parolă), cartea privind salariul."""
import io
import zipfile
from decimal import Decimal

import pytest
from django.core import mail as django_mail
from django.core.mail import get_connection

from apps.payroll import engine
from apps.payroll.models import Payment, PaymentLine, Payroll, PayslipDispatch, PayType

from .test_payroll import items_of, org, person  # noqa: F401 — fixtura și ajutoarele comune
from .test_payroll_payments import approved_payroll


def _type(code):
    return PayType.objects.get(code=code).id


def test_manual_amount_replaces_calculated_and_taxes_follow(admin_client, org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion")
    doc = Payroll.objects.create(year=2026, month=3)
    engine.calculate(doc)
    line = doc.lines.get()
    gross_before = line.gross
    # salariul de funcție corectat de mână: înlocuiește rândul calculat, nu se adaugă
    r = admin_client.post("/api/payroll/items/", {"line": line.id, "pay_type": _type("SAL"), "amount": "10000"}, format="json")
    assert r.status_code == 201, r.data
    line.refresh_from_db()
    sal = [i for i in line.items.select_related("pay_type") if i.pay_type.code == "SAL"]
    assert len(sal) == 1 and sal[0].manual and sal[0].amount == Decimal("10000")
    assert line.gross == gross_before - Decimal("14660") + Decimal("10000")
    assert line.taxable == line.cnam_base == line.gross and line.net == line.gross  # bazele urmează corectarea
    # aceeași corectare a doua oară schimbă suma, nu adaugă un rând
    admin_client.post("/api/payroll/items/", {"line": line.id, "pay_type": _type("SAL"), "amount": "11000"}, format="json")
    line.refresh_from_db()
    assert line.items.filter(pay_type__code="SAL").count() == 1 and line.gross == gross_before - Decimal("3660")
    # impozitul și CNAM nu se scriu în calcul — se rețin la plată
    for code in ("IMPOZIT", "CNAM"):
        r = admin_client.post("/api/payroll/items/", {"line": line.id, "pay_type": _type(code), "amount": "500"}, format="json")
        assert r.status_code == 400, code
    # recalcularea întregului calcul păstrează corectările
    engine.calculate(doc)
    line.refresh_from_db()
    assert line.gross == gross_before - Decimal("3660")
    # ștergerea corectării întoarce suma calculată
    manual = line.items.get(pay_type__code="SAL", manual=True)
    assert admin_client.delete(f"/api/payroll/items/{manual.id}/").status_code == 204
    line.refresh_from_db()
    assert line.gross == gross_before and line.items.get(pay_type__code="SAL").amount == Decimal("14660")
    # alt angajat nu e atins de recalcularea unui singur angajat
    assert doc.lines.count() == 1


def test_payment_line_corrections_recalculate_taxes(admin_client, org):  # noqa: F811
    person(org, "Popescu", "Ion")
    r = admin_client.post("/api/payroll/payments/", {"year": 2026, "month": 3, "kind": "advance"}, format="json")
    line = Payment.objects.get(pk=r.data["id"]).lines.get()
    # brutul → impozitele se refac
    d = admin_client.patch(f"/api/payroll/payment-lines/{line.id}/", {"gross": "5000"}, format="json").data
    assert (d["gross"], d["cnam"], d["income_tax"], d["amount"]) == ("5000.00", "450.00", "546.00", "4004.00") and d["manual"]
    # netul → brutul care dă exact acest net
    d = admin_client.patch(f"/api/payroll/payment-lines/{line.id}/", {"amount": "4000"}, format="json").data
    assert d["amount"] == "4000.00"
    g, c, t = Decimal(d["gross"]), Decimal(d["cnam"]), Decimal(d["income_tax"])
    assert g - c - t == Decimal("4000") and abs(c - g * Decimal("0.09")) <= Decimal("0.02")
    # impozitul scris direct → doar netul se reface
    d = admin_client.patch(f"/api/payroll/payment-lines/{line.id}/", {"income_tax": "0"}, format="json").data
    assert d["income_tax"] == "0.00" and Decimal(d["amount"]) == g - c
    assert admin_client.patch(f"/api/payroll/payment-lines/{line.id}/", {"gross": "-5"}, format="json").status_code == 400


def test_ipc21_and_annual_card_follow_payments(admin_client, org):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion")
    ion.idnp = "2001000123456"
    ion.save()
    approved_payroll(3)
    # fără îndreptări achitate: tabelul 2 (baza CAS) din calcul, tabelul 1 (venitul achitat, impozitul reținut) gol
    ipc = admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 3}).data
    assert ipc["total"]["persons"] == 1 and ipc["total"]["cas"] > 0
    assert ipc["table1"] == {"income": 0.0, "tax": 0.0, "cnam": 0.0}
    assert admin_client.get(f"/api/payroll/annual-card/{ion.id}/", {"year": 2026}).data["rows"] == []
    r = admin_client.post("/api/payroll/payments/", {"year": 2026, "month": 3, "kind": "salary"}, format="json")
    pay = Payment.objects.get(pk=r.data["id"])
    admin_client.post(f"/api/payroll/payments/{pay.id}/approve/")
    admin_client.post(f"/api/payroll/payments/{pay.id}/pay/", {"paid_on": "2026-04-05"}, format="json")
    ln = pay.lines.get()
    # achitat în aprilie: tabelul 1 din aprilie are venitul și impozitul plății; martie rămâne pe calcul
    april = admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 4}).data
    assert april["table1"] == {"income": float(ln.gross), "tax": float(ln.income_tax), "cnam": float(ln.cnam)}
    march = admin_client.get("/api/payroll/tax-reports/ipc21/", {"year": 2026, "month": 3}).data
    assert march["table1"]["income"] == 0 and march["total"]["persons"] == 1
    card = admin_client.get(f"/api/payroll/annual-card/{ion.id}/", {"year": 2026}).data
    assert [r["date"] for r in card["rows"]] == ["05.04.2026"]
    assert card["rows"][0]["tax"] == float(ln.income_tax) and card["hired"] == "01.01.2020"
    html = admin_client.get(f"/api/payroll/annual-card/{ion.id}/", {"year": 2026, "print": 1}).content.decode()
    assert "05.04.2026" in html and "Data plății" in html and "2001000123456" in html


def test_payslips_pdf_and_mail_with_password_zip(admin_client, org, monkeypatch, settings):  # noqa: F811
    ion, _ = person(org, "Popescu", "Ion")
    ion.idnp, ion.email = "2001000123456", "ion@spital.md"
    ion.save()
    ana, _ = person(org, "Rusu", "Ana", occ="nurse", salary="9200")  # fără e-mail
    doc = Payroll.objects.create(year=2026, month=3)
    engine.calculate(doc)
    doc.status = "approved"
    doc.save()
    r = admin_client.post("/api/payroll/payments/", {"payroll": doc.id, "kind": "salary", "date": "2026-04-05"}, format="json")
    pay = Payment.objects.get(pk=r.data["id"])
    base = f"/api/payroll/payments/{pay.id}"
    pdf = admin_client.get(f"{base}/payslip-pdf/")
    assert pdf.status_code == 200 and pdf["Content-Type"] == "application/pdf" and pdf.content[:5] == b"%PDF-"
    # din avans nu se fac fluturași; se trimit doar din îndreptarea aprobată
    adv = admin_client.post("/api/payroll/payments/", {"year": 2026, "month": 3, "kind": "advance"}, format="json").data["id"]
    assert admin_client.get(f"/api/payroll/payments/{adv}/payslip-pdf/").status_code == 400
    assert admin_client.post(f"{base}/payslip-mail/", {"employees": [ion.id]}, format="json").status_code == 400
    admin_client.post(f"{base}/approve/")
    # fără SMTP configurat — mesaj clar
    r = admin_client.post(f"{base}/payslip-mail/", {"employees": [ion.id]}, format="json")
    assert r.status_code == 400 and "E-mailul nu e configurat" in str(r.data)
    from apps.alerts import mail

    monkeypatch.setattr(mail, "connection", lambda: (get_connection("django.core.mail.backends.locmem.EmailBackend"),
                                                     {"from_email": "cadre@spital.md", "username": ""}))
    summary = admin_client.get(f"{base}/payslip-mail/").data
    assert summary["ready"] == 1 and summary["smtp"]
    assert {r["name"]: r["problem"] for r in summary["rows"]} == {"Popescu Ion": "", "Rusu Ana": "fără e-mail"}
    r = admin_client.post(f"{base}/payslip-mail/", {"employees": [ion.id, ana.id]}, format="json")
    assert [x["status"] for x in r.data["results"]] == ["sent", "skipped"]
    assert len(django_mail.outbox) == 1
    msg = django_mail.outbox[0]
    assert msg.to == ["ion@spital.md"] and "ultimele 5 cifre" in msg.body
    name, content, mimetype = msg.attachments[0]
    assert name == f"fluturas-2026-03-{ion.tab_number}.zip" and mimetype == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(content))
    with pytest.raises(RuntimeError):
        z.read(z.namelist()[0])  # fără parolă nu se deschide
    assert z.read(z.namelist()[0], pwd=b"23456")[:5] == b"%PDF-"
    assert PayslipDispatch.objects.filter(payment=pay).count() == 2
    last = {r["name"]: r["last"]["status"] for r in admin_client.get(f"{base}/payslip-mail/").data["rows"]}
    assert last == {"Popescu Ion": "sent", "Rusu Ana": "skipped"}


def test_salary_book_report(admin_client, org):  # noqa: F811
    person(org, "Popescu", "Ion")
    person(org, "Rusu", "Ana", occ="nurse", salary="9200")
    approved_payroll(3)
    approved_payroll(4)
    one = admin_client.get("/api/reports/salary_book/", {"date_from": "2026-03-01", "date_to": "2026-03-31"}).data
    titles = [c["title"] for c in one["columns"]]
    assert "Salariul de funcție" in " ".join(titles) and "Total calculat" in titles and "De plată" in titles
    rows = {r["name"]: r for r in one["rows"]}
    assert rows["Popescu Ion"]["gross"] > 0 and rows["Popescu Ion"]["net"] == pytest.approx(
        rows["Popescu Ion"]["gross"] - rows["Popescu Ion"]["withheld"])
    assert one["totals"]["gross"] == pytest.approx(sum(r["gross"] for r in one["rows"]))
    two = admin_client.get("/api/reports/salary_book/", {"date_from": "2026-03-01", "date_to": "2026-04-30"}).data
    assert {"_section": "Popescu Ion · " + Payroll.objects.first().lines.get(employee__last_name="Popescu").employee.tab_number} in two["rows"]
    assert any(r.get("name") == "martie 2026" for r in two["rows"]) and any(r.get("_subtotal") for r in two["rows"])
    html = admin_client.get("/api/reports/salary_book/print/", {"date_from": "2026-03-01", "date_to": "2026-03-31"}).content.decode()
    assert "FIȘA DE EVIDENȚĂ A RETRIBUȚIEI" in html and "Contabil-șef" in html and "Conducătorul" in html
