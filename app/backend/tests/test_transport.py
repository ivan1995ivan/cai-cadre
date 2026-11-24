"""S6b (pasul a) — transportul: vehiculele, tarifele pe km (rândul cel mai potrivit), cursa (foaia de parcurs) cu verificările ei,
actele șoferului, plata pe km în salariu (cu completarea până la salariul minim), importul din Excel, rolurile și modulul.
Diurna pe țări — test_transport_per_diem."""
from datetime import date
from decimal import Decimal

import pytest

from apps.core.models import Company
from apps.org.models import DictItem
from apps.payroll import engine
from apps.payroll.models import Payroll
from apps.staff.models import EmployeeDocument
from apps.transport.models import Country, Trip, Vehicle

from .test_payroll import org, person  # noqa: F401 — fixtura și ajutoarele comune
from .test_staff import xlsx

D = Decimal


@pytest.fixture
def fleet(org):  # noqa: F811
    """Modulul pornit, un cap tractor, o semiremorcă, un autobuz și tarifele pe km."""
    company = Company.get()
    company.transport_enabled = True
    company.save(update_fields=["transport_enabled"])
    org["truck"] = Vehicle.objects.create(plate="ABC 123", kind="tractor", brand="Volvo", category="CE")
    org["trailer"] = Vehicle.objects.create(plate="XYZ 987", kind="trailer", tachograph=False)
    org["bus"] = Vehicle.objects.create(plate="BUS 001", kind="bus", category="D")
    return org


def rate(api, value, **kw):
    r = api.post("/api/transport/km-rates/", {"date_from": "2026-01-01", "rate": value, "trip_kind": "", "scope": "", "vehicle_kind": "", **kw},
                 format="json")
    assert r.status_code == 201, r.data
    return r.data


def trip(api, job, vehicle, *, dep="2026-03-02T06:00:00+02:00", arr="2026-03-02T18:00:00+02:00", km="400", ok=True, **kw):
    body = {"driver": job.id, "vehicle": vehicle.id, "kind": "goods", "scope": "domestic", "departure": dep, "arrival": arr, "km": km,
            "legs": [], **kw}
    r = api.post("/api/transport/trips/", body, format="json")
    if ok:
        assert r.status_code == 201, r.data
    return r.data if ok else r


def approve(api, doc, ok=True):
    r = api.post(f"/api/transport/trips/{doc['id']}/approve/")
    if ok:
        assert r.status_code == 200, r.data
    return r


def items(year, month, job):
    Payroll.objects.filter(year=year, month=month).delete()
    pay = Payroll.objects.create(year=year, month=month)
    engine.calculate(pay)
    return {i.pay_type.code: i for i in pay.lines.get(employment=job).items.select_related("pay_type")}


def test_module_off_by_default_and_roles(admin_client, make_user, client_for, org):  # noqa: F811
    assert Company.get().transport_enabled is False
    assert admin_client.get("/api/transport/trips/").status_code == 403
    assert admin_client.get("/api/public/branding/").data["transport_enabled"] is False
    assert admin_client.patch("/api/company/", {"transport_enabled": True}, format="json").data["transport_enabled"] is True
    acc = client_for(make_user("contabil", ["accountant"]))
    head = make_user("sef.coloana", ["department_head"])
    assert acc.get("/api/transport/trips/").status_code == 200
    assert {"transport.view", "transport.create", "transport.edit"} <= head.permission_codes()
    assert "transport.approve" not in head.permission_codes() and head.data_scope("transport") == "own"


def test_km_rate_best_match_and_history(admin_client, fleet):
    from apps.transport import services

    rate(admin_client, "1.50")
    rate(admin_client, "2.00", scope="international")
    rate(admin_client, "2.20", scope="international", trip_kind="goods", vehicle_kind="tractor")
    rate(admin_client, "1.80", trip_kind="passengers", vehicle_kind="bus")
    rate(admin_client, "2.50", scope="international", trip_kind="goods", vehicle_kind="tractor", date_from="2026-04-01")
    _e, job = person(fleet, "Rusu", "Radu")

    def pick(**kw):
        dep = kw.pop("dep")
        t = Trip(driver=job, vehicle=kw.pop("vehicle", fleet["truck"]), departure=dep, arrival=dep, **kw)
        r = services.km_rate(t)
        return r.rate if r else None

    from datetime import datetime, timezone as tz
    mar, apr = datetime(2026, 3, 5, 8, tzinfo=tz.utc), datetime(2026, 4, 5, 8, tzinfo=tz.utc)
    assert pick(dep=mar, kind="goods", scope="domestic") == D("1.5")
    assert pick(dep=mar, kind="goods", scope="international") == D("2.2")  # cele mai multe potriviri exacte
    assert pick(dep=apr, kind="goods", scope="international") == D("2.5")  # cel nou, din aprilie
    assert pick(dep=mar, kind="passengers", scope="international", vehicle=fleet["bus"]) == D("1.8")


