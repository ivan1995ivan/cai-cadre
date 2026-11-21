"""Etapa 1: clasificatoarele, subdiviziunile, statele de personal (versiuni, ocupare), importul din Excel, tiparul."""
import io
from decimal import Decimal

import pytest
from openpyxl import Workbook, load_workbook

from apps.org import seed as org_seed
from apps.org import services
from apps.org.models import (DictItem, LegalBasis, Occupation, OrderType, Specialty, StaffList, StaffListLine,
                             Subdivision)


def xlsx(rows):
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = "date.xlsx"
    return buf


@pytest.fixture
def subs(seeded):
    hosp = Subdivision.objects.create(code="ADM", name_ro="Administrația", kind="admin", sort=1)
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1", kind="clinical", beds=40, sort=10)
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția anestezie și terapie intensivă", kind="clinical",
                                     harmful=True, extra_leave_days=7, sort=20)
    return {"adm": hosp, "tr1": tr1, "ati": ati}


@pytest.fixture
def occ(seeded):
    doctor = Occupation.objects.get(name_ro="Medic traumatolog-ortoped")
    nurse = Occupation.objects.get(name_ro="Asistent medical de secție")
    director = Occupation.objects.get(name_ro="Director")
    return {"doctor": doctor, "nurse": nurse, "director": director}


def make_list(subs, occ, effective="2026-01-01"):
    sl = StaffList.objects.create(number="1", effective_from=effective, approved_by="Ordinul MS nr. 1")
    StaffListLine.objects.create(staff_list=sl, subdivision=subs["adm"], occupation=occ["director"], units=1,
                                 base_salary=Decimal("20000"))
    StaffListLine.objects.create(staff_list=sl, subdivision=subs["tr1"], occupation=occ["doctor"], units=Decimal("4.5"),
                                 base_salary=Decimal("14660"), allowance_pct=Decimal("10"))
    StaffListLine.objects.create(staff_list=sl, subdivision=subs["tr1"], occupation=occ["nurse"], units=Decimal("9.25"),
                                 base_salary=Decimal("9000"))
    return sl


# --- datele inițiale -----------------------------------------------------------------
def test_seed_has_all_reference_data_and_is_idempotent(seeded):
    counts = (Occupation.objects.count(), Specialty.objects.count(), DictItem.objects.count(), LegalBasis.objects.count(),
              OrderType.objects.count())
    assert OrderType.objects.count() >= 40
    assert OrderType.objects.filter(from_1c=True).count() >= 15  # ordinele care existau în 1C
    assert set(OrderType.objects.values_list("group", flat=True)) == set("ABCDEFG")
    assert OrderType.objects.get(code="leave_annual").legal_bases.get().reference() == "art. 112 din Codul muncii nr. 154/2003"
    assert DictItem.objects.filter(kind="employment", code="internal").exists()
    assert Occupation.objects.get(code="221104").category == "physicians"
    org_seed.run()
    org_seed.run()
    assert counts == (Occupation.objects.count(), Specialty.objects.count(), DictItem.objects.count(),
                      LegalBasis.objects.count(), OrderType.objects.count())


def test_seed_keeps_user_changes(seeded):
    ot = OrderType.objects.get(code="hire")
    ot.name_ro = "Angajare (modificat)"
    ot.save()
    org_seed.run()
    assert OrderType.objects.get(code="hire").name_ro == "Angajare (modificat)"


# --- drepturile -------------------------------------------------------------------------
def test_dictionaries_crud_and_permissions(admin_client, make_user, client_for):
    r = admin_client.post("/api/org/occupations/", {"code": "999999", "name_ro": "Test funcție", "category": "nurses"},
                          format="json")
    assert r.status_code == 201, r.data
    dup = admin_client.post("/api/org/occupations/", {"code": "999999", "name_ro": "Alta"}, format="json")
    assert dup.status_code == 400
    head = client_for(make_user("sef", ["department_head"]))
    assert head.get("/api/org/occupations/").status_code == 403  # șeful de secție nu vede clasificatoarele
    inspector = client_for(make_user("insp", ["hr_inspector"]))
    assert inspector.get("/api/org/occupations/").status_code == 200
    assert inspector.delete(f"/api/org/occupations/{r.data['id']}/").status_code == 403
    found = admin_client.get("/api/org/occupations/", {"q": "traumatolog"}).data
    assert [o["name_ro"] for o in found] == ["Medic traumatolog-ortoped"]


