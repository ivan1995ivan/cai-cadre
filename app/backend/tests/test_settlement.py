"""Fișa decontărilor cu angajatul: soldul inițial, calculele și plățile cu soldul după fiecare, soldul final, concluzia, legăturile
spre documente; același sold ca în datoriile salariale (înainte de impozit și CNAM)."""
from decimal import Decimal

from apps.payroll.payments import debts

from .test_payroll import org, person  # noqa: F401 — fixtura și ajutorul comun
from .test_payroll_payments import approved_payroll, paid_salary


def report(api, emp, date_from, date_to, **extra):
    r = api.get("/api/reports/employee_settlement/", {"employee": emp.id, "date_from": date_from, "date_to": date_to, **extra})
    assert r.status_code == 200, r.data
    return r.json()


def test_statement(admin_client, org):  # noqa: F811
    e, _job = person(org, "Popescu", "Ion")
    march = approved_payroll(3)
    data = report(admin_client, e, "2026-03-01", "2026-03-31")
    owed = float(sum((ln.gross - ln.deductions for ln in march.lines.filter(employee=e)), Decimal("0")))
    assert data["rows"][0]["_subtotal"] and data["rows"][0]["balance"] == 0
    row = data["rows"][1]
    assert row["owed"] == owed and row["balance"] == owed and row["_link"] == f"/payroll/{march.pk}" and row["date"] == "2026-03-31"
    assert data["totals"]["balance"] == owed and "datorează lui Popescu Ion" in data["conclusion"]
    paid_salary(admin_client, 3, "2026-04-05")
    # aprilie: soldul inițial = martie, plata îl închide
    april = report(admin_client, e, "2026-04-01", "2026-04-30")
    assert april["rows"][0]["balance"] == owed and april["rows"][1]["paid"] == owed and april["rows"][1]["_link"].startswith("/payroll/payments/")
    assert april["totals"]["balance"] == 0 and "sunt închise" in april["conclusion"]
    # aceeași bază ca datoriile salariale: după plată — închise și acolo
    assert e.pk not in {d["employee"] for d in debts(2026, 4)}
    # fără angajat / angajat străin — eroare; în rusă
    assert admin_client.get("/api/reports/employee_settlement/", {"date_from": "2026-03-01", "date_to": "2026-03-31"}).status_code == 400
    assert "закрыты" in report(admin_client, e, "2026-04-01", "2026-04-30", lang="ru")["conclusion"]
    # tiparul și Excel
    assert admin_client.get("/api/reports/employee_settlement/print/", {"employee": e.id, "date_from": "2026-03-01",
                                                                       "date_to": "2026-03-31"}).status_code == 200
    x = admin_client.get("/api/reports/employee_settlement/", {"employee": e.id, "date_from": "2026-03-01", "date_to": "2026-03-31",
                                                              "export": "xlsx"})
    assert x.status_code == 200