def test_trip_checks_documents_and_km_pay(admin_client, fleet):
    rate(admin_client, "1.50")
    e, job = person(fleet, "Ceban", "Costel", salary="6000")
    # kilometrajul dă km; remorca pe locul vehiculului e greșită; întoarcerea înaintea plecării
    bad = trip(admin_client, job, fleet["trailer"], km="0")
    assert any("e remorcă" in p for p in bad["problems"]) and any("n-are km" in p for p in bad["problems"])
    assert trip(admin_client, job, fleet["truck"], arr="2026-03-01T18:00:00+02:00", ok=False).status_code == 400
    Trip.objects.all().delete()
    doc = trip(admin_client, job, fleet["truck"], odometer_out=120000, odometer_in=120450, km="0")
    assert D(doc["km"]) == D("450") and D(doc["km_amount"]) == D("675") and "450 km × 1,5 lei/km" in doc["how"]
    # actele: lipsesc → avertismente (nu opresc aprobarea); permisul expirat — se vede
    assert any("lipsește permisul de conducere" in w for w in doc["warnings"])
    EmployeeDocument.objects.create(employee=e, doc_type=DictItem.objects.get(kind="document", code="driving_licence"),
                                    expiry_date=date(2026, 2, 1))
    warn = admin_client.get(f"/api/transport/trips/{doc['id']}/").data["warnings"]
    assert any("permisul de conducere a expirat la 01.02.2026" in w for w in warn)
    assert any("cardul de conducător pentru tahograf" in w for w in warn)
    # o cursă suprapusă pentru același șofer oprește aprobarea
    clash = trip(admin_client, job, fleet["bus"], dep="2026-03-02T10:00:00+02:00", arr="2026-03-02T12:00:00+02:00", km="50")
    assert any("are și cursa" in p for p in clash["problems"])
    assert approve(admin_client, clash, ok=False).status_code == 400
    admin_client.delete(f"/api/transport/trips/{clash['id']}/")
    approve(admin_client, doc)
    # salariul: KM 675 lei; salariul de funcție 6 000 + KM 675 ≥ salariul minim 6 300 → fără completare
    pay = items(2026, 3, job)
    assert pay["KM"].amount == D("675") and pay["KM"].quantity == D("450") and doc["number"] in pay["KM"].note
    assert "MINIM" not in pay
    # aprobată — nu se mai modifică; anularea o scoate din calcul
    assert admin_client.patch(f"/api/transport/trips/{doc['id']}/", {"note": "x"}, format="json").status_code == 400
    assert admin_client.post(f"/api/transport/trips/{doc['id']}/unapprove/").status_code == 200
    assert "KM" not in items(2026, 3, job)
    assert admin_client.get(f"/api/transport/trips/{doc['id']}/print/").status_code == 200


def test_no_km_rate_blocks_approval(admin_client, fleet):
    _e, job = person(fleet, "Lungu", "Lucian")
    doc = trip(admin_client, job, fleet["truck"])
    assert any("Nu există tarif pe km" in p for p in doc["problems"])
    assert approve(admin_client, doc, ok=False).status_code == 400


