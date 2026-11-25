"""Împărțirea primei colective pe punctele ordinului de stimulare: egal, după salariu, după ore; rotunjirea fără rest."""
from decimal import Decimal

from apps.orders.distribute import split

from .test_orders import hired, make_order, org  # noqa: F401 — fixtura și ajutoarele comune


def test_split_rounding_without_remainder():
    parts = split(Decimal("100"), [Decimal("1")] * 3)
    assert parts == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")] and sum(parts) == Decimal("100")
    assert sum(split(Decimal("1000"), [Decimal("12000"), Decimal("8000"), Decimal("5000")])) == Decimal("1000")


def test_distribute_in_bonus_order(admin_client, org):  # noqa: F811
    a = hired(org, "Albu", "Ana")
    b = hired(org, "Botnaru", "Ion")
    order = make_order(admin_client, "bonus", [a, b])
    url = f"/api/orders/orders/{order['id']}/distribute/"
    r = admin_client.post(url, {"total": "3000", "method": "equal"}, format="json")
    assert r.status_code == 200, r.data
    assert [x["amount"] for x in r.data["rows"]] == [1500.0, 1500.0]
    jobs = {x.employee_id: x for x in (a.main_employment(), b.main_employment())}
    jobs[a.pk].base_salary = Decimal("10000")
    jobs[a.pk].save(update_fields=["base_salary"])
    jobs[b.pk].base_salary = Decimal("20000")
    jobs[b.pk].save(update_fields=["base_salary"])
    by = {x["name"]: x["amount"] for x in admin_client.post(url, {"total": "3000", "method": "salary"}, format="json").data["rows"]}
    assert by == {"Albu Ana": 1000.0, "Botnaru Ion": 2000.0}
    # după ore: fără pontaj — nimic de împărțit; fără lună — eroare
    assert admin_client.post(url, {"total": "3000", "method": "hours"}, format="json").status_code == 400
    assert admin_client.post(url, {"total": "3000", "method": "hours", "year": 2026, "month": 3}, format="json").status_code == 400
    assert admin_client.post(url, {"total": "-1", "method": "equal"}, format="json").status_code == 400
    other = make_order(admin_client, "leave_annual", [a])
    assert admin_client.post(f"/api/orders/orders/{other['id']}/distribute/", {"total": "1", "method": "equal"},
                             format="json").status_code == 400
