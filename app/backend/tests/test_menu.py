"""Meniul principal pe grupe (Registre / Rapoarte): salvarea, așezarea veche ignorată, sus / în stânga păstrat; trecerea la
Administrare → Setări (1.4.0) a meniului salvat, a bifelor rolurilor și a favoritelor."""
import importlib
import re
from pathlib import Path

from apps.core.models import SystemSetting
from apps.org.models import DictItem
from apps.users.models import Role


def test_menu_groups_saved(admin_client):
    sections = [{"key": "salarii", "name_ro": "", "name_ru": "", "icon": "wallet",
                 "items": ["payroll", "payroll"], "reports": ["taxReports"]}]
    r = admin_client.put("/api/settings/menu/", {"sections": sections}, format="json")
    assert r.status_code == 200, r.content
    saved = admin_client.get("/api/settings/menu/").json()
    assert saved["version"] == 2
    sec = saved["sections"][0]
    assert sec["items"] == ["payroll"]  # într-o grupă o funcție stă o singură dată
    assert sec["reports"] == ["taxReports"]


def test_settings_group_from_old_editor(admin_client):
    """Setările stau toate la Administrare → Setări: editorul rămas pe programul vechi trimite și grupa „settings” — setările
    ies din secțiune, celelalte funcții din ea trec la Registre, rapoartele la Rapoarte; denumirile rămân."""
    sections = [{"key": "salarii", "name_ro": "Salariul", "icon": "wallet", "items": ["payroll", "constants"], "reports": [],
                 "settings": ["payrollSettings", "excelImport", "repSalaryBook", "payroll"]}]
    assert admin_client.put("/api/settings/menu/", {"sections": sections}, format="json").status_code == 200
    sec = admin_client.get("/api/settings/menu/").json()["sections"][0]
    assert sec == {"key": "salarii", "name_ro": "Salariul", "name_ru": "", "icon": "wallet",
                   "items": ["payroll", "excelImport"], "reports": ["repSalaryBook"]}
    bad = admin_client.put("/api/settings/menu/", {"sections": ["salarii"]}, format="json")
    assert bad.status_code == 400


def _upgrade():
    from django.apps import apps

    importlib.import_module("apps.users.migrations.0004_settings_moved").settings_moved(apps, None)


def test_upgrade_moves_saved_menu_roles_and_favorites(admin_user, make_user):
    """Migrația 1.4.0: meniul salvat, bifele rolurilor și favoritele trec pe cheile și adresele noi, o singură dată; rolul vede
    după actualizare ce vedea înainte."""
    SystemSetting.write("menu_layout", {"version": 2, "layout": "left", "sections": [
        {"key": "institutia", "name_ro": "", "name_ru": "", "icon": "org", "items": ["org", "dictionaries"],
         "reports": ["repVacancies"], "settings": ["constants", "excelImport"]},
        {"key": "administrare", "name_ro": "", "name_ru": "", "icon": "admin", "items": ["users", "audit"], "reports": [],
         "settings": ["mainMenu", "repMunca1"]},
    ]})
    role = Role.objects.get(code="hr_inspector")
    role.menu_hidden = ["dictionaries", "leave", "users", "s:salarii"]
    role.save()
    admin_user.favorites = [
        {"path": "/payroll/settings", "key": "payrollSettings", "title": ""},
        {"path": "/dictionaries", "key": "dictionaries", "title": ""},
        {"path": "/dictionaries/other", "key": "", "title": "Clasificatoare · #other"},
        {"path": "/dictionaries/legal", "key": "", "title": "Clasificatoare · #legal"},
        {"path": "/admin/users", "key": "users", "title": ""},
    ]
    admin_user.save()
    _upgrade()
    layout = SystemSetting.read("menu_layout")
    assert layout["layout"] == "left"
    assert [(s["items"], s["reports"]) for s in layout["sections"]] == [
        (["org", "excelImport"], ["repVacancies"]), (["audit"], ["repMunca1"])]
    assert all("settings" not in s for s in layout["sections"])
    role.refresh_from_db()
    assert role.menu_hidden[:4] == ["occupations", "specialties", "legalBases", "orderTypes"]
    assert {"dict:vaccine", "dict:education_form", "leave", "leaveSettings", "users", "s:salarii"} <= set(role.menu_hidden)
    assert len(role.menu_hidden) == len(set(role.menu_hidden)) == 4 + 18 + 4
    admin_user.refresh_from_db()
    assert admin_user.favorites == [
        {"path": "/payroll/settings/types", "key": "payrollTypes", "title": ""},
        {"path": "/settings", "key": "settings", "title": ""},
        {"path": "/dictionaries/legal", "key": "legalBases", "title": ""},
        {"path": "/admin/users", "key": "users", "title": ""},
    ]
    before = (SystemSetting.read("menu_layout"), role.menu_hidden, admin_user.favorites)
    _upgrade()  # a doua oară nu mai schimbă nimic
    role.refresh_from_db()
    admin_user.refresh_from_db()
    assert (SystemSetting.read("menu_layout"), role.menu_hidden, admin_user.favorites) == before