def test_meta_lists_enums(admin_client):
    data = admin_client.get("/api/org/meta/").data
    assert "physicians" in data["categories"] and "hire" in data["order_effects"]
    assert {i["code"] for i in data["imports"]} == {"occupations", "specialties", "subdivisions", "staff_lines"}


# --- subdiviziunile ----------------------------------------------------------------------
def test_subdivision_tree_cycle_and_protected_delete(admin_client, subs, occ):
    child = admin_client.post("/api/org/subdivisions/", {"name_ro": "Salonul de reanimare", "parent": subs["ati"].id},
                              format="json")
    assert child.status_code == 201
    tree = admin_client.get("/api/org/subdivisions/", {"tree": "1"}).data
    ati = next(n for n in tree if n["code"] == "ATI")
    assert ati["children"][0]["name_ro"] == "Salonul de reanimare"
    cycle = admin_client.patch(f"/api/org/subdivisions/{subs['ati'].id}/", {"parent": child.data["id"]}, format="json")
    assert cycle.status_code == 400
    make_list(subs, occ)
    # „Șterge” doar marchează; ștergerea de tot (Administrare) nu atinge subdiviziunea folosită în state
    assert admin_client.delete(f"/api/org/subdivisions/{subs['tr1'].id}/").status_code == 204
    subs["tr1"].refresh_from_db()
    assert subs["tr1"].deletion_mark
    key = f"org.Subdivision:{subs['tr1'].id}"
    done = admin_client.post("/api/system/marked/delete/", {"keys": [key]}, format="json").data
    assert not done["deleted"] and done["blocked"][0]["refs"][0]["model"] == "org.StaffList"
    assert Subdivision.objects.filter(pk=subs["tr1"].id).exists()


# --- statele de personal ------------------------------------------------------------------
def test_staff_list_totals_by_category(subs, occ):
    sl = make_list(subs, occ)
    t = services.totals(sl)
    assert t["units"] == "14.75"
    cats = {c["code"]: c["units"] for c in t["categories"]}
    assert cats == {"leadership": "1.00", "physicians": "4.50", "nurses": "9.25"}
    # fondul: 20000 + 4.5 × 14660 × 1.10 + 9.25 × 9000
    assert Decimal(t["fund"]) == Decimal("20000") + Decimal("72567.00") + Decimal("83250.00")


def test_staff_list_lifecycle(admin_client, subs, occ):
    r = admin_client.post("/api/org/staff-lists/", {"number": "7", "effective_from": "2026-01-01",
                                                     "approved_by": "Decizia nr. 1"}, format="json")
    assert r.status_code == 201 and r.data["status"] == "draft"
    sl_id = r.data["id"]
    empty = admin_client.post(f"/api/org/staff-lists/{sl_id}/approve/")
    assert empty.status_code == 400  # fără rânduri nu se aprobă
    for occupation, units in ((occ["doctor"], "3"), (occ["nurse"], "6.5")):
        line = admin_client.post("/api/org/staff-list-lines/", {
            "staff_list": sl_id, "subdivision": subs["tr1"].id, "occupation": occupation.id, "units": units,
            "base_salary": "10000"}, format="json")
        assert line.status_code == 201, line.data
    bad = admin_client.post("/api/org/staff-list-lines/", {"staff_list": sl_id, "subdivision": subs["tr1"].id,
                                                            "occupation": occ["nurse"].id, "units": "0"}, format="json")
    assert bad.status_code == 400
    assert admin_client.post(f"/api/org/staff-lists/{sl_id}/approve/").data["status"] == "approved"
    # aprobat → nu se mai modifică
    line_id = StaffListLine.objects.filter(staff_list_id=sl_id).first().id
    assert admin_client.patch(f"/api/org/staff-list-lines/{line_id}/", {"units": "5"}, format="json").status_code == 400
    assert admin_client.patch(f"/api/org/staff-lists/{sl_id}/", {"number": "8"}, format="json").status_code == 400
    assert admin_client.delete(f"/api/org/staff-lists/{sl_id}/").status_code == 400
    # versiune nouă: copiază rândurile și se compară cu cea veche
    nv = admin_client.post(f"/api/org/staff-lists/{sl_id}/new-version/", {"effective_from": "2026-07-01"}, format="json")
    assert nv.status_code == 201 and nv.data["lines_count"] == 2 and nv.data["previous"] == sl_id
    new_id = nv.data["id"]
    nurse_line = StaffListLine.objects.get(staff_list_id=new_id, occupation=occ["nurse"])
    assert admin_client.patch(f"/api/org/staff-list-lines/{nurse_line.id}/", {"units": "7"}, format="json").status_code == 200
    admin_client.post("/api/org/staff-list-lines/", {"staff_list": new_id, "subdivision": subs["ati"].id,
                                                      "occupation": occ["doctor"].id, "units": "2"}, format="json")
    StaffListLine.objects.filter(staff_list_id=new_id, occupation=occ["doctor"], subdivision=subs["tr1"]).delete()
    changes = {(c["subdivision"], c["occupation"]): c["change"] for c in admin_client.get(f"/api/org/staff-lists/{new_id}/diff/").data}
    assert changes == {
        ("Secția traumatologie nr. 1", "Asistent medical de secție"): "changed",
        ("Secția traumatologie nr. 1", "Medic traumatolog-ortoped"): "removed",
        ("Secția anestezie și terapie intensivă", "Medic traumatolog-ortoped"): "added",
    }
    assert admin_client.post(f"/api/org/staff-lists/{new_id}/approve/").status_code == 200
    from datetime import date

    assert services.current(date(2026, 3, 1)).id == sl_id
    assert services.current(date(2026, 8, 1)).id == new_id


