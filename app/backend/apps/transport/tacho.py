"""Tahograful: încărcarea descărcărilor cardului de conducător, legarea lor de angajat, zilele cu activitățile (din descărcarea
cea mai nouă), rezumatul pe zile (ora Moldovei), constatările (apps.transport.tacho_rules) și ce vede cursa: timpii, încălcările
din timpul ei și țările din trecerile frontierei (generația 2 versiunea 2)."""
import hashlib
import unicodedata
from collections import defaultdict
from datetime import datetime, time, timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from . import ddd, tacho_rules
from .models import Country, TachoDay, TachoEvent, TachoFile

MAX_SIZE = 4 * 1024 * 1024
DOWNLOAD_DAYS = 28  # cardul se descarcă cel puțin o dată la 28 de zile (Reg. (UE) 581/2010; de verificat pentru RM)
CONTEXT_DAYS = 28  # datele de dinainte / de după perioada cerută, pentru odihnele și compensările care o ating
CODES = ("D", "W", "A", "R", "U")
FIELDS = {"D": "driving", "W": "work", "A": "availability", "R": "rest", "U": "unknown"}


# --- legarea de angajat ------------------------------------------------------------------------------------------------
def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).upper().replace("-", " ").split())


def _card_key(number: str) -> str:
    """Identificarea șoferului din numărul cardului: primele 14 caractere (ultimele două — indicii de înlocuire / reînnoire)."""
    return "".join(ch for ch in (number or "").upper() if ch.isalnum())[:14]


def match_employee(card) -> tuple:
    """(angajatul, „card” / „name”) sau (None, "") — întâi după numărul cardului din dosar, apoi după nume + data nașterii."""
    from apps.staff.models import Employee, EmployeeDocument

    key = _card_key(card.card_number)
    if key:
        docs = EmployeeDocument.objects.filter(doc_type__code="tachograph_card").select_related("employee")
        found = {d.employee for d in docs if _card_key(d.number) == key}
        if len(found) == 1:
            return found.pop(), "card"
    if card.birth_date and card.surname:
        surname, first = _plain(card.surname), _plain(card.first_names).split(" ")[0] if card.first_names else ""
        cands = [e for e in Employee.objects.filter(birth_date=card.birth_date)
                 if _plain(e.last_name) == surname and (not first or _plain(e.first_name).split(" ")[0] == first)]
        if len(cands) == 1:
            return cands[0], "name"
    return None, ""


def _ensure_card_document(employee, f: TachoFile):
    """Cardul legat după nume și nescris în dosar — se adaugă actul (numărul, emitentul, termenul de pe card)."""
    from apps.org.models import DictItem
    from apps.staff.models import EmployeeDocument

    kind = DictItem.objects.filter(kind="document", code="tachograph_card").first()
    if kind is None:
        return None
    docs = EmployeeDocument.objects.filter(employee=employee, doc_type=kind)
    if any("".join(ch for ch in d.number.upper() if ch.isalnum()) == f.card_number.upper() for d in docs):
        return None
    return EmployeeDocument.objects.create(employee=employee, doc_type=kind, number=f.card_number[:40],
                                           issued_by=f.authority[:200], issue_date=f.card_issue, expiry_date=f.card_expiry,
                                           note="Adăugat din descărcarea cardului de tahograf")


