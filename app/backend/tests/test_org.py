"""Etapa 1: clasificatoarele, subdiviziunile, statele de personal (versiuni, ocupare), importul din Excel, tiparul."""
import io
from decimal import Decimal

import pytest
from openpyxl import Workbook, load_workbook

from apps.org import seed as org_seed
from apps.org import services
from apps.org.serializers import StaffListLineSerializer
from apps.org.models import (STAFF_CATEGORY, DictItem, LegalBasis, Occupation, OrderType, Specialty, StaffList,
                             StaffListLine, Subdivision)


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
    adm = Subdivision.objects.create(code="ADM", name_ro="Administrația", kind="department", sort=1)
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția de croitorie nr. 1", kind="workshop", sort=10)
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția de vopsire", kind="workshop", harmful=True,
                                     extra_leave_days=7, sort=20)
    return {"adm": adm, "tr1": tr1, "ati": ati}


@pytest.fixture
def occ(seeded):
    # funcțiile livrate (CORM 006-2021); categoria vine din prima cifră a codului
    return {"director": Occupation.objects.get(code="112012"), "doctor": Occupation.objects.get(code="241106"),
            "nurse": Occupation.objects.get(code="753117")}


def make_list(subs, occ, effective="2026-01-01"):
    sl = StaffList.objects.create(number="1", effective_from=effective, approved_by="Ordinul directorului nr. 1-p")
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
    assert Occupation.objects.get(code="241106").category.code == "2"  # contabil: specialiști (grupa 2 CORM)
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


def test_seed_is_for_a_private_company(seeded):
    """Nimic de spital în clasificatoarele livrate; categoriile de personal = grupele majore CORM 006-2021."""
    cats = list(DictItem.objects.filter(kind=STAFF_CATEGORY).values_list("code", flat=True))
    assert cats == [str(i) for i in range(1, 10)]
    assert not OrderType.objects.filter(code__in=("attestation", "category_award", "on_call")).exists()
    assert not LegalBasis.objects.filter(code__in=("HG-837", "OMS-386", "OMS-100")).exists()
    assert not DictItem.objects.filter(kind="qualification").exists()
    assert not DictItem.objects.filter(kind="employment", code="resident").exists()
    assert not DictItem.objects.filter(kind="document", code__in=("residency_cert", "category_cert", "cme_cert")).exists()
    assert not Specialty.objects.exists()
    names = " ".join(Occupation.objects.values_list("name_ro", flat=True)).lower()
    assert "medic" not in names and "asistent medical" not in names
    for occupation in Occupation.objects.exclude(code=""):  # codul CORM: 6 cifre, categoria — după prima cifră
        assert len(occupation.code) == 6 and occupation.code.isdigit() and occupation.category.code == occupation.code[0]
    assert not Occupation.objects.filter(category__isnull=True).exists()
    assert DictItem.objects.get(kind="degree", code="dr").name_ro == "Doctor"
    checklist = " ".join(DictItem.objects.filter(kind="checklist").values_list("name_ro", flat=True))
    assert "SIA AMP" not in checklist and "halat" not in checklist and "art. 57" in checklist
    # temeiurile: articolele din Codul muncii completate, cu alineatul și litera
    refs = {b.code: b.reference() for b in LegalBasis.objects.all()}
    assert refs["CM-86-C"] == "art. 86 alin. (1) lit. c) din Codul muncii nr. 154/2003"
    assert refs["CM-AGR"] == "art. 82¹ din Codul muncii nr. 154/2003"
    for code in ("CM-STUDY", "CM-RECALL", "CM-OVERTIME", "CM-SUBST", "CM-TRAVEL", "CM-INCENT", "CM-148", "CM-211"):
        assert LegalBasis.objects.get(code=code).article, code
    assert {b.code for b in OrderType.objects.get(code="salary_set").legal_bases.all()} == {"CM-PAY", "REG-PAY"}
    assert {b.code for b in OrderType.objects.get(code="rest_day_work").legal_bases.all()} == {"CM-110", "CM-111"}
    assert OrderType.objects.get(code="sanction_lift").legal_bases.get().code == "CM-211"
    assert OrderType.objects.get(code="deduction").legal_bases.get().code == "CM-148"
    assert not OrderType.objects.get(code="staff_list").legal_bases.exists()
    reasons = {d.code: d.extra.get("legal_basis") for d in DictItem.objects.filter(kind="termination")}
    assert reasons["staff_cut"] == "CM-86-C" and reasons["agreement"] == "CM-AGR"
    assert all(LegalBasis.objects.filter(code=c).exists() for c in reasons.values() if c)


