"""S6b (pasul c) — GPS-ul vehiculelor și KPI-ul șoferilor: consumul cursei (rezervorul / de mână / GPS) și norma, importul
zilelor GPS din Excel și CSV (antetul altor programe, unitățile în celule), comparația cu foaia de parcurs, notarea
indicatorilor, fișa KPI (completarea, valorile de mână, pragul, aprobarea) și prima în salariu."""
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.payroll.models import PayType
from apps.transport import kpi
from apps.transport.models import GpsDay, KpiScheme, Trip

from .test_payroll import org, person  # noqa: F401
from .test_payroll_2026 import timesheet
from .test_transport import approve, fleet, items, rate, trip  # noqa: F401 — fixtura și ajutoarele comune

D = Decimal


def test_grade_both_directions_and_step():
    g = kpi.grade
    # mai puțin e mai bine: 100 % la ≤ 100, 0 la ≥ 110
    assert g(D("100"), "linear", D("100"), D("110")) == 100 and g(D("105"), "linear", D("100"), D("110")) == 50
    assert g(D("111"), "linear", D("100"), D("110")) == 0 and g(D("90"), "linear", D("100"), D("110")) == 100
    # mai mult e mai bine: 100 % la ≥ 100, 0 la ≤ 80
    assert g(D("90"), "linear", D("100"), D("80")) == 50 and g(D("80"), "linear", D("100"), D("80")) == 0
    assert g(D("100"), "linear", D("100"), D("80")) == 100
    # pragul
    assert g(D("0"), "step", D("0"), D("2")) == 100 and g(D("1"), "step", D("0"), D("2")) == 0
    assert g(D("95"), "step", D("95"), D("0")) == 100 and g(D("94.99"), "step", D("95"), D("0")) == 0
    assert g(D("3"), "linear", D("3"), D("3")) == 100 and g(D("4"), "linear", D("3"), D("3")) == 0


def test_trip_fuel_from_tank_manual_and_norm(admin_client, fleet):  # noqa: F811
    _e, job = person(fleet, "Ceban", "Costel")
    rate(admin_client, "1.50")
    fleet["truck"].fuel_norm = D("30")
    fleet["truck"].save()
    t = trip(admin_client, job, fleet["truck"], km="1000", fuel_out="200", fuel_added="150", fuel_in="35", fuel_adj_pct="5")
    assert D(t["fuel_used"]) == D("315") and t["fuel_source"] == "tank" and D(t["fuel_norm_l"]) == D("315")
    assert t["totals"]["fuel_pct"] == 100.0
    # consumul scris de mână (fără rămășițe); golit — se ia din GPS (aici nu e nimic)
    r = admin_client.patch(f"/api/transport/trips/{t['id']}/", {"fuel_out": None, "fuel_in": None, "fuel_added": None,
                                                                "fuel_used": "290"}, format="json")
    assert r.status_code == 200 and D(r.data["fuel_used"]) == D("290") and r.data["fuel_source"] == "manual"
    r = admin_client.patch(f"/api/transport/trips/{t['id']}/", {"fuel_used": None}, format="json")
    assert r.data["fuel_used"] is None and r.data["fuel_source"] == ""
    # rămășița la întoarcere mai mare decât ce a fost — problemă; litri negativi — respinși
    r = admin_client.patch(f"/api/transport/trips/{t['id']}/", {"fuel_out": "50", "fuel_in": "80"}, format="json")
    assert any("rămășița la întoarcere" in p for p in r.data["problems"])
    assert admin_client.patch(f"/api/transport/trips/{t['id']}/", {"fuel_added": "-1"}, format="json").status_code == 400
    # fără norma vehiculului — fără consum normat
    fleet["truck"].fuel_norm = None
    fleet["truck"].save()
    r = admin_client.patch(f"/api/transport/trips/{t['id']}/", {"fuel_out": "200", "fuel_in": "35"}, format="json")
    assert r.data["fuel_norm_l"] is None and r.data["totals"]["fuel_pct"] is None


