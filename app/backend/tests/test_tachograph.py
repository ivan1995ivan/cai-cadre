"""S6b (pasul b) — tahograful: citirea descărcării cardului de conducător (generația 1 și 2, construite aici după anexa 1B / 1C),
limitele de conducere și odihnă (AETR art. 6–8), încărcarea și legarea de angajat, zilele, cursa (timpii, avertismentele, țările
din trecerile frontierei) și alertele.

Fișierele de test sunt construite după specificație — de verificat și pe descărcări reale (`app/PLAN-SRL.md`)."""
import struct
from datetime import date, datetime, timedelta, timezone

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.org.models import DictItem
from apps.staff.models import EmployeeDocument
from apps.transport import ddd, tacho, tacho_rules
from apps.transport.models import TachoDay, TachoEvent, TachoFile, Trip

from .test_payroll import org, person  # noqa: F401
from .test_transport import fleet, rate  # noqa: F401

UTC = timezone.utc
ACT = {"R": 0, "A": 1, "W": 2, "D": 3}


# --- construirea fișierelor ---------------------------------------------------------------------------------------------
def _name(text, cp=1):
    return bytes([cp]) + text.encode(f"iso8859_{cp}").ljust(35, b" ")


def _t(dt):
    return struct.pack(">I", int(dt.timestamp())) if dt else b"\x00" * 4


def _bcd(n, width):
    s = str(n).rjust(width * 2, "0")
    return bytes(int(s[i]) << 4 | int(s[i + 1]) for i in range(0, len(s), 2))


def _tag(fid, app, value):
    return struct.pack(">HBH", fid, app, len(value)) + value


def change(minute, act, crew=False, inserted=True, manual=False):
    c = (1 if crew else 0) if inserted else (1 if manual else 0)
    return struct.pack(">H", (c << 14) | ((0 if inserted else 1) << 13) | (ACT[act] << 11) | minute)


def day_record(day, changes, distance=0, presence=1, prev=0):
    body = _t(datetime(day.year, day.month, day.day, tzinfo=UTC)) + _bcd(presence, 2) + struct.pack(">H", distance)
    body += b"".join(changes)
    return struct.pack(">HH", prev, 4 + len(body)) + body


def activity_ef(records, size=4000, start=None):
    """Tamponul circular: înregistrările puse una după alta de la `start` (implicit aproape de capăt — ca să se întoarcă)."""
    buf = bytearray(size)
    pos = start if start is not None else size - 30
    oldest, newest, prev = pos, pos, 0
    for day, changes, dist in records:
        rec = bytearray(day_record(day, changes, dist, prev=prev))
        newest = pos
        for i, b in enumerate(rec):
            buf[(pos + i) % size] = b
        prev = len(rec)
        pos = (pos + len(rec)) % size
    return struct.pack(">HH", oldest, newest) + bytes(buf)


def ident_ef(number, surname, first, birth, expiry=date(2029, 5, 1)):
    card = (bytes([0x23]) + number.encode().ljust(16) + _name("ASP") + _t(datetime(2024, 5, 2, tzinfo=UTC))
            + _t(datetime(2024, 5, 2, tzinfo=UTC)) + _t(datetime(expiry.year, expiry.month, expiry.day, tzinfo=UTC)))
    holder = _name(surname, 2) + _name(first, 2) + _bcd(birth.year, 2) + _bcd(birth.month, 1) + _bcd(birth.day, 1) + b"ro"
    return card + holder


def vehicles_ef(rows, gen=1):
    out = struct.pack(">H", len(rows) - 1 if rows else 0)
    for first, last, plate, odo_b, odo_e in rows:
        rec = (odo_b.to_bytes(3, "big") + odo_e.to_bytes(3, "big") + _t(first) + _t(last) + bytes([0x23])
               + bytes([1]) + plate.encode().ljust(13) + b"\x00\x01")
        out += rec + (b"V" * 17 if gen == 2 else b"")
    out += (b"\x00" * (48 if gen == 2 else 31)) * 2  # înregistrări goale
    return out


def places_ef(rows, gen=1):
    out = struct.pack(">H", len(rows)) if gen == 2 else bytes([len(rows)])
    for at, kind, country, odo in rows:
        rec = _t(at) + bytes([kind, country, 0]) + odo.to_bytes(3, "big")
        out += rec + (b"\x00" * 11 if gen == 2 else b"")
    return out