# --- încărcarea ---------------------------------------------------------------------------------------------------------
def upload(name: str, data: bytes, user) -> dict:
    """Un fișier → {status: created / duplicate / error, file, message}. Fișierul citit se păstrează; zilele angajatului se refac."""
    if len(data) > MAX_SIZE:
        return {"name": name, "status": "error", "message": "Fișierul e prea mare pentru o descărcare de card (cel mult 4 MB)."}
    digest = hashlib.sha256(data).hexdigest()
    same = TachoFile.objects.filter(sha256=digest).first()
    if same is not None:
        return {"name": name, "status": "duplicate", "file": same.pk, "message": "Fișierul a mai fost încărcat."}
    try:
        card = ddd.parse(data)
    except ddd.DddError as exc:
        return {"name": name, "status": "error", "message": str(exc)}
    except Exception:  # noqa: BLE001 — un fișier stricat nu trebuie să oprească celelalte
        return {"name": name, "status": "error", "message": "Fișierul nu se poate citi (stricat sau alt format)."}
    if not card.card_number:
        return {"name": name, "status": "error", "message": "Cardul n-are număr — nu e o descărcare de card de conducător."}
    employee, how = match_employee(card)
    with transaction.atomic():
        f = TachoFile(name=name[:200], sha256=digest, size=len(data), generation=card.generation, version=card.version,
                      card_number=card.card_number[:20], card_nation=card.card_nation, authority=card.authority[:60],
                      card_issue=card.issue_date, card_expiry=card.expiry_date, holder_surname=card.surname[:60],
                      holder_first_names=card.first_names[:60], birth_date=card.birth_date,
                      licence_number=card.licence_number[:20], downloaded_at=card.last_download, first_day=card.first_day,
                      last_day=card.last_day, days=len(card.days), employee=employee, matched_by=how, uploaded_by=user)
        f.file.save(f"{digest[:20]}.ddd", ContentFile(data), save=False)
        f.save()
        added = _ensure_card_document(employee, f) if how == "name" else None
        if employee is not None:
            rebuild(employee)
    who = employee.full_name() if employee else ""
    msg = (f"{len(card.days)} zile ({card.first_day:%d.%m.%Y}–{card.last_day:%d.%m.%Y})" if card.days else "fără activități")
    if employee is None:
        msg += f"; titularul {f.holder()} (cardul {f.card_number}) nu s-a găsit printre angajați — alegeți angajatul"
    elif added is not None:
        msg += "; cardul a fost adăugat în dosar"
    return {"name": name, "status": "created", "file": f.pk, "employee": employee.pk if employee else None,
            "employee_name": who, "message": msg}


def read(f: TachoFile):
    with f.file.open("rb") as fh:
        return ddd.parse(fh.read())


def rebuild(employee):
    """Zilele și evenimentele angajatului refăcute din toate descărcările lui: ziua se ia din descărcarea cea mai nouă care o
    are; evenimentele se adună (fără dubluri)."""
    TachoDay.objects.filter(employee=employee).delete()
    TachoEvent.objects.filter(employee=employee).delete()
    days, events = {}, {}
    files = sorted(TachoFile.objects.filter(employee=employee),
                   key=lambda x: (x.last_day or datetime.min.date(), x.downloaded_at or x.uploaded_at, x.pk))
    for f in files:
        try:
            card = read(f)
        except (ddd.DddError, OSError, ValueError):
            continue
        for rec in card.days:
            days[rec.day] = (f, rec)
        for p in card.places:
            events[(f"work_{p['kind']}", p["at"])] = TachoEvent(
                employee=employee, file=f, kind=f"work_{p['kind']}", at=p["at"], country=p["country"], odometer=p["odometer"],
                manual=p["manual"])
        for v in card.vehicles:
            events[("vehicle", v["first_use"])] = TachoEvent(
                employee=employee, file=f, kind="vehicle", at=v["first_use"], until=v["last_use"], country=v["nation"],
                plate=v["plate"][:16], odometer=v["odometer_begin"], odometer_end=v["odometer_end"])
        for b in card.borders:
            events[("border", b["at"])] = TachoEvent(employee=employee, file=f, kind="border", at=b["at"], country=b["entered"],
                                                     country_left=b["left"], odometer=b["odometer"])
        for ld in card.loads:
            events[(ld["kind"], ld["at"])] = TachoEvent(employee=employee, file=f, kind=ld["kind"], at=ld["at"],
                                                        odometer=ld["odometer"])
    rows = []
    for day, (f, rec) in sorted(days.items()):
        totals = dict.fromkeys(CODES, 0)
        for a, b, code, *_ in rec.spans:
            totals[code] += b - a
        rows.append(TachoDay(employee=employee, file=f, day=day, distance=rec.distance, presence=rec.presence,
                             spans=[[a, b, code, int(crew), int(manual)] for a, b, code, crew, _ins, manual in rec.spans],
                             **{FIELDS[c]: v for c, v in totals.items()}))
    TachoDay.objects.bulk_create(rows)
    TachoEvent.objects.bulk_create(list(events.values()))