def gps_csv(text, encoding="cp1251"):
    return SimpleUploadedFile("export.csv", text.encode(encoding), "text/csv")


def test_gps_import_csv_and_trip(admin_client, fleet):  # noqa: F811
    _e, job = person(fleet, "Ceban", "Costel")
    rate(admin_client, "1.50")
    truck = fleet["truck"]
    r = admin_client.patch(f"/api/transport/vehicles/{truck.pk}/", {"gps_id": "861234567"}, format="json")
    assert r.status_code == 200
    other = fleet["bus"]
    assert admin_client.patch(f"/api/transport/vehicles/{other.pk}/", {"gps_id": "861234567"}, format="json").status_code == 400
    # exportul unui sistem GPS: antetul în rusă, „;”, Windows-1251, unitățile în celule, ora „hh:mm”, data cu ora
    text = ("Объект;Дата;Пробег;Время в движении;Моточасы;Начало движения;Конец движения;Расход топлива;Страны\n"
            "861234567;02.03.2026 00:00:00;640,5 км;8:15;9:40;06:05;19:40;201,2 л;MD, RO\n"
            "ABC123;03.03.2026;612;7,5;;05:50;18:10;190;RO HU\n"
            "NEXISTENT;03.03.2026;10;;;;;;\n")
    check = admin_client.post("/api/transport/gps-days/import/", {"file": gps_csv(text), "dry_run": "1"}, format="multipart")
    assert check.status_code == 200 and not check.data["ok"], check.data
    assert [e["row"] for e in check.data["errors"]] == [4] and "NEXISTENT" in check.data["errors"][0]["error"]
    assert not GpsDay.objects.exists()
    text = "\n".join(text.splitlines()[:3]) + "\n"
    done = admin_client.post("/api/transport/gps-days/import/", {"file": gps_csv(text), "dry_run": "0"}, format="multipart")
    assert done.data["saved"] and done.data["created"] == 2
    d1 = GpsDay.objects.get(vehicle=truck, day="2026-03-02")
    assert d1.km == D("640.5") and d1.moving_min == 495 and d1.engine_min == 580 and str(d1.first_start) == "06:05:00"
    assert d1.fuel_l == D("201.2") and d1.countries == "MD,RO" and d1.source == "export.csv"
    d2 = GpsDay.objects.get(vehicle=truck, day="2026-03-03")
    assert d2.moving_min == 450 and d2.countries == "RO,HU"
    # din nou — km și coloanele din fișier se înlocuiesc, celelalte rămân; același vehicul și zi de două ori — eroare
    again = admin_client.post("/api/transport/gps-days/import/", {"file": gps_csv(
        "Vehicle;Date;Mileage\nABC 123;02.03.2026;641\n", "utf-8"), "dry_run": "0"}, format="multipart")
    assert again.data["updated"] == 1
    d1.refresh_from_db()
    assert d1.km == D("641") and d1.fuel_l == D("201.2") and d1.countries == "MD,RO"
    twice = admin_client.post("/api/transport/gps-days/import/", {"file": gps_csv(
        "Vehicle,Date,Mileage\nABC 123,02.03.2026,641\nABC 123,02.03.2026,10\n", "utf-8"), "dry_run": "1"}, format="multipart")
    assert "de două ori" in twice.data["errors"][0]["error"]
    # foaia de parcurs pe 02–03.03: km din GPS 641 + 612; foaia are 1000 km — avertisment; consumul — din GPS (foaia n-are)
    fleet["truck"].fuel_norm = D("30")
    fleet["truck"].save()
    t = trip(admin_client, job, truck, dep="2026-03-02T06:00:00+02:00", arr="2026-03-03T19:00:00+02:00", km="1000")
    info = admin_client.get(f"/api/transport/trips/{t['id']}/gps/").data
    assert info["km"] == 1253.0 and info["missing"] == [] and info["countries"] == ["MD", "RO", "HU"]
    assert info["fuel"] == 391.2 and t["fuel_source"] == "gps" and D(t["fuel_used"]) == D("391.2")
    assert any(w.startswith("GPS: în foaia de parcurs 1000 km") for w in t["warnings"])
    r = admin_client.patch(f"/api/transport/trips/{t['id']}/", {"km": "1250"}, format="json")
    assert not any(w.startswith("GPS: în foaia") for w in r.data["warnings"])
    # ziua fără combustibil — consumul GPS nu e complet
    GpsDay.objects.filter(pk=d1.pk).update(fuel_l=None)
    r = admin_client.patch(f"/api/transport/trips/{t['id']}/", {"km": "1251"}, format="json")
    assert r.data["fuel_used"] is None and r.data["fuel_source"] == ""
    # o zi fără GPS
    r = admin_client.patch(f"/api/transport/trips/{t['id']}/", {"arrival": "2026-03-04T10:00:00+02:00"}, format="json")
    assert any("lipsesc zilele 04.03" in w for w in r.data["warnings"]) and r.data["fuel_source"] == ""
    # șablonul și lista
    assert admin_client.get("/api/transport/gps-days/import/template/").status_code == 200
    rows = admin_client.get("/api/transport/gps-days/", {"vehicle": truck.pk, "month": "2026-03"}).data
    assert [x["day"] for x in rows] == ["2026-03-02", "2026-03-03"]