def borders_ef(rows):
    out = struct.pack(">H", len(rows))
    for at, left, entered, odo in rows:
        out += bytes([left, entered]) + _t(at) + b"\x01" + b"\x00" * 6 + b"\x01" + odo.to_bytes(3, "big")
    return out


def loads_ef(rows):
    out = struct.pack(">H", len(rows))
    for at, kind, odo in rows:
        out += _t(at) + bytes([kind]) + _t(at) + b"\x01" + b"\x00" * 6 + b"\x01" + odo.to_bytes(3, "big")
    return out


def card_file(number="D0000123456700", surname="Ceban", first="Costel", birth=date(1985, 6, 15), days=(), vehicles=(),
              places=(), gen=1, borders=(), loads=(), downloaded=None):
    number = number if len(number) == 16 else number + "00"
    app = 2 if gen == 2 else 0
    out = _tag(0x0002, 0, b"\x00" * 25) + _tag(0x0005, 0, b"\x00" * 8)
    if gen == 2:  # partea de generația 1 de pe cardul G2 + versiunea 2
        out += _tag(0x0501, 0, bytes([1]) + b"\x00" * 9) + _tag(0x0520, 0, ident_ef(number, surname, first, birth))
        out += _tag(0x0525, 2, b"\x00" * 4)
    out += _tag(0x0501, app, bytes([1]) + b"\x00" * (16 if gen == 2 else 9))
    out += _tag(0x0520, app, ident_ef(number, surname, first, birth)) + _tag(0x0520, app + 1, b"\x00" * 64)
    out += _tag(0x050E, app, _t(downloaded))
    out += _tag(0x0521, app, _name("ASP") + bytes([0x23]) + b"MD123456".ljust(16))
    out += _tag(0x0504, app, activity_ef(list(days)))
    out += _tag(0x0505, app, vehicles_ef(list(vehicles), gen)) + _tag(0x0506, app, places_ef(list(places), gen))
    if gen == 2:
        out += _tag(0x0528, 2, borders_ef(list(borders))) + _tag(0x0529, 2, loads_ef(list(loads)))
    return out


def shift(day, drive_from=6 * 60, blocks=(("D", 240), ("R", 45), ("D", 240), ("W", 30))):
    """Schimbările zilei: odihnă până la `drive_from`, apoi blocurile, apoi odihnă."""
    out, m = [change(0, "R")], drive_from
    for act, minutes in blocks:
        out.append(change(m, act))
        m += minutes
    out.append(change(m, "R"))
    return out


def timeline(start, parts):
    """Intervalele pentru reguli: [(act, minute), …] puse una după alta de la `start`."""
    out, t = [], start
    for act, minutes in parts:
        out.append((t, t + timedelta(minutes=minutes), act, False))
        t += timedelta(minutes=minutes)
    return out, t


def codes(found):
    return [f.code for f in found]


# --- citirea -------------------------------------------------------------------------------------------------------------
def test_parse_generation_1_card_with_wrapped_buffer():
    d1, d2 = date(2026, 3, 2), date(2026, 3, 3)
    data = card_file(days=[(d1, shift(d1), 610), (d2, [change(0, "R"), change(300, "D", crew=True), change(400, "R", inserted=False),
                                                     change(500, "W", inserted=False, manual=True), change(560, "R")], 120)],
                     vehicles=[(datetime(2026, 3, 2, 6, tzinfo=UTC), datetime(2026, 3, 3, 9, tzinfo=UTC), "ABC 123", 120000, 120730)],
                     places=[(datetime(2026, 3, 2, 6, tzinfo=UTC), 0, 0x23, 120000), (datetime(2026, 3, 2, 15, tzinfo=UTC), 1, 0x29, 120610)],
                     downloaded=datetime(2026, 3, 3, 12, tzinfo=UTC))
    card = ddd.parse(data)
    assert card.generation == 1 and card.card_number == "D000012345670000"
    assert (card.surname, card.first_names, card.birth_date) == ("Ceban", "Costel", date(1985, 6, 15))
    assert card.expiry_date == date(2029, 5, 1) and card.card_nation == "MD" and card.licence_number == "MD123456"
    assert [d.day for d in card.days] == [d1, d2] and card.days[0].distance == 610
    first = card.days[0].spans
    assert first[0][:3] == (0, 360, "R") and first[1][:3] == (360, 600, "D") and first[-1][:3] == (915, 1440, "R")
    second = card.days[1].spans
    assert second[1][:4] == (300, 400, "D", True)  # în echipaj
    assert second[2][2] == "U" and second[3][2] == "W" and second[3][5] is True  # fără card / introdus de mână
    assert card.vehicles[0]["plate"] == "ABC 123" and card.vehicles[0]["odometer_end"] == 120730
    assert [(p["kind"], p["country"]) for p in card.places] == [("begin", "MD"), ("end", "RO")]
    assert card.last_download == datetime(2026, 3, 3, 12, tzinfo=UTC)


