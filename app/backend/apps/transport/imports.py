"""Importul curselor din Excel (apps.core.excel_import): un rând = un segment de țară al unei curse; rândurile cu același
„Nr. cursei” (numărul din fișier — de ex. din programul de evidență sau din GPS) formează o cursă nouă, ciornă. Datele cursei
(șoferul, vehiculul, plecarea, întoarcerea, km…) se iau din primul ei rând; la cursa în țară coloanele țării rămân goale.
După import cursele se socotesc (km, tariful, diurna) — se aprobă din ecran."""
from datetime import datetime
from decimal import Decimal

from django.utils import timezone

from apps.core.excel_import import Column, RowError, Spec, _norm
from apps.staff.models import Employment

from .models import Country, Trip, TripLeg, Vehicle

KINDS = {"marfa": "goods", "marfuri": "goods", "goods": "goods", "грузы": "goods", "pasageri": "passengers",
         "passengers": "passengers", "пассажиры": "passengers"}
SCOPES = {"intern": "domestic", "in tara": "domestic", "domestic": "domestic", "международный": "international",
          "international": "international", "extern": "international", "внутренний": "domestic"}


def trips_spec() -> Spec:
    return Spec(
        code="trips", title="Cursele (foile de parcurs)",
        columns=[
            Column("trip", "Nr. cursei (în fișier)", required=True, example="1", aliases=("cursa", "nr cursa", "рейс", "№ рейса")),
            Column("tab_number", "Nr. tabel șofer", example="12", aliases=("sofer", "табельный номер", "tab")),
            Column("employment", "Raportul de muncă", example="", aliases=("functia", "трудовое отношение")),
            Column("co_tab", "Nr. tabel al doilea șofer", example="", aliases=("al doilea sofer", "второй водитель")),
            Column("vehicle", "Vehiculul (nr. de înmatriculare)", example="ABC 123", aliases=("vehicul", "автомобиль")),
            Column("trailer", "Remorca", example="", aliases=("semiremorca", "прицеп")),
            Column("kind", "Felul (marfă / pasageri)", example="marfă", aliases=("felul", "вид")),
            Column("scope", "Aria (în țară / internațional)", example="internațional", aliases=("aria", "направление")),
            Column("departure", "Plecarea (zz.ll.aaaa hh:mm)", example="02.03.2026 06:00", aliases=("plecarea", "выезд")),
            Column("arrival", "Întoarcerea (zz.ll.aaaa hh:mm)", example="09.03.2026 20:00",
                   aliases=("intoarcerea", "возвращение")),
            Column("km", "Km", kind="decimal", example=2850, aliases=("kilometri", "км")),
            Column("odometer_out", "Kilometrajul la plecare", kind="int", example="", aliases=("km plecare", "спидометр выезд")),
            Column("odometer_in", "Kilometrajul la întoarcere", kind="int", example="", aliases=("km intoarcere", "спидометр возврат")),
            Column("route", "Ruta", example="Chișinău – Iași – Budapesta – München", aliases=("маршрут",)),
            Column("country", "Țara (cod ISO 2)", example="RO", aliases=("tara", "страна")),
            Column("entered", "Intrarea în țară (zz.ll.aaaa hh:mm)", example="02.03.2026 09:30", aliases=("intrarea", "въезд")),
            Column("left", "Ieșirea din țară (zz.ll.aaaa hh:mm)", example="03.03.2026 04:10", aliases=("iesirea", "выезд из страны")),
            Column("loading", "Încărcare", kind="bool", example="nu", aliases=("incarcare", "погрузка")),
            Column("unloading", "Descărcare", kind="bool", example="nu", aliases=("descarcare", "разгрузка")),
            Column("meals", "Masa asigurată", kind="bool", example="nu", aliases=("masa", "питание")),
            Column("adr", "ADR", kind="bool", example="nu", aliases=("мопог",)),
            Column("note", "Observații", example="", aliases=("примечание",)),
        ],
        save_row=save_row,
        notes=["Un rând pe fiecare țară străină a cursei; rândurile cu același „Nr. cursei” fac o cursă. Datele cursei se iau din "
               "primul ei rând. Cursa în țară — un singur rând, fără țară.",
               "Ora se scrie „zz.ll.aaaa hh:mm” (ora Moldovei); intrarea / ieșirea — ora trecerii frontierei."],
    )


