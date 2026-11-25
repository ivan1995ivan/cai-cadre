"""GPS-ul vehiculelor (S6b pasul c): zilele din sistemul de monitorizare.

Sursa comună e raportul zilnic pe vehicul (km, timpul în mișcare, cu motorul pornit, prima pornire / ultima oprire,
combustibilul, kilometrajul, țările), adus din fișierul exportat de orice sistem GPS (Excel sau CSV, antetul recunoscut după
text — și cel din Wialon, GPS-trace, Navixy și alții, în română, rusă sau engleză) sau, când se va lega, din API-ul
furnizorului (scrie aceleași rânduri `GpsDay`, cu `source` = numele furnizorului). Vehiculul se găsește după identificatorul
din GPS (Setări → Vehiculele, „ID în GPS”) sau după numărul de înmatriculare. O zi importată din nou se actualizează: km și
coloanele din fișier se înlocuiesc, celelalte rămân.

Folosirea: în foaia de parcurs — km din GPS pe zilele cursei față de km ai foii (avertisment peste C.gps_km_tolerance_pct %),
butonul „Km din GPS”; consumul cursei din GPS, când foaia nu are nici rezervorul, nici consumul scris (KPI „consumul față de
normă”). Zilele sunt întregi: în ziua plecării / întoarcerii GPS-ul are și km din afara cursei, dacă vehiculul a mai mers.
"""
import re
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.core.excel_import import Column, RowError, Spec

from .models import GpsDay, Vehicle

ZERO = Decimal("0")


def gps_spec() -> Spec:
    return Spec(
        code="gps_days", title="GPS-ul vehiculelor: zilele (raportul zilnic din sistemul de monitorizare)",
        columns=[
            Column("vehicle", "Vehiculul (ID în GPS sau nr. de înmatriculare)", required=True, example="ABC 123",
                   aliases=("vehicul", "obiect", "obiectul", "unitate", "unit", "object", "vehicle", "device", "tracker", "объект",
                            "транспортное средство", "тс", "госномер", "гос номер", "номер", "plate")),
            Column("day", "Data", kind="date", required=True, example="02.03.2026",
                   aliases=("ziua", "date", "day", "дата", "день", "начало периода", "period start")),
            Column("km", "Km", kind="decimal", required=True, example=640.5,
                   aliases=("kilometri", "distanta", "parcurs", "mileage", "distance", "пробег", "пробег км", "пробег, км",
                            "пробег в поездках", "mileage km", "distance km")),
            Column("moving", "În mișcare (hh:mm sau ore)", example="8:15",
                   aliases=("timp in miscare", "moving time", "driving time", "время в движении", "в движении", "время движения")),
            Column("engine", "Motorul pornit (hh:mm sau ore)", example="9:40",
                   aliases=("ore motor", "engine hours", "motor hours", "моточасы", "время работы двигателя", "работа двигателя")),
            Column("first_start", "Prima pornire (hh:mm)", example="06:05",
                   aliases=("pornire", "start", "first start", "начало движения", "первое движение", "начало")),
            Column("last_stop", "Ultima oprire (hh:mm)", example="19:40",
                   aliases=("oprire", "stop", "last stop", "конец движения", "последняя остановка", "конец")),
            Column("fuel", "Combustibil consumat (l)", kind="decimal", example="",
                   aliases=("combustibil", "consum", "fuel", "fuel consumed", "fuel used", "расход топлива", "потрачено топлива",
                            "потрачено по дут", "расход, л", "топливо")),
            Column("odometer_start", "Kilometrajul la început", kind="int", example="",
                   aliases=("odometru inceput", "odometer start", "начальный пробег", "одометр начало", "пробег на начало")),
            Column("odometer_end", "Kilometrajul la sfârșit", kind="int", example="",
                   aliases=("odometru sfarsit", "odometer end", "конечный пробег", "одометр конец", "пробег на конец")),
            Column("countries", "Țările (coduri ISO 2, prin virgulă)", example="MD, RO",
                   aliases=("tari", "tarile", "countries", "страны")),
        ],
        save_row=save_row,
        notes=["Un rând = un vehicul într-o zi. Vehiculul se recunoaște după „ID în GPS” din Setări → Vehiculele sau după numărul de "
               "înmatriculare. Ziua importată din nou se actualizează: km și coloanele din fișier se înlocuiesc, celelalte rămân.",
               "Fișierul exportat din sistemul GPS poate fi încărcat direct (Excel sau CSV), dacă antetul are coloanele de mai sus "
               "(se recunosc și denumirile obișnuite în rusă și engleză: „Пробег”, „Mileage”, „Время в движении”, „Моточасы”…).",
               "Timpul se scrie „hh:mm” sau ore cu zecimale (8,25)."],
    )