def test_two_approved_lists_cannot_share_the_date(subs, occ):
    a = make_list(subs, occ)
    services.approve(a)
    b = make_list(subs, occ)
    from rest_framework.exceptions import ValidationError

    with pytest.raises(ValidationError):
        services.approve(b)
    services.cancel(a)
    services.approve(b)


def test_occupancy_all_vacant_without_employees(admin_client, subs, occ):
    assert admin_client.get("/api/org/occupancy/").data["rows"] == []  # fără state aprobate
    services.approve(make_list(subs, occ))
    data = admin_client.get("/api/org/occupancy/").data
    assert data["totals"] == {"approved": "14.75", "occupied": "0", "temporary": "0", "vacant": "14.75"}
    assert data["employees_module"] is True  # modulul de angajați (Etapa 2) e înscris; încă nu e nimeni angajat
    row = next(r for r in data["rows"] if r["occupation"] == "Asistent medical de secție")
    assert row["vacant"] == "9.25" and row["over"] is False


def test_occupancy_uses_registered_provider(subs, occ, monkeypatch):
    sl = make_list(subs, occ)
    services.approve(sl)

    def provider(staff_list, on_date):
        return {(subs["tr1"].id, occ["doctor"].id): {"occupied": Decimal("5"), "temporary": Decimal("1"),
                                                      "holders": [{"name": "Ion Popescu", "units": "1", "kind": "main"}]}}

    monkeypatch.setattr(services, "OCCUPANCY_PROVIDERS", [provider])
    row = next(r for r in services.occupancy()["rows"] if r["occupation"] == "Medic traumatolog-ortoped")
    assert row["occupied"] == "5" and row["vacant"] == "-0.50" and row["over"] is True


# --- importul din Excel ---------------------------------------------------------------------
def test_import_template_is_excel(admin_client):
    r = admin_client.get("/api/org/import/occupations/template/")
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    header = [c.value for c in wb.worksheets[0][1]]
    assert header[0] == "Cod CORM" and header[1] == "Denumirea (RO) *"
    assert "Instrucțiuni" in wb.sheetnames


def test_import_occupations_dry_run_then_save(admin_client, seeded):
    before = Occupation.objects.count()
    data = [["Denumirea (RO)", "cod corm", "Categoria de personal", "Ore pe saptamana"],
            ["Medic ortoped pediatru", "221299", "physicians", "35"],
            ["Medic de familie", "221104", "", ""],  # există: se actualizează
            ["Funcție greșită", "", "nimic", ""]]
    dry = admin_client.post("/api/org/import/occupations/", {"file": xlsx(data), "dry_run": "1"}, format="multipart").data
    assert dry["created"] == 1 and dry["updated"] == 1 and dry["errors"][0]["row"] == 4
    assert Occupation.objects.count() == before  # încercarea nu scrie nimic
    fail = admin_client.post("/api/org/import/occupations/", {"file": xlsx(data), "dry_run": "0"}, format="multipart").data
    assert fail["saved"] is False and Occupation.objects.count() == before  # cu erori nu se scrie nimic
    ok = admin_client.post("/api/org/import/occupations/", {"file": xlsx(data[:3]), "dry_run": "0"}, format="multipart").data
    assert ok["saved"] is True
    assert Occupation.objects.get(code="221299").weekly_hours == Decimal("35")