def _dt(value, title, required=True):
    if value in (None, ""):
        if required:
            raise RowError(f"„{title}” este obligatoriu.")
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        dt = None
        for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            raise RowError(f"„{title}”: „{text}” nu e o dată cu ora (zz.ll.aaaa hh:mm).")
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def _job(tab, job_text, day, user):
    from apps.staff import services as staff

    jobs = [j for j in Employment.objects.filter(employee__tab_number=tab).exclude(kind="contractor")
            .select_related("employee", "occupation") if j.is_active_on(day)]
    if not jobs:
        raise RowError(f"Nr. de tabel {tab}: nu are raport de muncă activ la {day:%d.%m.%Y}.")
    if not staff.can_see(jobs[0].employee, user, "transport"):
        raise RowError(f"Nr. de tabel {tab}: angajatul nu este în subdiviziunile dvs.")
    if job_text:
        want = _norm(job_text)
        found = [j for j in jobs if want in (str(j.pk), _norm(j.occupation.name_ro), _norm(j.get_kind_display()), _norm(j.kind))]
        if len(found) != 1:
            raise RowError(f"Raportul de muncă „{job_text}” nu se găsește (sau nu e unic) pentru nr. de tabel {tab}.")
        return found[0]
    if len(jobs) > 1:
        main = [j for j in jobs if j.kind == "main"]
        if len(main) == 1:
            return main[0]
        raise RowError(f"Nr. de tabel {tab} are {len(jobs)} raporturi de muncă; completați „Raportul de muncă”.")
    return jobs[0]


def _vehicle(plate, title, trailer=False):
    plate = " ".join(str(plate or "").upper().split())
    if not plate:
        return None
    v = Vehicle.objects.filter(plate=plate).first() or Vehicle.objects.filter(plate=plate.replace(" ", "")).first()
    if v is None:
        raise RowError(f"„{title}”: vehiculul {plate} nu există (Setări → Vehiculele).")
    if trailer != (v.kind == "trailer"):
        raise RowError(f"„{title}”: {plate} " + ("nu e remorcă." if trailer else "e remorcă."))
    return v


def save_row(values, context):
    key = str(values.get("trip") or "").strip()
    trips = context["trips"]
    trip = trips.get(key)
    if trip is None:
        # primul rând al cursei are datele ei (șoferul, vehiculul, plecarea, întoarcerea)
        for col, title in (("tab_number", "Nr. tabel șofer"), ("vehicle", "Vehiculul (nr. de înmatriculare)")):
            if not str(values.get(col) or "").strip():
                raise RowError(f"„{title}” este obligatoriu în primul rând al cursei {key}.")
        dep = _dt(values.get("departure"), "Plecarea")
        arr = _dt(values.get("arrival"), "Întoarcerea")
        if arr <= dep:
            raise RowError("Întoarcerea este înaintea plecării.")
        day = timezone.localtime(dep).date()
        driver = _job(str(values.get("tab_number") or "").strip(), str(values.get("employment") or "").strip(), day,
                      context["user"])
        co = None
        if values.get("co_tab"):
            co = _job(str(values["co_tab"]).strip(), "", day, context["user"])
        kind = KINDS.get(_norm(values.get("kind") or "marfa"))
        scope = SCOPES.get(_norm(values.get("scope") or ("international" if values.get("country") else "intern")))
        if kind is None or scope is None:
            raise RowError("Felul (marfă / pasageri) sau aria (în țară / internațional) nu se recunoaște.")
        km = values.get("km")
        if km is not None and km < 0:
            raise RowError("Km nu pot fi negativi.")
        from apps.core.models import NumberSeries

        trip = Trip.objects.create(
            number=NumberSeries.next_number("trip"), driver=driver, co_driver=co,
            vehicle=_vehicle(values.get("vehicle"), "Vehiculul"), trailer=_vehicle(values.get("trailer"), "Remorca", trailer=True),
            kind=kind, scope=scope, departure=dep, arrival=arr, km=km or Decimal("0"),
            odometer_out=values.get("odometer_out"), odometer_in=values.get("odometer_in"), route=values.get("route") or "",
            adr=bool(values.get("adr")), note=values.get("note") or "", created_by=context["user"])
        trips[key] = trip
        status = "created"
    else:
        status = "updated"
    code = str(values.get("country") or "").strip().upper()
    if code:
        country = Country.objects.filter(code=code).first()
        if country is None:
            raise RowError(f"Țara „{code}” nu există (Setări → Țările și diurnele).")
        entered = _dt(values.get("entered"), "Intrarea în țară")
        left = _dt(values.get("left"), "Ieșirea din țară")
        if left <= entered:
            raise RowError("Ieșirea din țară e înaintea intrării.")
        n = trip.legs.count() + 1
        TripLeg.objects.create(trip=trip, country=country, entered=entered, left=left, loading=bool(values.get("loading")),
                               unloading=bool(values.get("unloading")), meals=bool(values.get("meals")), sort=n * 10)
    elif status == "updated":
        raise RowError(f"Cursa {key} are deja datele; rândurile ei următoare trebuie să aibă țara.")
    return trip, status


def finish(context):
    """După import: fiecare cursă nouă se socotește (km, tariful, diurna)."""
    from . import services

    for trip in context["trips"].values():
        services.compute(Trip.objects.get(pk=trip.pk))