def test_seed_completes_articles_left_empty_by_old_versions(seeded):
    old = LegalBasis.objects.get(code="CM-RECALL")
    old.article = ""
    old.save()
    mine = LegalBasis.objects.get(code="CM-TRAVEL")
    mine.article, mine.act = "", "Contractul colectiv de muncă"  # schimbat de client — rămâne
    mine.save()
    org_seed.run()
    assert LegalBasis.objects.get(code="CM-RECALL").article == "122"
    assert LegalBasis.objects.get(code="CM-TRAVEL").article == ""


def test_staff_categories_are_an_editable_classifier(admin_client):
    """Categoria de personal: din clasificator (adăugare, redenumire); goală — după prima cifră a codului CORM."""
    new = admin_client.post("/api/org/dict-items/", {"kind": STAFF_CATEGORY, "code": "0", "name_ro": "Forțele armate"},
                            format="json")
    assert new.status_code == 201
    auto = admin_client.post("/api/org/occupations/", {"code": "099999", "name_ro": "Funcție de test"}, format="json").data
    assert auto["category"] == new.data["id"] and auto["category_name"] == "Forțele armate"
    no_code = admin_client.post("/api/org/occupations/", {"name_ro": "Funcție fără cod"}, format="json").data
    assert no_code["category"] is None
    other_kind = DictItem.objects.get(kind="sanction", code="warning")
    bad = admin_client.post("/api/org/occupations/", {"name_ro": "X", "category": other_kind.id}, format="json")
    assert bad.status_code == 400  # doar din clasificatorul categoriilor
    group2 = DictItem.objects.get(kind=STAFF_CATEGORY, code="2")
    admin_client.patch(f"/api/org/dict-items/{group2.id}/", {"name_ro": "Specialiști"}, format="json")
    filtered = admin_client.get("/api/org/occupations/", {"category": group2.id}).data
    assert filtered and {o["category_name"] for o in filtered} == {"Specialiști"}
    assert [o["name_ro"] for o in admin_client.get("/api/org/occupations/", {"category": "none"}).data] == ["Funcție fără cod"]
    # categoria folosită nu se șterge de tot (doar se marchează)
    assert admin_client.delete(f"/api/org/dict-items/{group2.id}/").status_code == 204
    done = admin_client.post("/api/system/marked/delete/", {"keys": [f"org.DictItem:{group2.id}"]}, format="json").data
    assert not done["deleted"] and DictItem.objects.filter(pk=group2.id).exists()


# --- drepturile -------------------------------------------------------------------------
def test_dictionaries_crud_and_permissions(admin_client, make_user, client_for):
    group3 = DictItem.objects.get(kind=STAFF_CATEGORY, code="3")
    r = admin_client.post("/api/org/occupations/", {"code": "999999", "name_ro": "Test funcție", "category": group3.id},
                          format="json")
    assert r.status_code == 201, r.data
    assert r.data["category"] == group3.id  # aleasă de mână, nu după prima cifră a codului
    dup = admin_client.post("/api/org/occupations/", {"code": "999999", "name_ro": "Alta"}, format="json")
    assert dup.status_code == 400
    head = client_for(make_user("sef", ["department_head"]))
    assert head.get("/api/org/occupations/").status_code == 403  # șeful de secție nu vede clasificatoarele
    inspector = client_for(make_user("insp", ["hr_inspector"]))
    assert inspector.get("/api/org/occupations/").status_code == 200
    assert inspector.delete(f"/api/org/occupations/{r.data['id']}/").status_code == 403
    found = admin_client.get("/api/org/occupations/", {"q": "contabil"}).data
    assert [o["name_ro"] for o in found] == ["Contabil-șef", "Contabil"]
    items = admin_client.get("/api/org/dict-items/", {"kind": "sanction"}).data
    assert [i["code"] for i in items] == ["warning", "reprimand", "severe", "dismissal"]


def test_meta_lists_enums(admin_client):
    data = admin_client.get("/api/org/meta/").data
    assert "staff_category" in data["dict_kinds"] and "hire" in data["order_effects"] and "categories" not in data
    assert data["subdivision_kinds"] == ["department", "section", "workshop", "branch", "warehouse", "other"]
    assert {i["code"] for i in data["imports"]} == {"occupations", "specialties", "subdivisions", "staff_lines"}


