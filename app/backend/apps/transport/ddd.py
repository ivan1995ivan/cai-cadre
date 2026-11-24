"""Citirea fișierului descărcat de pe **cardul de conducător** al tahografului digital (.ddd / .esm / .c1b…).

Formatul (descărcarea cardului): un șir de fișiere elementare (EF), fiecare cu eticheta FID (2 octeți) + anexa (1 octet:
00 — date, 01 — semnătură în DF Tachograph (generația 1, anexa 1B la Reg. 3821/85); 02 / 03 — în DF Tachograph_G2 (generația
2, anexa 1C la Reg. (UE) 2016/799)) + lungimea (2 octeți) + conținutul. Pe un card de generația 2 sunt amândouă; se citește G2.

Se citesc: identificarea cardului și a titularului (0520), ultima descărcare (050E), permisul (0521), **activitățile pe zile**
(0504 — tamponul circular CardDriverActivity: pe fiecare zi distanța și schimbările de activitate pe minute, ora UTC), vehiculele
folosite (0505), locurile de început / sfârșit ale perioadei zilnice de muncă (0506) și, la generația 2 versiunea 2, **trecerile
frontierei** (0528) și **încărcările / descărcările** (0529). Semnăturile digitale nu se verifică (se păstrează fișierul
original, pentru control).
"""
import struct
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

UTC = timezone.utc

# NationNumeric (anexa 1B / 1C): codul → (prescurtarea de pe tahograf, ISO 3166-1 alfa-2)
NATIONS = {
    0x01: ("A", "AT"), 0x02: ("AL", "AL"), 0x03: ("AND", "AD"), 0x04: ("ARM", "AM"), 0x05: ("AZ", "AZ"), 0x06: ("B", "BE"),
    0x07: ("BG", "BG"), 0x08: ("BIH", "BA"), 0x09: ("BY", "BY"), 0x0A: ("CH", "CH"), 0x0B: ("CY", "CY"), 0x0C: ("CZ", "CZ"),
    0x0D: ("D", "DE"), 0x0E: ("DK", "DK"), 0x0F: ("E", "ES"), 0x10: ("EST", "EE"), 0x11: ("F", "FR"), 0x12: ("FIN", "FI"),
    0x13: ("FL", "LI"), 0x14: ("FO", "FO"), 0x15: ("UK", "GB"), 0x16: ("GE", "GE"), 0x17: ("GR", "GR"), 0x18: ("H", "HU"),
    0x19: ("HR", "HR"), 0x1A: ("I", "IT"), 0x1B: ("IRL", "IE"), 0x1C: ("IS", "IS"), 0x1D: ("KZ", "KZ"), 0x1E: ("L", "LU"),
    0x1F: ("LT", "LT"), 0x20: ("LV", "LV"), 0x21: ("M", "MT"), 0x22: ("MC", "MC"), 0x23: ("MD", "MD"), 0x24: ("MK", "MK"),
    0x25: ("N", "NO"), 0x26: ("NL", "NL"), 0x27: ("P", "PT"), 0x28: ("PL", "PL"), 0x29: ("RO", "RO"), 0x2A: ("RSM", "SM"),
    0x2B: ("RUS", "RU"), 0x2C: ("S", "SE"), 0x2D: ("SK", "SK"), 0x2E: ("SLO", "SI"), 0x2F: ("TM", "TM"), 0x30: ("TR", "TR"),
    0x31: ("UA", "UA"), 0x32: ("V", "VA"), 0x33: ("YU", "RS"), 0x34: ("MNE", "ME"), 0x35: ("SRB", "RS"), 0x36: ("UZ", "UZ"),
    0x37: ("TJ", "TJ"), 0x38: ("KG", "KG"),
}
SPECIAL_NATIONS = {0x00: "", 0xFD: "EC", 0xFE: "EUR", 0xFF: "WLD"}
ACTIVITIES = "RAWD"  # 00 pauză / odihnă, 01 disponibilitate, 10 altă muncă, 11 conducere; U — necunoscut (fără card)
PLACE_TYPES = {0: "begin", 1: "end", 2: "begin", 3: "end", 4: "begin", 5: "end"}
LOAD_TYPES = {1: "load", 2: "unload", 3: "load_unload"}
KNOWN_FIDS = {0x0002, 0x0005, 0x0501, 0x0502, 0x0503, 0x0504, 0x0505, 0x0506, 0x0507, 0x0508, 0x050E, 0x0520, 0x0521, 0x0522,
              0x0523, 0x0524, 0x0525, 0x0526, 0x0527, 0x0528, 0x0529, 0x0530, 0xC100, 0xC101, 0xC108, 0xC109}