def test_old_keys_normalized_on_save(admin_client):
    """Ce trimite programul vechi rămas deschis în browser se salvează pe cheile noi. Registrul ascuns nu-și mai ia setările
    (după 1.4.0 se bifează separat) — asta face doar migrația."""
    me = admin_client.patch("/api/auth/me/", {"favorites": [{"path": "/worktime", "key": "worktime", "title": "Timp de muncă"}]},
                            format="json")
    assert me.status_code == 200 and me.data["favorites"] == [{"path": "/worktime/schedules", "key": "workSchedules", "title": ""}]
    role = Role.objects.get(code="hr_inspector")
    r = admin_client.patch(f"/api/roles/{role.id}/", {"menu_hidden": ["payrollSettings", "leave"]}, format="json")
    assert r.status_code == 200 and r.data["menu_hidden"] == ["payrollTypes", "payrollConstants", "leave"]


def test_dictionary_settings_match_frontend():
    """Fiecare clasificator mic (DictItem.KINDS) are setarea lui în interfață (DICT_KINDS din layout/nav.tsx)."""
    nav = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "layout" / "nav.tsx").read_text(encoding="utf-8")
    listed = re.findall(r"'([a-z_]+)'", re.search(r"export const DICT_KINDS = \[(.*?)\]", nav, re.S).group(1))
    assert listed == [code for code, _ in DictItem.KINDS]


def test_old_menu_ignored_layout_kept(admin_client):
    SystemSetting.write("menu_layout", {"sections": [{"key": "x", "items": ["payroll"]}], "layout": "left"})
    assert admin_client.get("/api/settings/menu/").json() == {"layout": "left"}
    # schimbarea așezării nu readuce secțiunile vechi
    admin_client.put("/api/settings/menu/", {"layout": "top"}, format="json")
    assert admin_client.get("/api/settings/menu/").json() == {"layout": "top"}


def test_layout_change_keeps_sections(admin_client):
    sections = [{"key": "principal", "icon": "home", "items": ["dashboard"], "reports": []}]
    admin_client.put("/api/settings/menu/", {"sections": sections}, format="json")
    admin_client.put("/api/settings/menu/", {"layout": "left"}, format="json")
    saved = admin_client.get("/api/settings/menu/").json()
    assert saved["layout"] == "left" and saved["sections"][0]["items"] == ["dashboard"]


def test_function_panel_switch(admin_client):
    """Panoul funcțiilor (Constante → Module): oprit implicit, se pornește din constante și ajunge în branding (interfața își
    schimbă așezarea după el)."""
    from rest_framework.test import APIClient

    public = APIClient()
    assert public.get("/api/public/branding/").data["function_panel"] is False
    r = admin_client.patch("/api/company/", {"function_panel": True}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["function_panel"] is True
    assert public.get("/api/public/branding/").data["function_panel"] is True


def test_function_panel_keys_exist():
    """Cheile panoului (PANEL_KIND, PANEL_FLOWS, PANEL_CLASSIFIERS din layout/nav.tsx) sunt funcții și setări care există:
    o greșeală de scriere ar scoate în tăcere un document sau un clasificator din panou."""
    nav = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "layout" / "nav.tsx").read_text(encoding="utf-8")

    def block(name):
        return re.search(rf"export const {name}[^=]*= [\[{{](.*?)\n[\]}}]", nav, re.S).group(1)

    keys = set(re.findall(r"key: '([A-Za-z:_]+)'", nav)) | set(re.findall(r"report\('([A-Za-z]+)'", nav))
    dict_kinds = re.findall(r"'([a-z_]+)'", re.search(r"export const DICT_KINDS = \[(.*?)\]", nav, re.S).group(1))
    settings = set(re.findall(r"key: '([A-Za-z]+)'", block("SETTINGS_NAV"))) | {f"dict:{k}" for k in dict_kinds}
    functions = keys - settings

    kinds = dict(re.findall(r"(\w+): '(start|doc)'", block("PANEL_KIND")))
    assert kinds and set(kinds) <= functions
    flows = re.findall(r"\['(\w+)', '(\w+)'\]", block("PANEL_FLOWS"))
    assert flows and all(a in kinds and b in kinds for a, b in flows)
    classifiers = block("PANEL_CLASSIFIERS")
    owners = re.findall(r"^\s+(\w+): \[", classifiers, re.M)
    used = set(re.findall(r"'([a-z:_A-Z]+)'", classifiers))
    assert owners and set(owners) <= functions
    assert used and used <= settings, used - settings