# --- subdiviziunile ----------------------------------------------------------------------
def test_subdivision_tree_cycle_and_protected_delete(admin_client, subs, occ):
    child = admin_client.post("/api/org/subdivisions/", {"name_ro": "Sectorul de uscare", "parent": subs["ati"].id},
                              format="json")
    assert child.status_code == 201
    tree = admin_client.get("/api/org/subdivisions/", {"tree": "1"}).data
    ati = next(n for n in tree if n["code"] == "ATI")
    assert ati["children"][0]["name_ro"] == "Sectorul de uscare" and ati["children"][0]["kind"] == "section"
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
    assert cats == {"1": "1.00", "2": "4.50", "7": "9.25"}
    assert [c["name"] for c in t["categories"]][0] == "Conducători și funcționari superiori"  # ordinea clasificatorului
    # categoria scrisă în rând are întâietate; funcția fără categorie — „Fără categorie”, la sfârșit
    line = sl.lines.get(occupation=occ["nurse"])
    line.category = DictItem.objects.get(kind=STAFF_CATEGORY, code="8")
    line.save()
    no_cat = Occupation.objects.create(name_ro="Funcție nouă")
    StaffListLine.objects.create(staff_list=sl, subdivision=subs["adm"], occupation=no_cat, units=1, base_salary=Decimal("1"))
    t = services.totals(sl, lang="en")
    assert [(c["code"], c["units"]) for c in t["categories"]] == [("1", "1.00"), ("2", "4.50"), ("8", "9.25"), ("", "1.00")]
    assert t["categories"][-1]["name"] == "No category"
    lines = {ln["occupation_name"]: ln for ln in StaffListLineSerializer(sl.lines.all(), many=True).data}
    assert lines["Cusător în confecții"]["effective_category"] == line.category_id
    assert lines["Funcție nouă"]["effective_category"] is None
    # fondul: 20000 + 4.5 × 14660 × 1.10 + 9.25 × 9000 + 1 (rândul fără categorie)
    assert Decimal(t["fund"]) == Decimal("20000") + Decimal("72567.00") + Decimal("83250.00") + Decimal("1")


def test_staff_list_lifecycle(admin_client, subs, occ):
    r = admin_client.post("/api/org/staff-lists/", {"number": "7", "effective_from": "2026-01-01",
                                                     "approved_by": "Ordinul directorului nr. 1-p"}, format="json")
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
        ("Secția de croitorie nr. 1", "Cusător în confecții"): "changed",
        ("Secția de croitorie nr. 1", "Contabil"): "removed",
        ("Secția de vopsire", "Contabil"): "added",
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
    row = next(r for r in data["rows"] if r["occupation"] == "Cusător în confecții")
    assert row["vacant"] == "9.25" and row["over"] is False
    assert row["category"] == occ["nurse"].category_id and row["category_name"] == "Muncitori calificați și lucrători din domeniul artizanal"


def test_occupancy_uses_registered_provider(subs, occ, monkeypatch):
    sl = make_list(subs, occ)
    services.approve(sl)

    def provider(staff_list, on_date):
        return {(subs["tr1"].id, occ["doctor"].id): {"occupied": Decimal("5"), "temporary": Decimal("1"),
                                                      "holders": [{"name": "Ion Popescu", "units": "1", "kind": "main"}]}}

    monkeypatch.setattr(services, "OCCUPANCY_PROVIDERS", [provider])
    row = next(r for r in services.occupancy()["rows"] if r["occupation"] == "Contabil")
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
            ["Funcție de test", "799999", "", "35"],  # categoria — după prima cifră a codului (7)
            ["Contabil", "241106", "", ""],  # există: se actualizează
            ["Funcție greșită", "", "nimic", ""],
            ["Operator la linia de îmbuteliere", "", "Operatori și asamblori", ""],  # după începutul denumirii
            ["Paznic de noapte", "", 9, ""]]  # după cod, scris ca număr în Excel
    dry = admin_client.post("/api/org/import/occupations/", {"file": xlsx(data), "dry_run": "1"}, format="multipart").data
    assert dry["created"] == 3 and dry["updated"] == 1 and [e["row"] for e in dry["errors"]] == [4]
    assert Occupation.objects.count() == before  # încercarea nu scrie nimic
    fail = admin_client.post("/api/org/import/occupations/", {"file": xlsx(data), "dry_run": "0"}, format="multipart").data
    assert fail["saved"] is False and Occupation.objects.count() == before  # cu erori nu se scrie nimic
    ok = admin_client.post("/api/org/import/occupations/", {"file": xlsx(data[:3] + data[4:]), "dry_run": "0"},
                           format="multipart").data
    assert ok["saved"] is True
    made = Occupation.objects.get(code="799999")
    assert made.weekly_hours == Decimal("35") and made.category.code == "7"
    assert Occupation.objects.get(name_ro="Operator la linia de îmbuteliere").category.code == "8"
    assert Occupation.objects.get(name_ro="Paznic de noapte").category.code == "9"


