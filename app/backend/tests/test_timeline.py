"""Cronologia angajatului și documentele legate de ordin (fișa angajatului, ordinul)."""
from .test_orders import cancel, hired, make_order, org, set_params, sign  # noqa: F401 — fixtura și ajutoarele comune


def test_timeline_and_related(admin_client, make_user, client_for, org):  # noqa: F811
    a = hired(org)
    order = make_order(admin_client, "leave_annual", [a])
    set_params(admin_client, order, {"date_from": "2026-04-27", "days": 28, "work_year_from": "2025-01-01",
                                     "work_year_to": "2025-12-31"})
    sign(admin_client, order)
    rel = admin_client.get(f"/api/orders/orders/{order['id']}/related/").data
    assert [r["kind"] for r in rel["made"]] == ["absence"] and "27.04.2026 – 26.05.2026" in rel["made"][0]["detail"]
    assert rel["made"][0]["employee"] == a.full_name()
    # anularea: ordinul vechi arată cine l-a anulat, cel nou — pe cine anulează
    new = cancel(admin_client, order)
    old = admin_client.get(f"/api/orders/orders/{order['id']}/related/").data
    assert any(r["kind"] == "cancelled_by" and r["link"] == f"/orders/{new['id']}" for r in old["made"])
    assert admin_client.get(f"/api/orders/orders/{new['id']}/related/").data["sources"][0]["kind"] == "cancels"
    # cronologia: istoria raportului, ordinele, absența — cele mai noi sus
    tl = admin_client.get(f"/api/staff/employees/{a.id}/timeline/").json()
    kinds = [e["kind"] for e in tl]
    assert {"job", "order"} <= set(kinds)
    assert [e["date"] for e in tl] == sorted((e["date"] for e in tl), reverse=True)
    hire = next(e for e in tl if e["kind"] == "job")
    assert "salariul" in hire["detail"]
    assert any(e["kind"] == "order" and e["link"] == f"/orders/{order['id']}" for e in tl)
    # fără dreptul la ordine — fără ordine în cronologie
    viewer = make_user("vede", [])
    from apps.users.models import Permission, Role

    role = Role.objects.create(code="doar_angajati", name_ro="Doar angajații", data_scopes={"employees": "all"})
    role.permissions.set(Permission.objects.filter(code="employees.view"))
    viewer.roles.add(role)
    got = client_for(type(viewer).objects.get(pk=viewer.pk)).get(f"/api/staff/employees/{a.id}/timeline/").json()
    assert got and {e["kind"] for e in got} == {"job"}