class DddError(ValueError):
    """Fișierul nu e o descărcare validă a cardului de conducător."""


@dataclass
class DayRecord:
    day: date  # ziua tahografului (00:00–24:00 UTC)
    distance: int  # km
    presence: int  # contorul zilelor de prezență
    # intervalele: (minutul de început, minutul de sfârșit, activitatea R/A/W/D/U, echipaj, cardul introdus, introdus manual)
    spans: list = field(default_factory=list)


@dataclass
class CardData:
    generation: int  # 1 sau 2
    version: int  # la generația 2: 1 sau 2 (cu trecerile frontierei)
    card_number: str = ""
    card_nation: str = ""
    authority: str = ""
    issue_date: date | None = None
    valid_from: date | None = None
    expiry_date: date | None = None
    surname: str = ""
    first_names: str = ""
    birth_date: date | None = None
    licence_number: str = ""
    licence_nation: str = ""
    last_download: datetime | None = None
    days: list = field(default_factory=list)
    vehicles: list = field(default_factory=list)  # {first_use, last_use, plate, nation, odometer_begin, odometer_end}
    places: list = field(default_factory=list)  # {at, kind begin/end, manual, country, odometer}
    borders: list = field(default_factory=list)  # {at, left, entered, odometer}
    loads: list = field(default_factory=list)  # {at, kind load/unload/load_unload, odometer}

    @property
    def first_day(self):
        return self.days[0].day if self.days else None

    @property
    def last_day(self):
        return self.days[-1].day if self.days else None


# --- tipurile de date ---------------------------------------------------------------------------------------------------
def _u16(b, i=0) -> int:
    return struct.unpack_from(">H", b, i)[0]


def _u24(b, i=0) -> int:
    return int.from_bytes(b[i:i + 3], "big")


def _time(b, i=0):
    """TimeReal: secundele de la 01.01.1970 00:00 UTC; 0 / FFFFFFFF — lipsă."""
    v = struct.unpack_from(">I", b, i)[0]
    if v in (0, 0xFFFFFFFF):
        return None
    return datetime.fromtimestamp(v, UTC)


def _tdate(b, i=0):
    t = _time(b, i)
    return t.date() if t else None


def _bcd(b) -> int | None:
    out = 0
    for byte in b:
        hi, lo = byte >> 4, byte & 0x0F
        if hi > 9 or lo > 9:
            return None
        out = out * 100 + hi * 10 + lo
    return out


def _datef(b):
    """Datef: anul (2 octeți BCD), luna, ziua (BCD)."""
    y, m, d = _bcd(b[0:2]), _bcd(b[2:3]), _bcd(b[3:4])
    try:
        return date(y, m, d) if y and m and d else None
    except (TypeError, ValueError):
        return None


def _text(raw: bytes, codepage: int = 1) -> str:
    enc = f"iso8859_{codepage}" if 1 <= codepage <= 16 and codepage != 12 else "latin_1"
    try:
        s = raw.decode(enc)
    except (LookupError, UnicodeDecodeError):
        s = raw.decode("latin_1", "replace")
    return " ".join(s.replace("\x00", " ").replace("\xff", " ").split())


def _name(b) -> str:
    """Name: pagina de cod (ISO 8859-x) + 35 de octeți."""
    return _text(bytes(b[1:]), b[0]) if b else ""


def nation(code: int) -> str:
    """Codul ISO 2 al țării de pe tahograf ('' — necunoscut; EC / EUR / WLD — zone)."""
    if code in NATIONS:
        return NATIONS[code][1]
    return SPECIAL_NATIONS.get(code, "")