def test_import_subdivisions_with_parent_and_missing_column(admin_client, seeded):
    missing = admin_client.post("/api/org/import/subdivisions/", {"file": xlsx([["Cod"], ["X"]]), "dry_run": "0"},
                                format="multipart").data
    assert missing["ok"] is False and "Denumirea (RO)" in missing["detail"]
    rows = [["Cod", "Denumirea (RO)", "Subdiviziunea-părinte (cod sau denumire)", "Tipul", "Condiții vătămătoare (da/nu)"],
            ["CHIR", "Departamentul producție", "", "department", ""],
            ["TR2", "Atelierul de sudură", "CHIR", "atelier", "da"]]
    r = admin_client.post("/api/org/import/subdivisions/", {"file": xlsx(rows), "dry_run": "0"}, format="multipart").data
    assert r["saved"] is True, r
    tr2 = Subdivision.objects.get(code="TR2")
    assert tr2.parent.code == "CHIR" and tr2.kind == "workshop" and tr2.harmful is True
    assert Subdivision.objects.get(code="CHIR").kind == "department"


def test_import_staff_lines_into_draft(admin_client, subs, occ):
    sl = StaffList.objects.create(effective_from="2026-01-01")
    rows = [["Subdiviziunea (cod sau denumire)", "Cod CORM", "Funcția", "Unități", "Salariul de funcție", "Categoria de personal"],
            ["TR1", "", "Contabil", 2.5, 14660, ""],
            ["Secția de vopsire", "", "Vopsitor auto", "1,5", "", "7"]]
    no_create = admin_client.post("/api/org/import/staff_lines/", {"file": xlsx(rows), "dry_run": "0",
                                                                   "staff_list": sl.id}, format="multipart").data
    assert no_create["saved"] is False and sl.lines.count() == 0
    r = admin_client.post("/api/org/import/staff_lines/", {"file": xlsx(rows), "dry_run": "0", "staff_list": sl.id,
                                                           "create_occupations": "1"}, format="multipart").data
    assert r["saved"] is True and sl.lines.count() == 2
    painter = sl.lines.get(occupation__name_ro="Vopsitor auto")
    assert painter.units == Decimal("1.5") and painter.category.code == "7"
    assert sl.lines.get(occupation__name_ro="Contabil").category is None  # goală — a funcției
    services.approve(sl)
    closed = admin_client.post("/api/org/import/staff_lines/", {"file": xlsx(rows), "dry_run": "1", "staff_list": sl.id},
                               format="multipart")
    assert closed.status_code == 400  # în statele aprobate nu se importă


# --- tiparul ----------------------------------------------------------------------------------
def test_staff_list_print_with_company_header_and_languages(admin_client, subs, occ):
    from apps.core.models import Company

    company = Company.get()
    company.name_ro, company.name_ru, company.legal_form = "„Exemplu Prim”", "«Пример Прим»", "SRL"
    company.save()
    sl = make_list(subs, occ)
    html = admin_client.get(f"/api/org/staff-lists/{sl.id}/print/").content.decode()
    assert "STATELE DE PERSONAL" in html and "„Exemplu Prim” SRL" in html and 'class="company-header"' in html
    assert "REPUBLICA MOLDOVA" not in html and "data:image/svg+xml" not in html  # fără Stema de Stat
    assert "Secția de croitorie nr. 1" in html and "Efectivul-limită" in html and "14,75" in html
    assert "Anexa nr. 1" in html and "Ordinul directorului nr. 1-p" in html and "IDNO" not in html  # IDNO necompletat — nu apare
    assert "Specialiști în diverse domenii de activitate" in html  # categoriile din clasificator
    ru = admin_client.get(f"/api/org/staff-lists/{sl.id}/print/", {"lang": "ru"}).content.decode()
    assert "ШТАТНОЕ РАСПИСАНИЕ" in ru and "«Пример Прим» SRL" in ru and "РЕСПУБЛИКА МОЛДОВА" not in ru


def test_print_template_preview_for_staff_list(admin_client, subs, occ):
    from apps.printing.models import PrintTemplate

    services.approve(make_list(subs, occ))
    tpl = PrintTemplate.objects.get(doc_type="staff_list")
    r = admin_client.post("/api/print/preview/", {"doc_type": "staff_list", "body": tpl.body, "css": tpl.css, "lang": "ro"},
                          format="json")
    assert r.status_code == 200 and "Cusător în confecții" in r.content.decode()