def test_parse_generation_2_with_borders_and_loads():
    d1 = date(2026, 3, 2)
    data = card_file(gen=2, days=[(d1, shift(d1), 500)],
                     vehicles=[(datetime(2026, 3, 2, 6, tzinfo=UTC), None, "ABC 123", 1, 501)],
                     borders=[(datetime(2026, 3, 2, 9, tzinfo=UTC), 0x23, 0x29, 200), (datetime(2026, 3, 2, 14, tzinfo=UTC), 0x29, 0x18, 480)],
                     loads=[(datetime(2026, 3, 2, 15, tzinfo=UTC), 2, 490)])
    card = ddd.parse(data)
    assert card.generation == 2 and card.version == 2 and len(card.days) == 1
    assert [(b["left"], b["entered"]) for b in card.borders] == [("MD", "RO"), ("RO", "HU")]
    assert card.loads[0]["kind"] == "unload" and card.vehicles[0]["plate"] == "ABC 123"


def test_not_a_driver_card():
    with pytest.raises(ddd.DddError):
        ddd.parse(b"\x76\x21" + b"\x00" * 200)  # descărcarea vehiculului
    with pytest.raises(ddd.DddError):
        ddd.parse(card_file()[:300])  # trunchiat
    workshop = card_file().replace(_tag(0x0501, 0, bytes([1]) + b"\x00" * 9), _tag(0x0501, 0, bytes([2]) + b"\x00" * 9))
    with pytest.raises(ddd.DddError, match="atelier"):
        ddd.parse(workshop)


# --- regulile ------------------------------------------------------------------------------------------------------------
START = datetime(2026, 3, 2, 0, 0, tzinfo=UTC)  # luni


def run(parts, start=START, pad_rest=0):
    spans, end = timeline(start, [("R", 12 * 60)] + list(parts) + ([("R", pad_rest)] if pad_rest else []))
    return tacho_rules.analyze(spans, start, end)


def test_continuous_driving_and_split_break():
    assert "continuous" in codes(run([("D", 300), ("R", 60)]))
    assert "continuous" not in codes(run([("D", 270), ("R", 45), ("D", 200), ("R", 660)]))
    # 15 + 30: împărțită corect
    assert "continuous" not in codes(run([("D", 120), ("R", 15), ("D", 150), ("R", 30), ("D", 200), ("R", 660)]))
    # 30, apoi 15 — a doua parte e prea scurtă
    assert "continuous" in codes(run([("D", 120), ("R", 30), ("D", 150), ("R", 15), ("D", 100), ("R", 660)]))
    # disponibilitatea nu e pauză
    assert "continuous" in codes(run([("D", 200), ("A", 60), ("D", 100), ("R", 660)]))


def day_of(drive, rest=11 * 60):
    """O zi de 24 de ore: `drive` minute de conducere cu pauzele cerute, altă muncă până la odihnă, odihna `rest`."""
    parts, left = [], drive
    while left > 0:
        chunk = min(240, left)
        parts += [("D", chunk), ("R", 45)]
        left -= chunk
    used = sum(m for _a, m in parts)
    if used + rest < 24 * 60:
        parts.append(("W", 24 * 60 - rest - used))
    return parts + [("R", rest)]


def test_daily_driving_and_extensions():
    assert "daily_driving" in codes(run(day_of(630, rest=9 * 60)))
    found = run(day_of(570, rest=10 * 60) * 3 + day_of(480))
    assert codes(found).count("daily_extension") == 1 and "daily_driving" not in codes(found)