def find_vehicle(text: str):
    text = str(text or "").strip()
    if not text:
        return None
    v = Vehicle.objects.filter(gps_id=text).first()
    if v is None:
        plate = " ".join(text.upper().split())
        v = Vehicle.objects.filter(plate=plate).first() or Vehicle.objects.filter(plate=plate.replace(" ", "")).first()
        if v is None:  # „ABC123” față de „ABC 123”
            compact = plate.replace(" ", "")
            v = next((x for x in Vehicle.objects.all() if x.plate.replace(" ", "") == compact), None)
    return v


def _minutes(value, title):
    """„8:15”, „8:15:30”, „1 day 02:10” / „1 д 02:10”, 8.25 (ore) → minute."""
    if value in (None, ""):
        return None
    if isinstance(value, timedelta):
        return int(value.total_seconds() // 60)
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    if isinstance(value, (int, float, Decimal)):  # ore cu zecimale (celula Excel cu ora vine ca time / timedelta)
        return int(Decimal(str(value)) * 60)
    text = str(value).strip().lower()
    days = 0
    m = re.match(r"^(\d+)\s*(?:days?|zile|zi|д\.?|дн\.?|дня|дней)\s*,?\s*(.*)$", text)
    if m:
        days, text = int(m.group(1)), m.group(2) or "0:00"
    m = re.match(r"^(\d+):(\d{1,2})(?::(\d{1,2}))?$", text)
    if m:
        return days * 1440 + int(m.group(1)) * 60 + int(m.group(2))
    try:
        return days * 1440 + int(Decimal(text.replace(",", ".")) * 60)
    except Exception:  # noqa: BLE001
        raise RowError(f"„{title}”: „{value}” nu e o durată (hh:mm sau ore).") from None


def _clock(value, title):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if isinstance(value, (int, float, Decimal)) and 0 <= float(value) < 1:  # fracția zilei din Excel
        mins = int(round(float(value) * 1440))
        return time(mins // 60 % 24, mins % 60)
    text = str(value).strip()
    m = re.search(r"(\d{1,2}):(\d{2})(?::\d{2})?\s*$", text)
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise RowError(f"„{title}”: „{value}” nu e o oră (hh:mm).")
    return time(int(m.group(1)), int(m.group(2)))


def _countries(text) -> str:
    codes = [c.upper() for c in re.split(r"[\s,;/–-]+", str(text or "")) if c.strip()]
    bad = [c for c in codes if len(c) != 2 or not c.isalpha()]
    if bad:
        raise RowError(f"„Țările”: „{', '.join(bad)}” nu sunt coduri ISO din două litere (RO, HU, DE…).")
    return ",".join(dict.fromkeys(codes))[:60]


def save_row(values, context):
    v = find_vehicle(values.get("vehicle"))
    if v is None:
        raise RowError(f"Vehiculul „{values.get('vehicle')}” nu există: scrieți-i „ID în GPS” sau numărul în Setări → Vehiculele.")
    km = values.get("km")
    if km is None or km < 0:
        raise RowError("Km lipsesc sau sunt negativi.")
    fuel = values.get("fuel")
    if fuel is not None and fuel < 0:
        raise RowError("Combustibilul nu poate fi negativ.")
    o1, o2 = values.get("odometer_start"), values.get("odometer_end")
    if o1 is not None and o2 is not None and o2 < o1:
        raise RowError("Kilometrajul la sfârșit e mai mic decât la început.")
    for col in ("odometer_start", "odometer_end"):
        if values.get(col) is not None and values[col] < 0:
            raise RowError("Kilometrajul nu poate fi negativ.")
    # doar coloanele care sunt în fișier: un al doilea export (de ex. doar combustibilul) completează ziua, nu o golește
    read = {"moving": ("moving_min", lambda x: _minutes(x, "În mișcare")),
            "engine": ("engine_min", lambda x: _minutes(x, "Motorul pornit")),
            "first_start": ("first_start", lambda x: _clock(x, "Prima pornire")),
            "last_stop": ("last_stop", lambda x: _clock(x, "Ultima oprire")), "fuel": ("fuel_l", lambda x: x),
            "odometer_start": ("odometer_start", lambda x: x), "odometer_end": ("odometer_end", lambda x: x),
            "countries": ("countries", _countries)}
    fields = {"km": km.quantize(Decimal("0.1")), "source": context.get("source", "fișier"), "imported_by": context.get("user"),
              "imported_at": timezone.now()}
    for key, (name, convert) in read.items():
        if key in values:
            fields[name] = convert(values[key])
    for key in ("moving_min", "engine_min"):
        if fields.get(key) is not None and not (0 <= fields[key] <= 1440):
            raise RowError("Timpul dintr-o zi e între 0 și 24 de ore.")
    seen = context.setdefault("seen", set())
    if (v.pk, values["day"]) in seen:
        raise RowError(f"Vehiculul {v.plate} pe {values['day']:%d.%m.%Y} apare de două ori în fișier.")
    seen.add((v.pk, values["day"]))
    obj, created = GpsDay.objects.update_or_create(vehicle=v, day=values["day"], defaults=fields)
    return _Label(obj), "created" if created else "updated"


class _Label:
    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        return f"{self.obj.vehicle.plate} — {self.obj.day:%d.%m.%Y}: {fmt(self.obj.km)} km"


def fmt(value) -> str:
    from .services import fmt as f

    return f(value)


# --- în foaia de parcurs ------------------------------------------------------------------------------------------------------
def trip_days(trip):
    """Zilele GPS ale vehiculului cursei, de la ziua plecării la ziua întoarcerii (ora Moldovei)."""
    from .services import local_day

    if not trip.vehicle_id:
        return [], []
    start, end = local_day(trip.departure), local_day(trip.arrival)
    rows = list(GpsDay.objects.filter(vehicle_id=trip.vehicle_id, day__gte=start, day__lte=end).order_by("day"))
    have = {r.day for r in rows}
    missing = [start + timedelta(days=i) for i in range((end - start).days + 1) if start + timedelta(days=i) not in have]
    return rows, missing


def trip_info(trip) -> dict:
    from .services import trip_km

    rows, missing = trip_days(trip)
    km = sum((r.km for r in rows), ZERO)
    fuel_rows = [r for r in rows if r.fuel_l is not None]
    fuel = sum((r.fuel_l for r in fuel_rows), ZERO) if rows and len(fuel_rows) == len(rows) and not missing else None
    sheet = trip_km(trip)
    diff_pct = float((sheet - km) / km * 100) if km else None
    odo = [r for r in rows if r.odometer_start is not None or r.odometer_end is not None]
    return {
        "days": [{"day": r.day, "km": float(r.km), "moving_min": r.moving_min, "engine_min": r.engine_min,
                  "first_start": r.first_start.strftime("%H:%M") if r.first_start else "",
                  "last_stop": r.last_stop.strftime("%H:%M") if r.last_stop else "",
                  "fuel_l": float(r.fuel_l) if r.fuel_l is not None else None, "odometer_start": r.odometer_start,
                  "odometer_end": r.odometer_end, "countries": [c for c in r.countries.split(",") if c], "source": r.source}
                 for r in rows],
        "missing": missing, "km": float(km), "fuel": float(fuel) if fuel is not None else None, "sheet_km": float(sheet),
        "diff_pct": round(diff_pct, 1) if diff_pct is not None else None,
        "odometer_out": odo[0].odometer_start if odo else None, "odometer_in": odo[-1].odometer_end if odo else None,
        "countries": list(dict.fromkeys(c for r in rows for c in r.countries.split(",") if c)),
    }


def trip_fuel(trip):
    """Consumul cursei din GPS: doar dacă fiecare zi a cursei are combustibilul; altfel None."""
    rows, missing = trip_days(trip)
    if not rows or missing or any(r.fuel_l is None for r in rows):
        return None
    return sum((r.fuel_l for r in rows), ZERO)


def trip_warnings(trip) -> list:
    """Avertismentele GPS ale cursei (nu opresc aprobarea): km foii față de km din GPS, zilele fără GPS."""
    if not trip.vehicle_id or not (trip.vehicle.gps_id or GpsDay.objects.filter(vehicle_id=trip.vehicle_id).exists()):
        return []
    info = trip_info(trip)
    out = []
    if not info["days"]:
        return ["GPS: vehiculul n-are zile importate în perioada cursei."]
    if info["missing"]:
        out.append("GPS: lipsesc zilele " + ", ".join(f"{d:%d.%m}" for d in info["missing"][:10]))
    from apps.payroll.engine import Constants

    from .services import local_day

    tol = Constants(local_day(trip.arrival))("gps_km_tolerance_pct", "5")
    if info["diff_pct"] is not None and abs(Decimal(str(info["diff_pct"]))) > tol:
        out.append(f"GPS: în foaia de parcurs {fmt(info['sheet_km'])} km, în GPS {fmt(info['km'])} km pe zilele cursei "
                   f"({'+' if info['diff_pct'] > 0 else ''}{fmt(info['diff_pct'])} %, admis ±{fmt(tol)} %)")
    return out
