"""Limitele timpului de conducere și de odihnă ale șoferului (Codul transporturilor rutiere nr. 150/2014; Acordul AETR art. 6–8,
la fel ca Reg. (CE) nr. 561/2006 art. 6–8), verificate pe activitățile de pe cardul tahografului.

Intrarea: intervalele (început, sfârșit, activitatea, echipaj) în ora UTC — D conducere, W altă muncă, A disponibilitate, R pauză /
odihnă, U necunoscut (cardul nu era în tahograf). Timpul fără card și zilele fără înregistrare se socotesc **odihnă** (ca
programele de analiză obișnuite) — conducerea fără card nu se vede de pe card. Săptămâna: luni 00:00 – duminică 24:00 UTC.

Regulile:
- conducerea continuă: după 4 h 30 min — pauza de 45 min (sau 15 min, apoi 30 min), art. 7;
- conducerea zilnică (între două odihne zilnice / săptămânale): 9 h, de cel mult două ori pe săptămână 10 h, art. 6 alin. (1);
- conducerea săptămânală: 56 h; în două săptămâni la rând: 90 h, art. 6 alin. (2), (3);
- odihna zilnică: în 24 de ore de la sfârșitul odihnei de dinainte — 11 h (sau 3 h + 9 h), redusă 9 h de cel mult 3 ori între
  două odihne săptămânale; în echipaj — 9 h în 30 de ore, art. 8 alin. (2), (4), (5);
- odihna săptămânală: cel târziu după 6 perioade de 24 h de la cea de dinainte; normală 45 h, redusă 24 h; în două săptămâni la
  rând cel puțin una normală; reducerea se compensează în bloc până la sfârșitul săptămânii a treia, lipită de o odihnă de cel
  puțin 9 h, art. 8 alin. (6), (7).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

H = 60
CONTINUOUS = 270
BREAK_FULL, BREAK_FIRST, BREAK_SECOND = 45, 15, 30
DAILY, DAILY_EXT, EXT_PER_WEEK = 9 * H, 10 * H, 2
WEEKLY, BIWEEKLY = 56 * H, 90 * H
DAILY_REST, DAILY_REST_REDUCED, SPLIT_FIRST, REDUCED_MAX = 11 * H, 9 * H, 3 * H, 3
WINDOW, CREW_WINDOW = 24 * H, 30 * H
WEEKLY_REST, WEEKLY_REST_REDUCED, WEEKLY_GAP = 45 * H, 24 * H, 144 * H

TITLES = {
    "continuous": "Conducere continuă peste 4 h 30 min fără pauza de 45 min (sau 15 + 30 min) — art. 7",
    "daily_driving": "Conducerea zilnică peste 10 h — art. 6 alin. (1)",
    "daily_extension": "A treia conducere zilnică peste 9 h în aceeași săptămână — art. 6 alin. (1)",
    "weekly_driving": "Conducerea săptămânală peste 56 h — art. 6 alin. (2)",
    "biweekly_driving": "Conducerea în două săptămâni la rând peste 90 h — art. 6 alin. (3)",
    "daily_rest": "Odihna zilnică insuficientă — art. 8 alin. (2)",
    "daily_rest_reduced": "Mai mult de 3 odihne zilnice reduse între două odihne săptămânale — art. 8 alin. (4)",
    "weekly_rest_late": "Odihna săptămânală după mai mult de 6 perioade de 24 h — art. 8 alin. (6)",
    "weekly_reduced_twice": "Două odihne săptămânale reduse la rând — art. 8 alin. (6)",
    "weekly_compensation": "Odihna săptămânală redusă necompensată la termen — art. 8 alin. (6), (7)",
    "compensation_due": "De compensat odihna săptămânală redusă — art. 8 alin. (6), (7)",
}


@dataclass
class Seg:
    start: datetime
    end: datetime
    act: str  # D / W / A / R
    crew: bool = False

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


@dataclass
class Finding:
    code: str
    start: datetime
    end: datetime
    value: int  # minute (ce s-a găsit)
    limit: int  # minute (limita)
    text: str
    level: str = "error"  # error — încălcare; info — de urmărit

    def as_dict(self) -> dict:
        return {"code": self.code, "title": TITLES[self.code], "start": self.start, "end": self.end, "value": self.value,
                "limit": self.limit, "text": self.text, "level": self.level}


def hm(minutes: int) -> str:
    minutes = int(round(minutes))
    h, m = divmod(abs(minutes), 60)
    return f"{h} h {m:02d} min" if m else f"{h} h"


def week_start(dt: datetime) -> datetime:
    d = dt - timedelta(days=dt.weekday())
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


def normalize(spans: list, data_start: datetime, data_end: datetime) -> list:
    """Intervalele → segmente lipite pe [data_start, data_end): golurile și U devin R, cele de același fel se unesc."""
    out = []

    def add(a, b, act, crew=False):
        a, b = max(a, data_start), min(b, data_end)
        if b <= a:
            return
        if out and out[-1].act == act and out[-1].end >= a:
            out[-1].end = max(out[-1].end, b)
            out[-1].crew = out[-1].crew or crew
        else:
            out.append(Seg(a, b, act, crew))

    cursor = data_start
    for a, b, code, crew in sorted(spans, key=lambda x: x[0]):
        a = max(a, cursor)
        if b <= a:
            continue
        if a > cursor:
            add(cursor, a, "R")
        add(a, b, "R" if code == "U" else code, bool(crew))
        cursor = b
    if cursor < data_end:
        add(cursor, data_end, "R")
    return out


def _driving_between(segs, a, b) -> int:
    total = 0
    for s in segs:
        if s.act == "D" and s.end > a and s.start < b:
            total += int((min(s.end, b) - max(s.start, a)).total_seconds() // 60)
    return total


def _continuous(segs) -> list:
    out, acc, first_part, since = [], 0, False, None
    for s in segs:
        if s.act == "D":
            if acc == 0:
                since = s.start
            acc += s.minutes
        elif s.act == "R":
            m = s.minutes
            if m >= BREAK_FULL or (first_part and m >= BREAK_SECOND):
                if acc > CONTINUOUS:
                    out.append(Finding("continuous", since, s.start, acc, CONTINUOUS,
                                       f"{hm(acc)} de conducere fără pauza cerută (limita {hm(CONTINUOUS)})"))
                acc, first_part = 0, False
            elif m >= BREAK_FIRST:
                first_part = True
    if acc > CONTINUOUS and segs:
        out.append(Finding("continuous", since, segs[-1].end, acc, CONTINUOUS,
                           f"{hm(acc)} de conducere fără pauza cerută (limita {hm(CONTINUOUS)})"))
    return out


def _daily_driving(segs, data_start, data_end) -> list:
    out = []
    rests = [s for s in segs if s.act == "R" and s.minutes >= DAILY_REST_REDUCED]
    bounds = [(data_start, rests[0].start if rests else data_end, False)]
    bounds += [(r.end, rests[i + 1].start, True) for i, r in enumerate(rests[:-1])]
    if rests:
        bounds.append((rests[-1].end, data_end, False))
    ext = {}
    for a, b, complete in bounds:
        drive = _driving_between(segs, a, b)
        if drive <= DAILY:
            continue
        week = week_start(a)
        if complete:
            ext[week] = ext.get(week, 0) + 1
        if drive > DAILY_EXT:
            out.append(Finding("daily_driving", a, b, drive, DAILY_EXT,
                               f"{hm(drive)} de conducere între două odihne (limita {hm(DAILY_EXT)})"))
        elif complete and ext[week] > EXT_PER_WEEK:
            out.append(Finding("daily_extension", a, b, drive, DAILY,
                               f"{hm(drive)} de conducere — a {ext[week]}-a zi peste 9 h în săptămână (cel mult 2)"))
    return out


def _weekly_driving(segs, data_start, data_end) -> list:
    out = []
    weeks = {}
    w = week_start(data_start)
    while w < data_end:
        weeks[w] = _driving_between(segs, w, w + timedelta(days=7))
        w += timedelta(days=7)
    for w, total in weeks.items():
        if total > WEEKLY:
            out.append(Finding("weekly_driving", w, w + timedelta(days=7), total, WEEKLY,
                               f"{hm(total)} de conducere în săptămâna {w:%d.%m}–{w + timedelta(days=6):%d.%m.%Y} (limita 56 h)"))
        nxt = w + timedelta(days=7)
        if nxt in weeks and total + weeks[nxt] > BIWEEKLY:
            both = total + weeks[nxt]
            out.append(Finding("biweekly_driving", w, nxt + timedelta(days=7), both, BIWEEKLY,
                               f"{hm(both)} de conducere în săptămânile {w:%d.%m}–{nxt + timedelta(days=6):%d.%m.%Y} (limita 90 h)"))
    return out


def _daily_rest(segs, data_end) -> list:
    out = []
    rests = [s for s in segs if s.act == "R"]
    first = next((r for r in rests if r.minutes >= DAILY_REST_REDUCED), None)
    if first is None:
        return out
    t0, reduced = first.end, 0
    guard = 0
    while guard < 5000:
        guard += 1
        crew = any(s.crew for s in segs if s.act == "D" and s.start < t0 + timedelta(minutes=CREW_WINDOW) and s.end > t0)
        window = CREW_WINDOW if crew else WINDOW
        w_end = t0 + timedelta(minutes=window)
        if w_end > data_end:
            break
        cands = [r for r in rests if t0 <= r.start < w_end]
        q = next((r for r in cands if r.minutes >= DAILY_REST_REDUCED), None)
        if q is None:
            longest = max((int((min(r.end, w_end) - r.start).total_seconds() // 60) for r in cands), default=0)
            out.append(Finding("daily_rest", t0, w_end, longest, DAILY_REST_REDUCED if crew else DAILY_REST,
                               f"în {window // 60} de ore de la odihna de dinainte cea mai lungă odihnă e {hm(longest)} "
                               f"(cerut {hm(DAILY_REST_REDUCED if crew else DAILY_REST)}, redusă {hm(DAILY_REST_REDUCED)})"))
            q = next((r for r in rests if r.start >= w_end and r.minutes >= DAILY_REST_REDUCED), None)
            if q is None:
                break
        else:
            inside = int((min(q.end, w_end) - q.start).total_seconds() // 60)
            split = any(r.start < q.start and r.minutes >= SPLIT_FIRST for r in cands)
            if inside >= DAILY_REST or (crew and inside >= DAILY_REST_REDUCED) or (split and inside >= DAILY_REST_REDUCED):
                pass  # odihna normală (sau împărțită 3 + 9, sau în echipaj)
            elif inside >= DAILY_REST_REDUCED:
                reduced += 1
                if reduced > REDUCED_MAX:
                    out.append(Finding("daily_rest_reduced", q.start, q.end, inside, DAILY_REST,
                                       f"a {reduced}-a odihnă zilnică redusă ({hm(inside)}) de la odihna săptămânală (cel mult 3)"))
            else:
                out.append(Finding("daily_rest", t0, w_end, inside, DAILY_REST_REDUCED,
                                   f"odihna începută la {q.start:%d.%m %H:%M} UTC are în cele {window // 60} de ore doar {hm(inside)} "
                                   f"(cel puțin {hm(DAILY_REST_REDUCED)})"))
        if q.minutes >= WEEKLY_REST_REDUCED:
            reduced = 0
        t0 = q.end
    return out


def _weekly_rest(segs, data_start, data_end) -> list:
    out = []
    weekly = [s for s in segs if s.act == "R" and s.minutes >= WEEKLY_REST_REDUCED]
    # de la începutul datelor: odihna de dinainte s-a terminat cel târziu atunci
    first = weekly[0].start if weekly else data_end
    if first - data_start > timedelta(minutes=WEEKLY_GAP):
        gap = int((first - data_start).total_seconds() // 60)
        out.append(Finding("weekly_rest_late", data_start + timedelta(minutes=WEEKLY_GAP), first, gap, WEEKLY_GAP,
                           f"cel puțin {hm(gap)} fără odihnă săptămânală (cel mult 6 × 24 h)"))
    for i, r in enumerate(weekly[1:], start=1):
        prev = weekly[i - 1]
        gap = int((r.start - prev.end).total_seconds() // 60)
        if gap > WEEKLY_GAP:
            out.append(Finding("weekly_rest_late", prev.end + timedelta(minutes=WEEKLY_GAP), r.start, gap, WEEKLY_GAP,
                               f"odihna săptămânală a început după {hm(gap)} de la cea de dinainte (cel mult 6 × 24 h)"))
        if prev.minutes < WEEKLY_REST and r.minutes < WEEKLY_REST:
            out.append(Finding("weekly_reduced_twice", r.start, r.end, r.minutes, WEEKLY_REST,
                               f"odihnele săptămânale de {hm(prev.minutes)} și {hm(r.minutes)} sunt amândouă reduse"))
    if weekly:
        last = weekly[-1]
        due = last.end + timedelta(minutes=WEEKLY_GAP)
        if due < data_end:
            out.append(Finding("weekly_rest_late", due, data_end, int((data_end - last.end).total_seconds() // 60), WEEKLY_GAP,
                               "după 6 perioade de 24 h de la ultima odihnă săptămânală nu urmează alta"))
    # compensarea reducerii
    used = set()
    rests = [s for s in segs if s.act == "R" and s.minutes >= DAILY_REST_REDUCED]
    for r in weekly:
        if r.minutes >= WEEKLY_REST:
            continue
        deficit = WEEKLY_REST - r.minutes
        deadline = week_start(r.start) + timedelta(days=28)  # sfârșitul săptămânii a treia de după
        found = None
        for x in rests:
            if x.start <= r.end or x.start >= deadline or id(x) in used:
                continue
            base = WEEKLY_REST if x.minutes >= WEEKLY_REST_REDUCED else DAILY_REST_REDUCED
            if x.minutes - base >= deficit:
                found = x
                break
        if found is not None:
            used.add(id(found))
        elif deadline <= data_end:
            out.append(Finding("weekly_compensation", r.start, deadline, r.minutes, WEEKLY_REST,
                               f"odihna săptămânală redusă la {hm(r.minutes)}: {hm(deficit)} de compensat până la "
                               f"{deadline - timedelta(minutes=1):%d.%m.%Y} — compensarea nu se găsește"))
        else:
            out.append(Finding("compensation_due", r.start, deadline, r.minutes, WEEKLY_REST,
                               f"odihna săptămânală redusă la {hm(r.minutes)}: de compensat {hm(deficit)} până la "
                               f"{deadline - timedelta(minutes=1):%d.%m.%Y}, lipit de o odihnă de cel puțin 9 h", level="info"))
    return out


def analyze(spans: list, data_start: datetime, data_end: datetime) -> list:
    """Toate constatările pe datele [data_start, data_end), ordonate după început."""
    if data_end <= data_start:
        return []
    segs = normalize(spans, data_start, data_end)
    found = (_continuous(segs) + _daily_driving(segs, data_start, data_end) + _weekly_driving(segs, data_start, data_end)
             + _daily_rest(segs, data_end) + _weekly_rest(segs, data_start, data_end))
    return sorted(found, key=lambda f: (f.start, f.code))