def test_weekly_and_biweekly_driving():
    five = day_of(540, rest=10 * 60) * 2 + day_of(480) * 3
    assert not {"weekly_driving", "biweekly_driving"} & set(codes(run(five + [("R", 46 * 60)])))
    # 6 zile × 9 h 30 min = 57 h în săptămână
    heavy = day_of(570, rest=12 * 60) * 6
    found = run(heavy + [("R", 46 * 60)] + day_of(540, rest=12 * 60) * 5)
    assert "weekly_driving" in codes(found) and "biweekly_driving" in codes(found)


def test_daily_rest_reduced_split_and_insufficient():
    assert "daily_rest" in codes(run([("D", 240), ("R", 45), ("D", 240), ("W", 6 * 60), ("R", 8 * 60), ("D", 60), ("R", 11 * 60)]))
    # 3 h + 9 h — odihna împărțită, nu redusă
    split = [("D", 240), ("R", 3 * 60), ("D", 240), ("R", 45), ("W", 75), ("R", 9 * 60)]
    assert not [c for c in codes(run(split * 5)) if c.startswith("daily_rest")]
    # odihne reduse (9 h 30 min) la rând — a patra e prea mult
    reduced = [("D", 240), ("R", 45), ("D", 240), ("W", 315), ("R", 9 * 60 + 30)]
    found = run(reduced * 5)
    assert codes(found).count("daily_rest_reduced") >= 1


def week(rest):
    """Cinci zile de lucru; ultima odihnă (cea săptămânală) are exact `rest` minute."""
    return day_of(480) * 4 + day_of(480)[:-1] + [("R", rest)]


def test_compliant_schedule_has_no_findings():
    # trei săptămâni calendaristice: luni–vineri 8–10 h de conducere (cel mult două prelungiri), odihna de la vineri seara
    # până luni dimineața (59 h) — nimic de semnalat
    ext = day_of(600, rest=11 * 60) * 2 + day_of(480) * 2 + day_of(480)[:-1] + [("R", 59 * 60)]
    assert run(ext + week(59 * 60) * 2) == []


def test_rests_cut_by_the_data_edges_are_not_judged():
    # datele încep cu o odihnă (de fapt mai lungă, de dinaintea descărcării) și se termină cu una (descărcarea în timpul ei):
    # lungimea lor reală nu se știe — nu sunt „odihne săptămânale reduse”
    spans, end = timeline(START, [("R", 28 * 60)] + day_of(480) * 4 + day_of(480)[:-1] + [("R", 30 * 60)])
    found = tacho_rules.analyze(spans, START, end)
    assert not {"weekly_reduced_twice", "weekly_compensation", "compensation_due"} & set(codes(found))


def test_weekly_rest_rules():
    assert "weekly_rest_late" in codes(run(day_of(480) * 7))
    # două odihne săptămânale reduse la rând
    found = run(week(25 * 60) + week(26 * 60) + week(46 * 60))
    assert "weekly_reduced_twice" in codes(found)
    # redusă (25 h), fără compensare până la sfârșitul săptămânii a treia
    found = run(week(25 * 60) + week(45 * 60) * 4)
    assert "weekly_compensation" in codes(found)
    # compensată: o odihnă săptămânală de 45 + 20 h
    found = run(week(25 * 60) + week(65 * 60) + week(45 * 60) * 3)
    assert "weekly_compensation" not in codes(found)
    # termenul încă nu a trecut — de urmărit
    found = run(week(25 * 60) + day_of(480) * 2)
    due = [f for f in found if f.code == "compensation_due"]
    assert due and all(f.level == "info" for f in due)


# --- încărcarea și ecranele --------------------------------------------------------------------------------------------
def upload(api, *files):
    body = {"files": [SimpleUploadedFile(name, data, "application/octet-stream") for name, data in files]}
    r = api.post("/api/transport/tacho-files/upload/", body, format="multipart")
    assert r.status_code == 200, r.data
    return r.data["results"]


def card_doc(e, number):
    return EmployeeDocument.objects.create(employee=e, doc_type=DictItem.objects.get(kind="document", code="tachograph_card"),
                                           number=number)


def rows_of(data):
    return data["results"] if isinstance(data, dict) else data