def driver_trips(api, fleet, job):
    """Două curse aprobate în martie: consumul 105 % din normă; actele — una la timp, una nepredată (termenul trecut)."""
    rate(api, "1.50")
    fleet["truck"].fuel_norm = D("30")
    fleet["truck"].save()
    a = trip(api, job, fleet["truck"], km="1000", fuel_out="200", fuel_added="150", fuel_in="35",
             docs_submitted="2026-03-04")
    b = trip(api, job, fleet["truck"], dep="2026-03-10T06:00:00+02:00", arr="2026-03-10T20:00:00+02:00", km="500")
    approve(api, a)
    approve(api, b)


def setup_scheme(api, fleet, **kw):
    scheme = KpiScheme.objects.get(code="SOFERI")
    r = api.patch(f"/api/transport/kpi-schemes/{scheme.pk}/", {"base_amount": "1000", **kw}, format="json")
    assert r.status_code == 200, r.data
    r = api.post("/api/transport/kpi-assignments/", {"scheme": scheme.pk, "occupation": fleet["doctor"].pk,
                                                    "date_from": "2026-01-01"}, format="json")
    assert r.status_code == 201, r.data
    return scheme


def new_sheet(api, month=3):
    r = api.post("/api/transport/kpi-sheets/", {"year": 2026, "month": month}, format="json")
    assert r.status_code == 201, r.data
    r = api.post(f"/api/transport/kpi-sheets/{r.data['id']}/fill/")
    assert r.status_code == 200, r.data
    return r.data