def test_import_subdivisions_with_parent_and_missing_column(admin_client, seeded):
    missing = admin_client.post("/api/org/import/subdivisions/", {"file": xlsx([["Cod"], ["X"]]), "dry_run": "0"},
                                format="multipart").data
    assert missing["ok"] is False and "Denumirea (RO)" in missing["detail"]
    rows = [["Cod", "Denumirea (RO)", "Subdiviziunea-părinte (cod sau denumire)", "Paturi", "Condiții vătămătoare (da/nu)"],
            ["CHIR", "Departamentul chirurgie", "", "", ""],
            ["TR2", "Secția traumatologie nr. 2", "CHIR", "35", "da"]]
    r = admin_client.post("/api/org/import/subdivisions/", {"file": xlsx(rows), "dry_run": "0"}, format="multipart").data
    assert r["saved"] is True, r
    tr2 = Subdivision.objects.get(code="TR2")
    assert tr2.parent.code == "CHIR" and tr2.beds == 35 and tr2.harmful is True


def test_import_staff_lines_into_draft(admin_client, subs, occ):
    sl = StaffList.objects.create(effective_from="2026-01-01")
    rows = [["Subdiviziunea (cod sau denumire)", "Cod CORM", "Funcția", "Unități", "Salariul de funcție"],
            ["TR1", "", "Medic traumatolog-ortoped", 2.5, 14660],
            ["Secția anestezie și terapie intensivă", "", "Medic anestezist pediatric", "1,5", ""]]
    no_create = admin_client.post("/api/org/import/staff_lines/", {"file": xlsx(rows), "dry_run": "0",
                                                                   "staff_list": sl.id}, format="multipart").data
    assert no_create["saved"] is False and sl.lines.count() == 0
    r = admin_client.post("/api/org/import/staff_lines/", {"file": xlsx(rows), "dry_run": "0", "staff_list": sl.id,
                                                           "create_occupations": "1"}, format="multipart").data
    assert r["saved"] is True and sl.lines.count() == 2
    assert sl.lines.get(occupation__name_ro="Medic anestezist pediatric").units == Decimal("1.5")
    services.approve(sl)
    closed = admin_client.post("/api/org/import/staff_lines/", {"file": xlsx(rows), "dry_run": "1", "staff_list": sl.id},
                               format="multipart")
    assert closed.status_code == 400  # în statele aprobate nu se importă


# --- tiparul ----------------------------------------------------------------------------------
def test_staff_list_print_with_stema_and_languages(admin_client, subs, occ):
    from apps.core.models import Company

    company = Company.get()
    company.founder_ro, company.name_ro = "Ministerul Sănătății", "IMSP Spitalul Clinic de Traumatologie și Ortopedie"
    company.save()
    sl = make_list(subs, occ)
    html = admin_client.get(f"/api/org/staff-lists/{sl.id}/print/").content.decode()
    assert "STATELE DE PERSONAL" in html and "REPUBLICA MOLDOVA" in html
    assert "data:image/svg+xml;base64," in html  # Stema de Stat, pusă în pagină
    assert "Secția traumatologie nr. 1" in html and "Efectivul-limită" in html and "14,75" in html
    assert "Anexa nr. 1" in html and "Ordinul MS nr. 1" in html and "· IDNO" not in html
    ru = admin_client.get(f"/api/org/staff-lists/{sl.id}/print/", {"lang": "ru"}).content.decode()
    assert "ШТАТНОЕ РАСПИСАНИЕ" in ru and "РЕСПУБЛИКА МОЛДОВА" in ru
    company.show_stema = False
    company.save()
    plain = admin_client.get(f"/api/org/staff-lists/{sl.id}/print/").content.decode()
    assert "data:image/svg+xml" not in plain


def test_print_template_preview_for_staff_list(admin_client, subs, occ):
    from apps.printing.models import PrintTemplate

    services.approve(make_list(subs, occ))
    tpl = PrintTemplate.objects.get(doc_type="staff_list")
    r = admin_client.post("/api/print/preview/", {"doc_type": "staff_list", "body": tpl.body, "css": tpl.css, "lang": "ro"},
                          format="json")
    assert r.status_code == 200 and "Medic traumatolog-ortoped" in r.content.decode()
