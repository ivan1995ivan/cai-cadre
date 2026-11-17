"""Aranjarea pentru toți (formele): o pune cine are dreptul de setări, o citește oricine; a utilizatorului rămâne separată."""


def test_layout_for_everyone(admin_client, make_user, client_for):
    layout = {"type": "group", "id": "root", "direction": "vertical", "children": []}
    assert admin_client.put("/api/ui-defaults/layout:employee/", {"value": layout}, format="json").status_code == 200

    head = client_for(make_user("sef", ["department_head"]))
    assert head.get("/api/ui-defaults/").json() == {"layout:employee": layout}
    # fără dreptul de setări nu se schimbă pentru toți
    assert head.put("/api/ui-defaults/layout:employee/", {"value": {}}, format="json").status_code == 403
    assert head.delete("/api/ui-defaults/layout:employee/").status_code == 403
    # aranjarea proprie nu atinge pe cea pentru toți
    head.put("/api/ui-prefs/layout:employee/", {"value": {"mine": True}}, format="json")
    assert head.get("/api/ui-defaults/layout:employee/").json() == layout

    assert admin_client.delete("/api/ui-defaults/layout:employee/").status_code == 204
    assert head.get("/api/ui-defaults/").json() == {}


def test_layout_for_everyone_size_limit(admin_client):
    r = admin_client.put("/api/ui-defaults/layout:x/", {"value": {"t": "x" * 30000}}, format="json")
    assert r.status_code == 400
