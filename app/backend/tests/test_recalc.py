"""Recalcularea cu comparație: încercarea nu scrie nimic, arată angajații cu schimbări (vechi / nou, rândurile pe tipuri), iar
aplicarea recalculează doar angajații aleși."""
from decimal import Decimal

from apps.payroll import engine
from apps.payroll.models import Payroll, PayrollLine

from .test_payroll import org, person  # noqa: F401 — fixtura și ajutorul comun


def test_preview_and_apply_selected(admin_client, org):  # noqa: F811
    a, ja = person(org, "Albu", "Ana", salary="10000")
    b, jb = person(org, "Botnaru", "Ion", salary="12000")
    doc = Payroll.objects.create(year=2026, month=3)
    engine.calculate(doc)
    old_a = PayrollLine.objects.get(payroll=doc, employee=a).gross
    old_b = PayrollLine.objects.get(payroll=doc, employee=b).gross
    # salariul s-a schimbat la amândoi după calcul
    for job, salary in ((ja, "11000"), (jb, "13000")):
        job.base_salary = Decimal(salary)
        job.save(update_fields=["base_salary"])
    r = admin_client.post(f"/api/payroll/payrolls/{doc.id}/preview/")
    assert r.status_code == 200, r.data
    rows = {x["name"]: x for x in r.data["rows"]}
    assert set(rows) == {"Albu Ana", "Botnaru Ion"}
    ra = rows["Albu Ana"]
    assert ra["status"] == "changed" and ra["old_gross"] == float(old_a) and ra["new_gross"] > ra["old_gross"]
    assert any(i["code"] == "SAL" and i["old"] == 10000 and i["new"] == 11000 for i in ra["items"]) and ra["diff_net"] > 0
    # încercarea n-a scris nimic
    assert PayrollLine.objects.get(payroll=doc, employee=a).gross == old_a
    # aplicarea doar pentru Albu
    assert admin_client.post(f"/api/payroll/payrolls/{doc.id}/apply/", {"employees": [a.id]}, format="json").status_code == 200
    assert PayrollLine.objects.get(payroll=doc, employee=a).gross > old_a
    assert PayrollLine.objects.get(payroll=doc, employee=b).gross == old_b
    left = admin_client.post(f"/api/payroll/payrolls/{doc.id}/preview/").data["rows"]
    assert [x["name"] for x in left] == ["Botnaru Ion"]
    assert admin_client.post(f"/api/payroll/payrolls/{doc.id}/apply/", {"employees": []}, format="json").status_code == 400
    # calculul aprobat nu se încearcă
    doc.status = "approved"
    doc.save()
    assert admin_client.post(f"/api/payroll/payrolls/{doc.id}/preview/").status_code == 400