# --- etichetele ---------------------------------------------------------------------------------------------------------
def read_tags(data: bytes) -> dict:
    """{(fid, anexa): conținutul} — ultimul câștigă dacă se repetă."""
    if len(data) < 5:
        raise DddError("Fișierul e prea scurt pentru o descărcare de card.")
    out, pos = {}, 0
    while pos + 5 <= len(data):
        fid, app, length = _u16(data, pos), data[pos + 2], _u16(data, pos + 3)
        if app > 3 or fid not in KNOWN_FIDS:
            if not out:
                raise DddError("Fișierul nu e o descărcare a cardului de conducător (alt format — de ex. descărcarea "
                               "vehiculului V_*.ddd).")
            break  # resturi după ultimul EF (completare cu zerouri)
        end = pos + 5 + length
        if end > len(data):
            raise DddError(f"Fișierul e trunchiat (EF {fid:04X}).")
        out[(fid, app)] = data[pos + 5:end]
        pos = end
    if (0x0520, 0) not in out and (0x0520, 2) not in out:
        raise DddError("Fișierul n-are identificarea cardului (EF 0520) — nu e o descărcare de card de conducător.")
    return out


# --- EF-urile ----------------------------------------------------------------------------------------------------------
def _identification(card: CardData, v: bytes):
    if len(v) < 143:
        raise DddError("Identificarea cardului (EF 0520) e incompletă.")
    card.card_nation = nation(v[0])
    card.card_number = _text(bytes(v[1:17])).replace(" ", "")
    card.authority = _name(v[17:53])
    card.issue_date, card.valid_from, card.expiry_date = (_tdate(v, 53), _tdate(v, 57), _tdate(v, 61))
    card.surname = _name(v[65:101])
    card.first_names = _name(v[101:137])
    card.birth_date = _datef(v[137:141])


def _licence(card: CardData, v: bytes):
    if len(v) >= 53:
        card.licence_nation = nation(v[36])
        card.licence_number = _text(bytes(v[37:53])).replace(" ", "")


def _day_record(rec: bytes) -> DayRecord | None:
    when = _time(rec, 4)
    if when is None:
        return None
    changes = {}
    for i in range(12, len(rec) - 1, 2):
        v = _u16(rec, i)
        minute = v & 0x07FF
        if minute > 1439:
            continue
        slot, c, p, act = v >> 15 & 1, v >> 14 & 1, v >> 13 & 1, v >> 11 & 3
        inserted = p == 0
        code = ACTIVITIES[act] if inserted or c == 1 else "U"
        changes[minute] = (code, inserted and c == 1, inserted, (not inserted) and c == 1, slot)
    marks = sorted(changes.items())
    day = DayRecord(day=when.date(), distance=_u16(rec, 10), presence=_bcd(rec[8:10]) or 0)
    for n, (minute, (code, crew, inserted, manual, _slot)) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else 1440
        if end <= minute:
            continue
        last = day.spans[-1] if day.spans else None
        if last and last[2] == code and last[3] == crew and last[4] == inserted and last[5] == manual and last[1] == minute:
            day.spans[-1] = (last[0], end, code, crew, inserted, manual)
        else:
            day.spans.append((minute, end, code, crew, inserted, manual))
    if marks and marks[0][0] > 0:  # înainte de prima schimbare — necunoscut
        day.spans.insert(0, (0, marks[0][0], "U", False, False, False))
    return day


def _activities(v: bytes) -> list:
    """Tamponul circular: de la cea mai nouă înregistrare înapoi, pe lungimea înregistrării de dinainte, până la cea mai veche."""
    if len(v) < 4 + 12:
        return []
    oldest, newest = _u16(v, 0), _u16(v, 2)
    buf = bytes(v[4:])
    n = len(buf)
    if oldest >= n or newest >= n:
        raise DddError("Activitățile (EF 0504): indicatorii tamponului sunt în afara lui.")
    ring = buf + buf

    def take(pos, size):
        return ring[pos:pos + size]

    out, pos, guard = {}, newest, 0
    while guard < 2000:
        guard += 1
        head = take(pos, 12)
        prev_len, rec_len = _u16(head, 0), _u16(head, 2)
        if rec_len < 12 or rec_len > n:
            break
        rec = _day_record(take(pos, rec_len))
        if rec is not None and rec.day not in out:
            out[rec.day] = rec
        if pos == oldest or prev_len == 0:
            break
        pos = (pos - prev_len) % n
    return [out[d] for d in sorted(out)]