def delete_file(f: TachoFile):
    employee = f.employee
    with transaction.atomic():
        f.file.delete(save=False)
        f.delete()
        if employee is not None:
            rebuild(employee)


def assign(f: TachoFile, employee):
    old = f.employee
    with transaction.atomic():
        f.employee, f.matched_by = employee, "manual" if employee else ""
        f.save(update_fields=["employee", "matched_by"])
        for e in {old, employee} - {None}:
            rebuild(e)


# --- timpul -------------------------------------------------------------------------------------------------------------
def _utc(day):
    return ddd.day_start(day)


def spans(employee, start: datetime, end: datetime) -> tuple:
    """(intervalele UTC (început, sfârșit, cod, echipaj), începutul datelor, sfârșitul datelor) pe [start, end); sfârșitul
    datelor e tăiat la ora ultimei descărcări, dacă ea cade în ultima zi (după ea cardul încă nu știe nimic)."""
    first = (start.astimezone(ddd.UTC) - timedelta(days=1)).date()
    last = (end.astimezone(ddd.UTC) + timedelta(days=1)).date()
    days = list(TachoDay.objects.filter(employee=employee, day__gte=first, day__lte=last).order_by("day"))
    if not days:
        return [], None, None
    out = []
    for d in days:
        base = _utc(d.day)
        out += [(base + timedelta(minutes=a), base + timedelta(minutes=b), code, bool(crew)) for a, b, code, crew, *_ in d.spans]
    data_start = max(_utc(days[0].day), start)
    data_end = _utc(days[-1].day) + timedelta(days=1)
    latest = (TachoFile.objects.filter(employee=employee, last_day=days[-1].day, downloaded_at__isnull=False)
              .order_by("-downloaded_at").values_list("downloaded_at", flat=True).first())
    if latest is not None and _utc(days[-1].day) <= latest < data_end:
        data_end = latest
    return out, data_start, min(data_end, end)


def _clip(rows, data_end):
    """Intervalele tăiate la sfârșitul datelor (ora ultimei descărcări): după ea cardul încă nu știe nimic."""
    if data_end is None:
        return rows
    return [(s, min(e, data_end), code, crew) for s, e, code, crew in rows if s < data_end]


def findings(employee, start: datetime, end: datetime) -> list:
    """Constatările care încep în [start, end) (datele cu CONTEXT_DAYS zile înainte și după)."""
    pad = timedelta(days=CONTEXT_DAYS)
    rows, a, b = spans(employee, start - pad, end + pad)
    if not rows:
        return []
    return [f for f in tacho_rules.analyze(rows, a, b) if start <= f.start < end]


def _local_bounds(day):
    a = timezone.make_aware(datetime.combine(day, time.min))
    return a, a + timedelta(days=1)