def test_kpi_sheet_fill_override_approve_and_payroll(admin_client, fleet):  # noqa: F811
    e, job = person(fleet, "Ceban", "Costel")
    driver_trips(admin_client, fleet, job)
    for body in ({"kind": "damage_cargo", "date": "2026-03-05", "amount": "1200"},
                 {"kind": "damage_vehicle", "date": "2026-03-06", "at_fault": False},  # nu din vina lui — nu se numără
                 {"kind": "fine", "date": "2026-02-27"}):  # altă lună
        assert admin_client.post("/api/transport/incidents/", {"employee": e.pk, **body}, format="json").status_code == 201
    other_e, other = person(fleet, "Rusu", "Ion", occ="nurse")  # funcția fără schemă — nu intră
    scheme = setup_scheme(admin_client, fleet)
    sheet = new_sheet(admin_client)
    assert sheet["number"].startswith("KP") and len(sheet["lines"]) == 1
    line = sheet["lines"][0]
    by = {d["code"]: d for d in line["details"]}
    assert by["CONSUM"]["value"] == 105.0 and by["CONSUM"]["score"] == 50.0
    assert by["DAUNE"]["value"] == 1.0 and by["DAUNE"]["score"] == 50.0
    assert by["AMENZI"]["value"] == 0.0 and by["AMENZI"]["score"] == 100.0
    assert by["ACTE"]["value"] == 50.0 and by["ACTE"]["score"] == 0.0 and "1 din 2" in by["ACTE"]["how"]
    assert by["TAHO"]["value"] is None and by["TAHO"]["score"] is None  # fără card — nu intră în punctaj
    # (40 × 50 + 20 × 50 + 10 × 100 + 15 × 0) / 85
    assert D(line["score"]) == D("47.06") and D(line["amount"]) == D("470.60") and D(line["base"]) == D("1000")
    # valoarea scrisă de mână rămâne la completarea din nou
    r = admin_client.post(f"/api/transport/kpi-sheets/{sheet['id']}/line/", {"line": line["id"], "overrides": {"ACTE": "100"}},
                          format="json")
    assert r.status_code == 200
    again = admin_client.post(f"/api/transport/kpi-sheets/{sheet['id']}/fill/").data["lines"][0]
    assert again["overrides"] == {"ACTE": "100"} and D(again["score"]) == D("64.71") and D(again["amount"]) == D("647.10")
    assert admin_client.post(f"/api/transport/kpi-sheets/{sheet['id']}/line/", {"line": line["id"], "overrides": {"NU": "1"}},
                             format="json").status_code == 400
    # aprobarea → prima în salariul lunii
    assert admin_client.post(f"/api/transport/kpi-sheets/{sheet['id']}/approve/").status_code == 200
    got = items(2026, 3, job)
    assert got["KPI"].amount == D("647.10") and "fișa KPI" in got["KPI"].note
    assert "KPI" not in items(2026, 3, other)
    pt = PayType.objects.get(code="KPI")
    assert pt.taxable and pt.cas and pt.in_average
    # pe timpul lucrat: o zi lucrătoare absentă în pontaj — prima scade în aceeași proporție ca salariul de funcție
    timesheet(fleet, [(e, 31, "A", None)])
    got = items(2026, 3, job)
    share = got["SAL"].amount / D("14660")
    assert share < 1 and abs(got["KPI"].amount - D("647.10") * share) <= D("0.02") and "% lucrat din normă" in got["KPI"].note
    # evenimentul lunii aprobate nu se mai schimbă; fișa aprobată nu se completează
    inc = admin_client.get("/api/transport/incidents/", {"month": "2026-03"}).data[0]
    assert admin_client.delete(f"/api/transport/incidents/{inc['id']}/").status_code == 400
    assert admin_client.post(f"/api/transport/kpi-sheets/{sheet['id']}/fill/").status_code == 400
    # a doua fișă pe aceeași lună nu se aprobă pentru același șofer
    dup = new_sheet(admin_client)
    r = admin_client.post(f"/api/transport/kpi-sheets/{dup['id']}/approve/")
    assert r.status_code == 400 and "are deja prima KPI" in str(r.data)
    # tiparul
    assert admin_client.get(f"/api/transport/kpi-sheets/{sheet['id']}/print/").status_code == 200
    # anularea → prima iese din salariu
    assert admin_client.post(f"/api/transport/kpi-sheets/{sheet['id']}/unapprove/").status_code == 200
    assert "KPI" not in items(2026, 3, job)
    _ = scheme, other_e


