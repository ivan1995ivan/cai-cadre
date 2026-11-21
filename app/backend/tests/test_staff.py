"""Etapa 2: dosarul angajatului — raporturi de muncă cu istoric, vechimea, vizibilitatea, datele sensibile, importul,
ocuparea posturilor și tiparul (fișa MR-2, adeverințele, lista)."""
import io
from datetime import date, timedelta
from decimal import Decimal

import pytest
from openpyxl import Workbook

from apps.org import services as org_services
from apps.org.models import DictItem, Occupation, StaffList, StaffListLine, Subdivision
from apps.staff import services
from apps.staff.models import AccessLog, Employee, Employment, PriorExperience
from .conftest import occupation


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
def org(seeded):
    tr1 = Subdivision.objects.create(code="TR1", name_ro="Secția traumatologie nr. 1", name_ru="Травматология № 1")
    ati = Subdivision.objects.create(code="ATI", name_ro="Secția ATI")
    bo = Subdivision.objects.create(code="BO", name_ro="Blocul operator", parent=ati)
    return {
        "tr1": tr1, "ati": ati, "bo": bo,
        "doctor": occupation("Medic traumatolog-ortoped"),
        "nurse": occupation("Asistent medical de secție"),
        "anest": occupation("Medic anesteziolog-reanimatolog"),
    }


def make_emp(last="Popescu", first="Ion", idnp="", **extra):
    return Employee.objects.create(tab_number=services.next_tab_number(), last_name=last, first_name=first, idnp=idnp, **extra)


def hire(emp, org, occ="doctor", sub="tr1", **extra):
    fields = {"kind": "main", "rate": Decimal("1"), "base_salary": Decimal("14660"), "date_from": date(2020, 1, 1), **extra}
    return services.hire(emp, subdivision=org[sub], occupation=org[occ], **fields)


# --- angajatul și raporturile de muncă ---------------------------------------------------------
def test_create_employee_with_auto_tab_number_and_idnp_checks(admin_client, org):
    r = admin_client.post("/api/staff/employees/", {"last_name": "Popescu", "first_name": "Ion", "idnp": "2001000123456"},
                          format="json")
    assert r.status_code == 201, r.data
    assert r.data["tab_number"] == "1"
    second = admin_client.post("/api/staff/employees/", {"last_name": "Rusu", "first_name": "Ana"}, format="json")
    assert second.data["tab_number"] == "2"
    dup = admin_client.post("/api/staff/employees/", {"last_name": "X", "first_name": "Y", "idnp": "2001000123456"}, format="json")
    assert dup.status_code == 400 and "idnp" in dup.data
    bad = admin_client.post("/api/staff/employees/", {"last_name": "X", "first_name": "Y", "idnp": "123"}, format="json")
    assert bad.status_code == 400
    assert admin_client.get("/api/staff/employees/next-number/").data["tab_number"] == "3"


def test_hire_cumul_and_single_main_contract(admin_client, org):
    emp = make_emp()
    r = admin_client.post("/api/staff/employments/", {
        "employee": emp.id, "kind": "main", "subdivision": org["tr1"].id, "occupation": org["doctor"].id, "rate": "1",
        "base_salary": "14660", "date_from": "2020-01-01", "hire_order": "12-p din 30.12.2019"}, format="json")
    assert r.status_code == 201, r.data
    assert r.data["history"][0]["event"] == "hire" and r.data["history"][0]["order"] == "12-p din 30.12.2019"
    again = admin_client.post("/api/staff/employments/", {
        "employee": emp.id, "kind": "main", "subdivision": org["ati"].id, "occupation": org["anest"].id, "rate": "1",
        "date_from": "2021-01-01"}, format="json")
    assert again.status_code == 400  # al doilea raport de bază activ
    cumul = admin_client.post("/api/staff/employments/", {
        "employee": emp.id, "kind": "internal", "subdivision": org["ati"].id, "occupation": org["anest"].id, "rate": "0.5",
        "date_from": "2021-01-01"}, format="json")
    assert cumul.status_code == 201
    too_much = admin_client.post("/api/staff/employments/", {
        "employee": emp.id, "kind": "internal", "subdivision": org["ati"].id, "occupation": org["anest"].id, "rate": "2",
        "date_from": "2021-01-01"}, format="json")
    assert too_much.status_code == 400
    row = admin_client.get("/api/staff/employees/").data["results"][0]
    assert row["jobs"] == 2 and row["subdivision"] == "Secția traumatologie nr. 1" and row["kind"] == "main"