def test_upload_match_assign_and_rebuild(admin_client, fleet):  # noqa: F811
    e, _job = person(fleet, "Ceban", "Costel")
    card_doc(e, "D0000123456700")
    d1, d2, d3 = date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 4)
    first = card_file(days=[(d1, shift(d1), 610), (d2, [change(0, "R"), change(360, "D")], 50)],
                      downloaded=datetime(2026, 3, 3, 7, tzinfo=UTC))
    later = card_file(days=[(d2, shift(d2), 600), (d3, shift(d3), 590)], downloaded=datetime(2026, 3, 5, 7, tzinfo=UTC))
    res = upload(admin_client, ("C_1.ddd", first), ("C_2.ddd", later), ("bad.ddd", b"nimic"))
    assert [r["status"] for r in res] == ["created", "created", "error"] and res[0]["employee"] == e.pk
    assert upload(admin_client, ("again.ddd", first))[0]["status"] == "duplicate"
    days = {d.day: d for d in TachoDay.objects.filter(employee=e)}
    assert set(days) == {d1, d2, d3} and days[d2].distance == 600 and days[d2].driving == 480  # ziua din descărcarea nouă
    assert len(rows_of(admin_client.get("/api/transport/tacho-files/").data)) == 2
    # ștergerea celei noi — ziua 2 revine la cea veche
    newer = TachoFile.objects.get(pk=res[1]["file"])
    assert admin_client.post(f"/api/transport/tacho-files/{newer.pk}/remove/").status_code == 204
    assert TachoDay.objects.get(employee=e, day=d2).distance == 50 and not TachoDay.objects.filter(day=d3).exists()
    # descărcarea rămasă e din 03.03 07:00 UTC (09:00 la Chișinău): după ora ei cardul nu știe nimic — ziua se oprește acolo
    rows = {x["day"]: x for x in admin_client.get("/api/transport/tacho/days/", {"employee": e.pk, "month": "2026-03"}).data["days"]}
    last = rows[d2]
    assert last["spans"][-1][1] == 9 * 60
    assert sum(last[k] for k in ("driving", "work", "availability", "rest", "unknown")) == 9 * 60
    assert not rows[d3]["has_data"]
    # originalul se descarcă doar prin API
    r = admin_client.get(f"/api/transport/tacho-files/{res[0]['file']}/original/")
    assert r.status_code == 200 and b"".join(r.streaming_content) == first
    assert TachoFile.objects.get(pk=res[0]["file"]).file.name.startswith("private/tachograph/")


def test_match_by_name_adds_card_and_manual_assign(admin_client, fleet):  # noqa: F811
    e, _ = person(fleet, "Țurcanu", "Ștefan")
    e.birth_date = date(1990, 1, 20)
    e.save(update_fields=["birth_date"])
    one = card_file(number="D0000999999900", surname="TURCANU", first="STEFAN ION", birth=date(1990, 1, 20),
                    days=[(date(2026, 3, 2), shift(date(2026, 3, 2)), 100)])
    res = upload(admin_client, ("c.ddd", one))
    assert res[0]["employee"] == e.pk and "adăugat în dosar" in res[0]["message"]
    doc = EmployeeDocument.objects.get(employee=e, doc_type__code="tachograph_card")
    assert doc.number == "D000099999990000" and doc.expiry_date == date(2029, 5, 1)
    other, _ = person(fleet, "Lungu", "Petru")
    res = upload(admin_client, ("x.ddd", card_file(number="D0000777777700", surname="Necunoscut", first="Ion",
                                                    days=[(date(2026, 3, 2), shift(date(2026, 3, 2)), 80)])))
    assert res[0]["employee"] is None and "alegeți angajatul" in res[0]["message"]
    assert not TachoDay.objects.filter(employee=other).exists()
    r = admin_client.post(f"/api/transport/tacho-files/{res[0]['file']}/assign/", {"employee": other.pk}, format="json")
    assert r.status_code == 200 and r.data["employee"] == other.pk and r.data["matched_by"] == "manual"
    assert TachoDay.objects.filter(employee=other).count() == 1