def test_trips_import_from_excel(admin_client, fleet):
    rate(admin_client, "2")
    e, job = person(fleet, "Moraru", "Mihai")
    Country.objects.get_or_create(code="RO", defaults={"name_ro": "România"})
    Country.objects.get_or_create(code="HU", defaults={"name_ro": "Ungaria"})
    head = ["Nr. cursei (în fișier)", "Nr. tabel șofer", "Vehiculul (nr. de înmatriculare)", "Remorca", "Aria (în țară / internațional)",
            "Plecarea (zz.ll.aaaa hh:mm)", "Întoarcerea (zz.ll.aaaa hh:mm)", "Km", "Țara (cod ISO 2)", "Intrarea în țară (zz.ll.aaaa hh:mm)",
            "Ieșirea din țară (zz.ll.aaaa hh:mm)", "Descărcare"]
    url = "/api/transport/trips/import/"
    assert admin_client.get(url + "template/").status_code == 200
    rows = [head,
            ["A1", e.tab_number, "ABC 123", "XYZ 987", "internațional", "02.03.2026 06:00", "06.03.2026 20:00", 2100, "RO",
             "02.03.2026 09:00", "03.03.2026 02:00", "nu"],
            ["A1", "", "", "", "", "", "", "", "HU", "03.03.2026 02:00", "05.03.2026 10:00", "da"],
            ["B2", e.tab_number, "NIMIC", "", "în țară", "10.03.2026 06:00", "10.03.2026 18:00", 300]]
    trial = admin_client.post(url, {"file": xlsx(rows), "dry_run": "1"}, format="multipart").data
    assert not trial["ok"] and "NIMIC nu există" in trial["errors"][0]["error"] and not Trip.objects.exists()
    rows[3][2] = "BUS 001"
    done = admin_client.post(url, {"file": xlsx(rows), "dry_run": "0"}, format="multipart").data
    assert done["saved"], done
    a1 = Trip.objects.get(scope="international")
    assert a1.trailer == fleet["trailer"] and [leg.country.code for leg in a1.legs.all()] == ["RO", "HU"]
    assert a1.legs.get(country__code="HU").unloading is True and a1.km_amount == D("4200")
    assert Trip.objects.get(scope="domestic").vehicle == fleet["bus"]


# --- diurna (HG 10/2012) ------------------------------------------------------------------------------------------------------
def eur(rate="19.5", day=date(2026, 3, 1)):
    from apps.core.models import Currency, ExchangeRate

    ExchangeRate.objects.create(currency=Currency.objects.get(code="EUR"), date=day, rate=D(rate), nominal=1)


def legs(*rows):
    out = []
    for code, entered, left, *flags in rows:
        out.append({"country": Country.objects.get(code=code).id, "entered": entered, "left": left,
                    "loading": "load" in flags, "unloading": "unload" in flags, "meals": "meals" in flags, "km": None})
    return out


def test_per_diem_norms_seeded_from_hg_10_2012(seeded):
    from apps.transport.models import PerDiemNorm

    got = {n.country.code: (n.currency, n.amount) for n in PerDiemNorm.objects.select_related("country")
           if n.country.code in ("MD", "RO", "DE", "HU", "UA", "CH", "US")}
    assert got == {"MD": ("MDL", D("250")), "RO": ("EUR", D("60")), "DE": ("EUR", D("75")), "HU": ("EUR", D("70")),
                   "UA": ("EUR", D("65")), "CH": ("EUR", D("110")), "US": ("USD", D("110"))}
    assert Country.objects.count() == 186  # rândurile anexei, fără cele 7 fără țară proprie (orașe, regiuni)


def test_per_diem_short_stays(admin_client, fleet):
    rate(admin_client, "1")
    eur()
    _e, job = person(fleet, "Iașan", "Ion")
    # Chișinău – Iași – Chișinău: 8 ore în România — 20 % din 60 EUR × 19,5 = 234
    t8 = trip(admin_client, job, fleet["truck"], scope="international", dep="2026-03-02T06:00:00+02:00", arr="2026-03-02T20:00:00+02:00",
              legs=legs(("RO", "2026-03-02T09:00:00+02:00", "2026-03-02T17:00:00+02:00", "unload")))
    assert [(d["country_code"], D(d["pct"]), D(d["amount"])) for d in t8["diems"]] == [("RO", D("20"), D("234"))]
    # 10 ore — 40 %: 468; cu masa asigurată — 20 % (pct. 33)
    t10 = admin_client.patch(f"/api/transport/trips/{t8['id']}/", {"legs": legs(
        ("RO", "2026-03-02T08:00:00+02:00", "2026-03-02T18:00:00+02:00", "unload"))}, format="json").data
    assert [D(d["amount"]) for d in t10["diems"]] == [D("468")] and "pct. 31 lit. b" in t10["diems"][0]["how"]
    meals = admin_client.patch(f"/api/transport/trips/{t8['id']}/", {"legs": legs(
        ("RO", "2026-03-02T08:00:00+02:00", "2026-03-02T18:00:00+02:00", "unload", "meals"))}, format="json").data
    assert [D(d["amount"]) for d in meals["diems"]] == [D("234")]