def _records(v: bytes, ptr_size: int, sizes: tuple):
    body = v[ptr_size:]
    for size in sizes:
        if body and len(body) % size == 0:
            return size, [body[i:i + size] for i in range(0, len(body), size)]
    return None, []


def _vehicles(v: bytes, gen: int) -> list:
    size, recs = _records(v, 2, (48, 31) if gen == 2 else (31,))
    out = []
    for r in recs:
        first, last = _time(r, 6), _time(r, 10)
        if first is None:
            continue
        out.append({"first_use": first, "last_use": last, "odometer_begin": _u24(r, 0), "odometer_end": _u24(r, 3),
                    "nation": nation(r[14]), "plate": _text(bytes(r[16:29]), r[15])})
    return sorted(out, key=lambda x: x["first_use"])


def _places(v: bytes, gen: int) -> list:
    size, recs = _records(v, 2 if gen == 2 else 1, (21,) if gen == 2 else (10,))
    out = []
    for r in recs:
        at = _time(r, 0)
        if at is None or r[4] not in PLACE_TYPES:
            continue
        out.append({"at": at, "kind": PLACE_TYPES[r[4]], "manual": r[4] in (2, 3), "country": nation(r[5]),
                    "odometer": _u24(r, 7)})
    return sorted(out, key=lambda x: x["at"])


def _borders(v: bytes) -> list:
    size, recs = _records(v, 2, (17,))
    out = []
    for r in recs:
        at = _time(r, 2)
        if at is None:
            continue
        out.append({"at": at, "left": nation(r[0]), "entered": nation(r[1]), "odometer": _u24(r, 14)})
    return sorted(out, key=lambda x: x["at"])


def _loads(v: bytes) -> list:
    size, recs = _records(v, 2, (20,))
    out = []
    for r in recs:
        at = _time(r, 0)
        if at is None or r[4] not in LOAD_TYPES:
            continue
        out.append({"at": at, "kind": LOAD_TYPES[r[4]], "odometer": _u24(r, 17)})
    return sorted(out, key=lambda x: x["at"])


def parse(data: bytes) -> CardData:
    """Descărcarea cardului → CardData. DddError dacă nu e un card de conducător sau e stricat."""
    tags = read_tags(data)
    gen2 = (0x0504, 2) in tags or (0x0520, 2) in tags
    app = 2 if gen2 else 0

    def ef(fid):
        return tags.get((fid, app)) if (fid, app) in tags else tags.get((fid, 0))

    ident = ef(0x0501)
    if ident and ident[0] != 1:
        raise DddError("Cardul nu e un card de conducător (e de atelier, de control sau de întreprindere).")
    card = CardData(generation=2 if gen2 else 1, version=2 if (0x0525, 2) in tags else 1)
    _identification(card, ef(0x0520))
    if ef(0x050E) and len(ef(0x050E)) >= 4:
        card.last_download = _time(ef(0x050E), 0)
    if ef(0x0521):
        _licence(card, ef(0x0521))
    if ef(0x0504):
        card.days = _activities(ef(0x0504))
    if ef(0x0505):
        card.vehicles = _vehicles(ef(0x0505), card.generation)
    if ef(0x0506):
        card.places = _places(ef(0x0506), card.generation)
    if gen2 and (0x0528, 2) in tags:
        card.borders = _borders(tags[(0x0528, 2)])
    if gen2 and (0x0529, 2) in tags:
        card.loads = _loads(tags[(0x0529, 2)])
    return card


def day_start(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def spans_utc(record: DayRecord) -> list:
    """Intervalele zilei ca (început, sfârșit, activitatea, echipaj) cu ora UTC."""
    base = day_start(record.day)
    return [(base + timedelta(minutes=a), base + timedelta(minutes=b), code, crew) for a, b, code, crew, *_ in record.spans]