def test_days_findings_trip_and_alerts(admin_client, fleet):  # noqa: F811
    from apps.alerts import engine

    rate(admin_client, "1.50")
    e, job = person(fleet, "Ceban", "Costel")
    card_doc(e, "D0000123456700")
    d1, d2 = date(2026, 3, 2), date(2026, 3, 3)
    long_day = [change(0, "R"), change(240, "D"), change(570, "R"), change(615, "D"), change(915, "R")]  # 5 h 30 + 5 h
    data = card_file(gen=2, days=[(d1, long_day, 900), (d2, shift(d2), 600)],
                     borders=[(datetime(2026, 3, 2, 8, tzinfo=UTC), 0x23, 0x29, 100), (datetime(2026, 3, 3, 9, tzinfo=UTC), 0x29, 0x23, 1400)],
                     loads=[(datetime(2026, 3, 2, 12, tzinfo=UTC), 1, 300)],
                     downloaded=datetime(2026, 3, 4, 10, tzinfo=UTC))
    upload(admin_client, ("c.ddd", data))
    r = admin_client.get("/api/transport/tacho/days/", {"employee": e.pk, "month": "2026-03"})
    assert r.status_code == 200
    rows = {x["day"]: x for x in r.data["days"]}
    assert rows[d1]["driving"] == 630 and rows[d1]["km"] == 900 and "RO" in rows[d1]["countries"]
    assert {f["code"] for f in rows[d1]["findings"]} >= {"continuous", "daily_driving"}
    assert not rows[date(2026, 3, 20)]["has_data"]
    assert not rows[date(2026, 3, 5)]["has_data"]
    found = admin_client.get("/api/transport/tacho/findings/", {"month": "2026-03"}).data["rows"]
    assert {f["code"] for f in found} >= {"continuous", "daily_driving"} and found[0]["name"] == e.full_name()
    # cursa: timpii, avertismentul, țările din trecerile frontierei
    body = {"driver": job.id, "vehicle": fleet["truck"].id, "kind": "goods", "scope": "international",
            "departure": "2026-03-02T06:00:00+02:00", "arrival": "2026-03-03T18:00:00+02:00", "km": "1500", "legs": []}
    t = admin_client.post("/api/transport/trips/", body, format="json").data
    info = admin_client.get(f"/api/transport/trips/{t['id']}/tacho/").data
    assert info["people"][0]["totals"]["driving"] >= 630 and info["people"][0]["covered"]
    warn = admin_client.get(f"/api/transport/trips/{t['id']}/").data["warnings"]
    assert any("încălcări ale timpului de conducere" in w for w in warn)
    legs = admin_client.get(f"/api/transport/trips/{t['id']}/tacho-legs/").data["legs"]
    assert len(legs) == 1 and legs[0]["country_code"] == "RO" and legs[0]["loading"] is True
    assert legs[0]["left"] == datetime(2026, 3, 3, 9, tzinfo=UTC)
    # fără treceri ale frontierei — eroare clară
    Trip.objects.filter(pk=t["id"]).update(departure=datetime(2026, 3, 10, tzinfo=UTC), arrival=datetime(2026, 3, 11, tzinfo=UTC))
    assert admin_client.get(f"/api/transport/trips/{t['id']}/tacho-legs/").status_code == 400
    # alertele: descărcarea cardului la 28 de zile, încălcările recente
    dl = tacho.download_alerts(date(2026, 3, 30), 7, {})
    assert dl and dl[0].due == date(2026, 4, 1) and dl[0].employee == e.pk
    assert not tacho.download_alerts(date(2026, 3, 10), 7, {})
    inf = tacho.infringement_alerts(date(2026, 3, 5), 14, {})
    assert inf and inf[0].kind == "tacho_infringement" and "Conducere continuă" in inf[0].text
    assert "tacho_download" in engine.KINDS and "tacho_infringement" in engine.KINDS
    assert TachoEvent.objects.filter(employee=e, kind="border").count() == 2


def test_department_head_sees_only_own_drivers(admin_client, make_user, client_for, fleet):  # noqa: F811
    e, _ = person(fleet, "Ceban", "Costel")
    card_doc(e, "D0000123456700")
    upload(admin_client, ("c.ddd", card_file(days=[(date(2026, 3, 2), shift(date(2026, 3, 2)), 100)])))
    api = client_for(make_user("sef.coloana", ["department_head"]))
    assert rows_of(api.get("/api/transport/tacho-files/").data) == []
    assert api.get("/api/transport/tacho/days/", {"employee": e.pk, "month": "2026-03"}).status_code == 400
    assert api.get("/api/transport/tacho/findings/", {"month": "2026-03"}).data["rows"] == []