def test_kpi_threshold_pct_base_and_personal_scheme(admin_client, fleet):  # noqa: F811
    e, job = person(fleet, "Ceban", "Costel", salary="10000")
    driver_trips(admin_client, fleet, job)
    setup_scheme(admin_client, fleet, min_score="60")
    line = new_sheet(admin_client)["lines"][0]  # (40 × 50 + 20 × 100 + 10 × 100 + 15 × 0) / 85
    assert D(line["score"]) == D("58.82") and D(line["amount"]) == 0 and "sub pragul" in line["note"]
    # schema pe raportul de muncă are întâietate față de cea pe funcție: 10 % din salariul de funcție, doar consumul
    r = admin_client.post("/api/transport/kpi-schemes/", {"code": "PERS", "name": "Personală", "base_kind": "pct", "base_pct": "10",
                                                         "items": [{"indicator": _ind("CONSUM"), "weight": "1", "mode": "step",
                                                                    "full_at": "106"}]}, format="json")
    assert r.status_code == 201, r.data
    assert admin_client.post("/api/transport/kpi-assignments/", {"scheme": r.data["id"], "employment": job.pk,
                                                                "date_from": "2026-03-01"}, format="json").status_code == 201
    line = new_sheet(admin_client)["lines"][0]
    assert line["scheme_code"] == "PERS" and D(line["base"]) == D("1000") and D(line["score"]) == 100 and D(line["amount"]) == D("1000")
    # aceeași funcție / raport de două ori în aceeași perioadă — respins; nici funcția, nici raportul — respins
    assert admin_client.post("/api/transport/kpi-assignments/", {"scheme": r.data["id"], "employment": job.pk,
                                                                "date_from": "2026-06-01"}, format="json").status_code == 400
    assert admin_client.post("/api/transport/kpi-assignments/", {"scheme": r.data["id"], "date_from": "2026-06-01"},
                             format="json").status_code == 400
    # schema cu baza 0 nu se aprobă
    scheme = KpiScheme.objects.get(code="PERS")
    scheme.base_pct = 0
    scheme.save()
    sheet = new_sheet(admin_client)
    r = admin_client.post(f"/api/transport/kpi-sheets/{sheet['id']}/approve/")
    assert r.status_code == 400 and "n-are baza primei" in str(r.data)
    _ = e


def test_kpi_no_data_and_roles(admin_client, make_user, client_for, fleet):  # noqa: F811
    _e, job = person(fleet, "Ceban", "Costel")
    setup_scheme(admin_client, fleet)
    sheet = new_sheet(admin_client)
    line = sheet["lines"][0]  # fără curse, fără card: doar evenimentele (0) au date — dar schema cere curse
    assert {d["code"] for d in line["details"] if d["score"] is not None} == {"DAUNE", "AMENZI"}
    assert line["score"] is None and D(line["amount"]) == 0 and "Fără curse" in line["note"]
    scheme = KpiScheme.objects.get(code="SOFERI")
    assert admin_client.patch(f"/api/transport/kpi-schemes/{scheme.pk}/", {"needs_trips": False}, format="json").status_code == 200
    line = admin_client.post(f"/api/transport/kpi-sheets/{sheet['id']}/fill/").data["lines"][0]
    assert D(line["score"]) == 100 and D(line["amount"]) == D("1000")
    head = client_for(make_user("sef.coloana", ["department_head"]))
    assert head.get("/api/transport/kpi-sheets/").status_code == 200
    sheet = Trip.objects.none()
    _ = job, sheet


def _ind(code):
    from apps.transport.models import KpiIndicator

    return KpiIndicator.objects.get(code=code).pk


def test_import_reads_csv_and_units():
    from apps.core.excel_import import Column, _cell, _csv_rows

    assert _cell("640,5 km", Column("k", "Km", kind="decimal")) == D("640.5")
    assert _cell("12 l", Column("k", "L", kind="decimal")) == D("12")
    assert _cell("1 234,5", Column("k", "Km", kind="decimal")) == D("1234.5")
    assert _cell("02.03.2026 00:00:00", Column("d", "Data", kind="date")).isoformat() == "2026-03-02"
    with pytest.raises(Exception):
        _cell("doi km", Column("k", "Km", kind="decimal"))
    assert _csv_rows("a\tb\n1\t2\n".encode("utf-8-sig")) == [("a", "b"), ("1", "2")]
    assert _csv_rows("Дата;Пробег\n1;2\n".encode("cp1251"))[0] == ("Дата", "Пробег")
    from apps.core.excel_import import RowError

    for junk, text in ((b"\xd0\xcf\x11\xe0" + b"\x00" * 60, ".xls"), (b"\x89PNG\r\n\x1a\n\x00\x00", "nici text CSV")):
        with pytest.raises(RowError, match=text):
            _csv_rows(junk)