def day_rows(employee, first, last) -> list:
    """Rezumatul pe zilele locale (ora Moldovei): minutele pe activități, intervalele zilei, km, țările, vehiculele, constatările."""
    lo, _ = _local_bounds(first)
    _, hi = _local_bounds(last)
    rows, data_start, data_end = spans(employee, lo, hi)
    rows = _clip(rows, data_end)
    found = findings(employee, lo, hi) if rows else []
    km = {d.day: d.distance for d in TachoDay.objects.filter(employee=employee, day__gte=first - timedelta(days=1),
                                                             day__lte=last + timedelta(days=1))}
    events = list(TachoEvent.objects.filter(employee=employee, at__lt=hi).exclude(kind="vehicle", until__lt=lo)
                  .exclude(at__lt=lo, kind__in=("work_begin", "work_end", "border", "load", "unload", "load_unload")))
    out = []
    d = first
    while d <= last:
        a, b = _local_bounds(d)
        totals = dict.fromkeys(CODES, 0)
        parts = []
        for s, e, code, crew in rows:
            s2, e2 = max(s, a), min(e, b)
            if e2 <= s2:
                continue
            m0, m1 = int((s2 - a).total_seconds() // 60), int((e2 - a).total_seconds() // 60)
            totals[code] += m1 - m0
            parts.append([m0, m1, code, int(crew)])
        countries = []
        for ev in events:
            if a <= ev.at < b and ev.kind in ("work_begin", "work_end", "border") and ev.country and ev.country not in countries:
                countries.append(ev.country)
        plates = sorted({ev.plate for ev in events if ev.kind == "vehicle" and ev.at < b and (ev.until or ev.at) >= a and ev.plate})
        out.append({"day": d, "has_data": bool(parts), "spans": parts, **{FIELDS[c]: v for c, v in totals.items()},
                    "km": km.get(d, 0), "countries": countries, "vehicles": plates,
                    "findings": [f.as_dict() for f in found if a <= f.start < b]})
        d += timedelta(days=1)
    return out


# --- cursa ---------------------------------------------------------------------------------------------------------------
def trip_info(trip) -> dict:
    """Pentru fiecare șofer al cursei: are date de pe card pe toată cursa, timpii (min) și constatările din timpul ei."""
    people = []
    for job in (trip.driver, trip.co_driver):
        if job is None:
            continue
        emp = job.employee
        rows, a, b = spans(emp, trip.departure, trip.arrival)
        rows = _clip(rows, b)
        totals = dict.fromkeys(CODES, 0)
        for s, e, code, _crew in rows:
            s2, e2 = max(s, trip.departure), min(e, trip.arrival)
            if e2 > s2:
                totals[code] += int((e2 - s2).total_seconds() // 60)
        covered = bool(rows) and a <= trip.departure and b >= trip.arrival
        people.append({"employee": emp.pk, "name": emp.full_name(), "has_data": bool(rows), "covered": covered,
                       "totals": {FIELDS[c]: v for c, v in totals.items()},
                       "findings": [f.as_dict() for f in findings(emp, trip.departure, trip.arrival)] if rows else [],
                       "borders": TachoEvent.objects.filter(employee=emp, kind="border", at__gte=trip.departure,
                                                            at__lte=trip.arrival).count()})
    return {"people": people, "any_files": TachoFile.objects.exists()}


def legs_from_borders(trip) -> list:
    """Țările cursei din trecerile frontierei înregistrate pe cardul șoferului (generația 2 versiunea 2) și încărcările /
    descărcările din ele — propunerea de segmente (nu se salvează)."""
    emp = trip.driver.employee
    events = list(TachoEvent.objects.filter(employee=emp, at__gte=trip.departure, at__lte=trip.arrival,
                                            kind__in=("border", "load", "unload", "load_unload")).order_by("at"))
    borders = [e for e in events if e.kind == "border"]
    if not borders:
        raise ValidationError({"detail": "Pe cardul șoferului nu sunt treceri ale frontierei în timpul cursei (le înregistrează doar "
                                         "tahograful de generația 2 versiunea 2 — „smart 2”, din 2023–2025)."})
    countries = {c.code: c for c in Country.objects.all()}
    legs, cur = [], None
    for e in borders:
        if cur is not None:
            cur["left"] = e.at
            legs.append(cur)
            cur = None
        if e.country and e.country != "MD" and e.country in countries:
            cur = {"country": countries[e.country].pk, "country_code": e.country, "country_name": countries[e.country].name_ro,
                   "entered": e.at, "left": None, "loading": False, "unloading": False, "meals": False, "km": None, "note": ""}
    if cur is not None:
        cur["left"] = trip.arrival
        legs.append(cur)
    for e in events:
        if e.kind == "border":
            continue
        for leg in legs:
            if leg["entered"] <= e.at < leg["left"]:
                leg["loading"] = leg["loading"] or e.kind in ("load", "load_unload")
                leg["unloading"] = leg["unloading"] or e.kind in ("unload", "load_unload")
    return legs


def trip_warnings(trip) -> list:
    """Avertismentele cursei din tahograf (nu opresc aprobarea): lipsa datelor de pe card, încălcările din timpul cursei."""
    if not (trip.vehicle_id and trip.vehicle.tachograph) or not TachoFile.objects.exists():
        return []
    out = []
    info = trip_info(trip)
    for p in info["people"]:
        if not p["has_data"]:
            out.append(f"{p['name']}: nu sunt descărcări ale cardului de tahograf pentru cursă")
        elif not p["covered"]:
            out.append(f"{p['name']}: descărcările cardului nu acoperă toată cursa")
        errors = [f for f in p["findings"] if f["level"] == "error"]
        if errors:
            out.append(f"{p['name']}: {len(errors)} încălcări ale timpului de conducere / odihnă în timpul cursei (Tahograful)")
    return out


# --- alertele ------------------------------------------------------------------------------------------------------------
def _module_on() -> bool:
    from apps.core.models import Company

    c = Company.objects.first()
    return bool(c and c.transport_enabled)


def download_alerts(today, days, cfg):
    """Cardul de conducător de descărcat: ultimul fișier mai vechi de DOWNLOAD_DAYS zile (cei cu cardul în dosar, activi)."""
    from apps.alerts.engine import Alert, _d, _subs
    from apps.staff.models import EmployeeDocument

    if not _module_on():
        return []
    out = []
    holders = {d.employee for d in EmployeeDocument.objects.filter(
        doc_type__code="tachograph_card", employee__status="active").select_related("employee")
        .prefetch_related("employee__employments") if not d.expiry_date or d.expiry_date >= today}
    last = defaultdict(lambda: None)
    for f in TachoFile.objects.filter(employee__in=holders):
        when = timezone.localtime(f.downloaded_at).date() if f.downloaded_at else timezone.localtime(f.uploaded_at).date()
        last[f.employee_id] = max(filter(None, (last[f.employee_id], when)))
    for e in holders:
        prev = last[e.pk]
        due = (prev + timedelta(days=DOWNLOAD_DAYS)) if prev else today
        if due > today + timedelta(days=days):
            continue
        text = (f"{e.full_name()} — ultima descărcare a cardului {_d(prev)}, de descărcat până la {_d(due)}" if prev
                else f"{e.full_name()} — cardul de tahograf n-a fost descărcat încă în program")
        out.append(Alert("tacho_download", f"tachodl:{e.pk}:{due}", "Descărcarea cardului de tahograf", text, due,
                         "warning" if due <= today else "task", e.pk, e.full_name(), _subs(e), "/transport/tachograph"))
    return out


def infringement_alerts(today, days, cfg):
    """Încălcările din ultimele `days` zile (implicit 14), câte o alertă pe șofer și zi."""
    from apps.alerts.engine import Alert, _d, _subs
    from apps.staff.models import Employee

    if not _module_on():
        return []
    out = []
    lo, _ = _local_bounds(today - timedelta(days=max(days, 1)))
    _, hi = _local_bounds(today)
    people = Employee.objects.filter(tacho_days__day__gte=(lo - timedelta(days=1)).date()).distinct().prefetch_related("employments")
    for e in people:
        per_day = defaultdict(list)
        for f in findings(e, lo, hi):
            if f.level == "error":
                per_day[timezone.localtime(f.start).date()].append(f)
        for day, items in sorted(per_day.items()):
            out.append(Alert("tacho_infringement", f"tachoinf:{e.pk}:{day}", "Încălcări ale timpului de conducere / odihnă",
                             f"{e.full_name()} — {_d(day)}: " + "; ".join(tacho_rules.TITLES[i.code].split(" — ")[0] for i in items),
                             day, "warning", e.pk, e.full_name(), _subs(e), f"/transport/tachograph?employee={e.pk}&tab=days&month={day:%Y-%m}"))
    return out