def test_change_keeps_history_and_future_changes_wait(admin_client, org):
    emp = make_emp()
    job = hire(emp, org)
    r = admin_client.post(f"/api/staff/employments/{job.id}/change/", {
        "date": "2023-05-01", "occupation": org["anest"].id, "subdivision": org["ati"].id, "base_salary": "15200",
        "order": "88-p din 28.04.2023"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["occupation"] == org["anest"].id and len(r.data["history"]) == 2
    assert services.values_on(job, date(2022, 1, 1))["occupation_id"] == org["doctor"].id
    future = date.today() + timedelta(days=30)
    admin_client.post(f"/api/staff/employments/{job.id}/change/", {"date": future.isoformat(), "rate": "0.75"}, format="json")
    job.refresh_from_db()
    assert job.rate == Decimal("1")  # încă nu
    assert services.apply_due_changes(future) == 1
    job.refresh_from_db()
    assert job.rate == Decimal("0.75")
    nothing = admin_client.post(f"/api/staff/employments/{job.id}/change/", {"date": "2024-01-01", "rate": "0.75"}, format="json")
    assert nothing.status_code == 400  # nimic de schimbat
    plain_edit = admin_client.patch(f"/api/staff/employments/{job.id}/", {"base_salary": "1"}, format="json")
    assert plain_edit.status_code == 400  # salariul nu se schimbă fără istoric


def test_suspend_resume_terminate_and_status(admin_client, org):
    emp = make_emp()
    job = hire(emp, org)
    other = make_emp("Rusu", "Ana")
    subst = hire(other, org, occ="doctor", kind="substitute", substitutes=job, date_from=date(2024, 3, 1))
    assert admin_client.post(f"/api/staff/employments/{job.id}/suspend/",
                             {"date": "2024-03-01", "reason": "Concediu de îngrijire a copilului"}, format="json").status_code == 200
    emp.refresh_from_db()
    assert emp.status == "suspended"
    assert admin_client.post(f"/api/staff/employments/{job.id}/resume/", {"date": "2025-03-01"}, format="json").status_code == 200
    reason = DictItem.objects.get(kind="termination", code="resignation")
    r = admin_client.post(f"/api/staff/employments/{job.id}/terminate/",
                          {"date": "2025-10-01", "reason": reason.id, "order": "201-p"}, format="json")
    assert r.status_code == 200 and r.data["status"] == "ended" and r.data["termination_reason_name"] == "Demisie"
    emp.refresh_from_db()
    subst.refresh_from_db()
    assert emp.status == "dismissed" and subst.status == "ended"  # suplinirea încetează odată cu raportul suplinit
    arch = admin_client.post(f"/api/staff/employees/{emp.id}/archive/", {}, format="json")
    assert arch.status_code == 200, arch.data
    assert arch.data["is_archived"] is True
    assert admin_client.get("/api/staff/employees/").data["count"] == 0  # implicit: doar cei în funcție
    assert admin_client.get("/api/staff/employees/", {"status": "archived"}).data["count"] == 1
    assert admin_client.delete(f"/api/staff/employees/{emp.id}/").status_code == 400


# --- vechimea ------------------------------------------------------------------------------------
def test_seniority_merges_overlaps_and_splits_kinds(org):
    emp = make_emp()
    PriorExperience.objects.create(employee=emp, organization="Spitalul A", date_from=date(2010, 1, 1), date_to=date(2014, 12, 31))
    PriorExperience.objects.create(employee=emp, organization="Cumul B", date_from=date(2014, 1, 1), date_to=date(2015, 6, 30))
    PriorExperience.objects.create(employee=emp, organization="Bancă", date_from=date(2016, 1, 1), date_to=date(2016, 12, 31),
                                   in_specialty=False)
    hire(emp, org, date_from=date(2020, 1, 1))
    s = services.seniority(emp, date(2025, 12, 31))
    assert (s["total"]["years"], s["total"]["months"], s["total"]["days"]) == (12, 6, 0)  # 5a6l + 1a + 6a
    assert (s["specialty"]["years"], s["specialty"]["months"]) == (11, 6)
    assert (s["institution"]["years"], s["institution"]["months"], s["institution"]["days"]) == (6, 0, 0)
    assert services.seniority_text(s["institution"]) == "6 ani 0 luni 0 zile"


# --- vizibilitatea și datele sensibile -------------------------------------------------------------
def test_department_head_sees_only_own_subdivision_and_no_sensitive_data(org, make_user, client_for, admin_client):
    a, b = make_emp(idnp="2001000000001"), make_emp("Rusu", "Ana", idnp="2001000000002")
    hire(a, org, sub="tr1")
    hire(b, org, occ="anest", sub="bo")
    head = make_user("sef", ["department_head"])
    org["ati"].users.add(head)
    api = client_for(head)
    names = [r["full_name"] for r in api.get("/api/staff/employees/").data["results"]]
    assert names == []  # rolul are „doar ale mele”: ATI fără sub-secții → nimeni direct în ATI
    role = head.roles.first()
    role.data_scopes = {**role.data_scopes, "employees": "team"}
    role.save()
    head = type(head).objects.get(pk=head.pk)
    api = client_for(head)
    rows = api.get("/api/staff/employees/").data["results"]
    assert [r["full_name"] for r in rows] == ["Rusu Ana"]  # „echipa”: ATI cu blocul operator
    assert rows[0]["idnp"] is None  # fără dreptul „date sensibile”
    assert api.get(f"/api/staff/employees/{a.id}/").status_code == 404
    card = api.get(f"/api/staff/employees/{b.id}/").data
    assert card["idnp"] is None and card["iban"] is None
    assert api.get("/api/staff/documents/", {"employee": b.id}).status_code == 403
    jobs = api.get("/api/staff/employments/", {"employee": b.id}).data
    assert jobs[0]["occupation_name"] == "Medic anesteziolog-reanimatolog" and jobs[0]["base_salary"] is None
    assert api.get("/api/staff/employments/", {"employee": a.id}).data == []  # alt angajat: nimic
    assert api.post(f"/api/staff/employments/{jobs[0]['id']}/suspend/", {"date": "2025-01-01"}, format="json").status_code == 403


def test_masked_field_is_not_overwritten(org, make_user, client_for):
    emp = make_emp(idnp="2001000000009")
    hire(emp, org)
    insp = client_for(make_user("insp", ["hr_inspector"]))  # inspectorul are „sensitive”, dar salariul e ascuns
    card = insp.get(f"/api/staff/employees/{emp.id}/").data
    assert card["idnp"] == "2001000000009"
    jobs = insp.get("/api/staff/employments/", {"employee": emp.id}).data
    assert jobs[0]["base_salary"] is None
    upd = insp.patch(f"/api/staff/employees/{emp.id}/", {**card, "phone": "069000000"}, format="json")
    assert upd.status_code == 200, upd.data
    emp.refresh_from_db()
    assert emp.idnp == "2001000000009" and emp.phone == "069000000"


def test_opening_the_file_is_logged(admin_client, org):
    emp = make_emp()
    admin_client.get(f"/api/staff/employees/{emp.id}/")
    admin_client.get(f"/api/staff/employees/{emp.id}/print/", {"doc": "employee_card"})
    actions = list(AccessLog.objects.filter(employee=emp).values_list("action", flat=True))
    assert sorted(actions) == ["print", "view"]
    assert len(admin_client.get(f"/api/staff/employees/{emp.id}/access-log/").data) == 2


# --- ocuparea posturilor ---------------------------------------------------------------------------
def test_employees_fill_the_staff_list_occupancy(org):
    sl = StaffList.objects.create(effective_from=date(2025, 1, 1))
    StaffListLine.objects.create(staff_list=sl, subdivision=org["tr1"], occupation=org["doctor"], units=Decimal("3"))
    org_services.approve(sl)
    a, b, c = make_emp(), make_emp("Rusu", "Ana"), make_emp("Ceban", "Dan")
    hire(a, org)
    job_b = hire(b, org, rate=Decimal("0.5"))
    hire(c, org, kind="internal", rate=Decimal("0.25"))
    services.suspend(job_b, date(2025, 2, 1), "Concediu de îngrijire a copilului")
    occ = org_services.occupancy(on_date=date(2025, 6, 1))
    row = occ["rows"][0]
    assert occ["employees_module"] is True
    assert (row["occupied"], row["temporary"], row["vacant"]) == ("1.75", "0.50", "1.25")
    assert {h["name"] for h in row["holders"]} == {"Popescu I.", "Rusu A.", "Ceban D."}


# --- importul din Excel -----------------------------------------------------------------------------
def test_import_employees_with_cumul_then_family_and_experience(admin_client, org):
    rows = [["Nr. tabel", "Numele", "Prenumele", "IDNP", "Data nașterii", "Sexul (M/F)", "Subdiviziunea (cod sau denumire)",
             "Funcția", "Tipul angajării", "Norma", "Data angajării", "Salariul de funcție"],
            ["101", "Popescu", "Ion", "2001000123456", "15.03.1980", "M", "TR1", "Medic traumatolog-ortoped", "de bază", 1,
             "01.09.2015", 14660],
            ["101", "Popescu", "Ion", "2001000123456", "15.03.1980", "M", "ATI", "Medic anesteziolog-reanimatolog", "cumul intern",
             0.25, "01.01.2020", 15200],
            ["", "Rusu", "Ana", "", "", "F", "TR1", "Asistent medical de secție", "", "", "01.02.2018", 9200]]
    dry = admin_client.post("/api/staff/import/employees/", {"file": xlsx(rows), "dry_run": "1"}, format="multipart").data
    assert dry["ok"] and dry["created"] == 2 and dry["updated"] == 1, dry
    assert Employee.objects.count() == 0
    r = admin_client.post("/api/staff/import/employees/", {"file": xlsx(rows), "dry_run": "0"}, format="multipart").data
    assert r["saved"], r
    ion = Employee.objects.get(tab_number="101")
    assert ion.employments.count() == 2
    ana = Employee.objects.get(last_name="Rusu")
    assert ana.tab_number == "102" and ana.employments.get().rate == Decimal("1")
    assert ion.employments.get(kind="main").history.get().event == "import"
    again = admin_client.post("/api/staff/import/employees/", {"file": xlsx(rows), "dry_run": "0"}, format="multipart").data
    assert again["saved"] and Employment.objects.count() == 3  # reimportul nu dublează raporturile

    fam = [["Nr. tabel", "Rudenia", "Numele, prenumele", "Data nașterii", "Întreținut (da/nu)"],
           ["101", "Fiică", "Popescu Maria", "10.05.2015", "da"], ["999", "Fiu", "Necunoscut", "", ""]]
    bad = admin_client.post("/api/staff/import/family/", {"file": xlsx(fam), "dry_run": "0"}, format="multipart").data
    assert bad["saved"] is False and bad["errors"][0]["row"] == 3
    ok = admin_client.post("/api/staff/import/family/", {"file": xlsx(fam[:2]), "dry_run": "0"}, format="multipart").data
    assert ok["saved"] and ion.family.get().dependent is True

    exp = [["IDNP angajat", "Unitatea", "Funcția", "De la", "Până la", "În specialitate (da/nu)"],
           ["2001000123456", "IMSP SCR", "Medic rezident", "01.09.2009", "31.08.2015", "da"]]
    assert admin_client.post("/api/staff/import/experience/", {"file": xlsx(exp), "dry_run": "0"}, format="multipart").data["saved"]
    assert services.seniority(ion, date(2025, 8, 31))["total"]["years"] == 16


def test_import_employee_unknown_subdivision_rolls_back(admin_client, org):
    rows = [["Numele", "Prenumele", "Subdiviziunea (cod sau denumire)", "Funcția", "Data angajării"],
            ["Popescu", "Ion", "TR1", "Medic traumatolog-ortoped", "01.01.2020"],
            ["Rusu", "Ana", "NU-EXISTA", "Medic traumatolog-ortoped", "01.01.2020"]]
    r = admin_client.post("/api/staff/import/employees/", {"file": xlsx(rows), "dry_run": "0"}, format="multipart").data
    assert r["saved"] is False and "NU-EXISTA" in r["errors"][0]["error"]
    assert Employee.objects.count() == 0


# --- tiparul ------------------------------------------------------------------------------------------
def test_prints_card_certificates_and_list(admin_client, org):
    emp = make_emp(idnp="2001000123456", sex="F", birth_date=date(1985, 4, 2))
    hire(emp, org, contract_number="15", contract_date=date(2019, 12, 30))
    PriorExperience.objects.create(employee=emp, organization="IMSP SCR", date_from=date(2010, 1, 1), date_to=date(2019, 12, 31))
    card = admin_client.get(f"/api/staff/employees/{emp.id}/print/", {"doc": "employee_card"}).content.decode()
    assert "FIȘA PERSONALĂ A SALARIATULUI" in card and "Popescu Ion" in card and "2001000123456" in card
    assert 'class="company-header"' in card and "data:image/svg+xml" not in card and "IMSP SCR" in card
    cert = admin_client.get(f"/api/staff/employees/{emp.id}/print/", {"doc": "certificate_work", "purpose": "Banca"}).content.decode()
    assert "dna" in cert and "Medic traumatolog-ortoped" in cert and "contractului individual de muncă nr. 15" in cert
    assert "AD-" in cert and "Banca" in cert
    cert2 = admin_client.get(f"/api/staff/employees/{emp.id}/print/", {"doc": "certificate_work"}).content.decode()
    num1, num2 = (c.split("Nr. ")[1].split("<")[0] for c in (cert, cert2))
    assert num1.startswith("AD-") and num1 != num2  # fiecare adeverință are numărul ei
    sen = admin_client.get(f"/api/staff/employees/{emp.id}/print/", {"doc": "certificate_seniority"}).content.decode()
    assert "VECHIMEA ÎN MUNCĂ" in sen and "ani" in sen
    lst = admin_client.get("/api/staff/employees/print-list/").content.decode()
    assert "LISTA ANGAJAȚILOR" in lst and "Secția traumatologie nr. 1" in lst and "1 angajați" in lst
    assert admin_client.get(f"/api/staff/employees/{emp.id}/print/", {"doc": "nimic"}).status_code == 400


# --- mai multe raporturi: de bază, cumul, contract de prestări servicii ----------------------------------------
def test_several_jobs_with_percent_rate_cumul_pay_and_service_contract(admin_client, org):
    from apps.leave import balance

    sl = StaffList.objects.create(effective_from=date(2025, 1, 1))
    StaffListLine.objects.create(staff_list=sl, subdivision=org["ati"], occupation=org["anest"], units=Decimal("2"))
    org_services.approve(sl)
    a = make_emp()
    hire(a, org, date_from=date(2020, 1, 1))
    # cumulul intern: raport separat, cu modalitatea lui de remunerare (S4b) — aici tarif orar
    bad = admin_client.post("/api/staff/employments/", {"employee": a.id, "kind": "internal", "subdivision": org["ati"].id,
                                                        "occupation": org["anest"].id, "rate": "0.25", "pay_mode": "hourly",
                                                        "date_from": "2025-01-01"}, format="json")
    assert bad.status_code == 400 and "tariful orar" in str(bad.data)
    r = admin_client.post("/api/staff/employments/", {"employee": a.id, "kind": "internal", "subdivision": org["ati"].id,
                                                      "occupation": org["anest"].id, "rate": "0.25", "pay_mode": "hourly",
                                                      "hourly_rate": "95", "date_from": "2025-01-01"}, format="json")
    assert r.status_code == 201, r.data
    assert (r.data["pay_mode"], Decimal(r.data["hourly_rate"])) == ("hourly", 95)
    job = Employment.objects.get(pk=r.data["id"])
    assert (job.history.get().pay_mode, job.history.get().hourly_rate) == ("hourly", Decimal("95"))
    r = admin_client.post(f"/api/staff/employments/{job.id}/change/", {"date": "2025-06-01", "hourly_rate": "110"},
                          format="json")
    assert r.status_code == 200, r.data
    job.refresh_from_db()
    assert job.hourly_rate == Decimal("110") and job.history.count() == 2 and job.history.last().event == "change"
    # contract de prestări servicii: nu ocupă post, nu intră în vechime, nu dă concediu
    c = make_emp("Ceban", "Dan")
    services.hire(c, kind="contractor", subdivision=org["ati"], occupation=org["anest"], rate=Decimal("0.5"),
                  date_from=date(2024, 1, 1))
    row = org_services.occupancy(on_date=date(2025, 7, 1))["rows"][0]
    assert row["occupied"] == "0.25"
    assert services.seniority(c, date(2025, 7, 1))["total"]["total_days"] == 0
    assert balance.balance(c, on_date=date(2025, 7, 1))["years"] == []


def test_combination_order_sets_cumul_pay_and_import_percent_rate(admin_client, org):
    from .test_orders import make_order, set_params, sign

    a = make_emp()
    hire(a, org, date_from=date(2020, 1, 1))
    base = a.employments.get()
    # cumularea funcțiilor (CM art. 156): pe același contract — înregistrarea pe raportul de bază, nu un raport nou
    order = make_order(admin_client, "combination", [a])
    item = set_params(admin_client, order, {"subdivision": org["ati"].id, "occupation": org["anest"].id, "percent": "50",
                                            "date_from": "2026-03-02", "date_to": "2026-08-31"})
    assert "fără eliberare de la munca de bază" in item["text"] and "plata de 50% din salariul de funcție" in item["text"]
    sign(admin_client, order)
    assert a.employments.count() == 1
    rec = base.combinations.get()
    assert (rec.kind, rec.occupation_id, rec.pay_mode, rec.value, rec.date_to) == (
        "combination", org["anest"].id, "pct_own", Decimal("50"), date(2026, 8, 31))
    # ca raport separat (cumul intern cu pontaj propriu) — la cerere
    order = make_order(admin_client, "combination", [a])
    set_params(admin_client, order, {"mode": "separate", "subdivision": org["ati"].id, "occupation": org["anest"].id,
                                     "rate": "0.5", "base_salary": "15200", "date_from": "2026-03-02", "date_to": "2026-08-31"})
    sign(admin_client, order)
    job = a.employments.get(kind="internal")
    assert (job.rate, job.base_salary, job.allowance_pct, job.combinations.count()) == (Decimal("0.5"), Decimal("15200"), Decimal("0"), 0)
    rows = [["Numele", "Prenumele", "Subdiviziunea (cod sau denumire)", "Funcția", "Tipul angajării", "Norma", "Data angajării"],
            ["Rusu", "Ana", "TR1", "Medic traumatolog-ortoped", "de bază", "50%", "01.01.2020"],
            ["Rusu", "Ana", "ATI", "Medic anesteziolog-reanimatolog", "prestări servicii", 25, "01.01.2021"]]
    r = admin_client.post("/api/staff/import/employees/", {"file": xlsx(rows), "dry_run": "0"}, format="multipart").data
    assert r["saved"], r
    ana = Employee.objects.get(last_name="Rusu")
    assert sorted((j.kind, j.rate) for j in ana.employments.all()) == [("contractor", Decimal("0.25")), ("main", Decimal("0.5"))]


def test_ids_filter_gives_names_without_opening_the_file(admin_client, org):
    a, b, c = make_emp("Albu"), make_emp("Botnaru"), make_emp("Ciobanu", status="dismissed")
    r = admin_client.get("/api/staff/employees/", {"ids": f"{a.id},{c.id},x", "status": "all"})
    assert r.status_code == 200
    assert sorted(row["id"] for row in r.json()["results"]) == sorted([a.id, c.id])
    assert not AccessLog.objects.filter(employee__in=[a, b, c]).exists()