def test_per_diem_long_trip_transit_destination_and_payroll(admin_client, fleet):
    rate(admin_client, "1")
    eur()
    e, job = person(fleet, "Neagu", "Nicolae", salary="7000")
    _c, co = person(fleet, "Ojog", "Oleg", salary="7000")
    # 02.03 06:00 plecarea; România în tranzit 22 h; Germania — descărcare; înapoi prin România 18 h; 06.03 09:00 sosirea.
    doc = trip(admin_client, job, fleet["truck"], co_driver=co.id, scope="international", km="3600",
               dep="2026-03-02T06:00:00+02:00", arr="2026-03-06T09:00:00+02:00",
               legs=legs(("RO", "2026-03-02T10:00:00+02:00", "2026-03-03T08:00:00+02:00"),
                         ("DE", "2026-03-03T08:00:00+02:00", "2026-03-05T12:00:00+02:00", "unload"),
                         ("RO", "2026-03-05T12:00:00+02:00", "2026-03-06T06:00:00+02:00")))
    mine = [d for d in doc["diems"] if d["employment"] == job.id]
    # 5 zile (ziua plecării și a sosirii incluse, pct. 24), toate cu norma Germaniei (tranzitul sub 24 h — pct. 23; pct. 26):
    # 75 EUR × 19,5 = 1 462,50 pe zi
    assert [(d["day"], d["country_code"], D(d["amount"])) for d in mine] == [
        (f"2026-03-0{n}", "DE", D("1462.5")) for n in range(2, 7)]
    assert "pct. 23" in mine[0]["how"] and len(doc["diems"]) == 10  # și al doilea șofer
    assert doc["totals"]["per_diem"] == 14625.0 and doc["totals"]["per_diem_taxable"] == 0
    # întreprinderea plătește 120 %: partea peste normă e impozabilă; sub 70 % — nu se aprobă (pct. 22¹)
    more = admin_client.patch(f"/api/transport/trips/{doc['id']}/", {"per_diem_pct": "120"}, format="json").data
    assert D(more["diems"][0]["amount"]) == D("1755") and D(more["diems"][0]["taxable"]) == D("292.5")
    low = admin_client.patch(f"/api/transport/trips/{doc['id']}/", {"per_diem_pct": "60"}, format="json").data
    assert any("sub minimul de 70" in p for p in low["problems"])
    admin_client.patch(f"/api/transport/trips/{doc['id']}/", {"per_diem_pct": "120"}, format="json")
    approve(admin_client, doc)
    pay = items(2026, 3, job)
    # diurna în limita normei — neimpozabilă; peste normă — impozabilă; plata pe km
    assert pay["DIURNA"].amount == D("7312.5") and pay["DIURNAEX"].amount == D("1462.5") and pay["KM"].amount == D("3600")
    line = Payroll.objects.get(year=2026, month=3).lines.get(employment=job)
    assert line.taxable == line.gross - D("7312.5")
    assert "DIURNA" in items(2026, 3, co)


def test_per_diem_needs_exchange_rate_and_domestic_rule(admin_client, fleet):
    from apps.payroll.models import PayConstant

    rate(admin_client, "1")
    _e, job = person(fleet, "Pavel", "Petru")
    doc = trip(admin_client, job, fleet["truck"], scope="international", dep="2026-03-02T06:00:00+02:00", arr="2026-03-04T20:00:00+02:00",
               legs=legs(("HU", "2026-03-02T12:00:00+02:00", "2026-03-04T12:00:00+02:00", "unload")))
    assert any("Lipsește cursul BNM pentru EUR la 01.03.2026" in p for p in doc["problems"]) and not doc["diems"]
    # cursa în țară: fără diurnă (pct. 3); cu setarea — 250 lei pe zi, doar la mai multe zile (pct. 24)
    dom = trip(admin_client, job, fleet["bus"], dep="2026-03-10T06:00:00+02:00", arr="2026-03-11T20:00:00+02:00")
    assert dom["diems"] == []
    PayConstant.objects.filter(code="per_diem_domestic_pay").update(value=D("1"))
    again = admin_client.patch(f"/api/transport/trips/{dom['id']}/", {"note": "x"}, format="json").data
    assert [D(d["amount"]) for d in again["diems"]] == [D("250"), D("250")]
    one = trip(admin_client, job, fleet["bus"], dep="2026-03-12T06:00:00+02:00", arr="2026-03-12T20:00:00+02:00")
    assert one["diems"] == []
