"""Calendarul: sărbătorile nelucrătoare din Republica Moldova și zilele de concediu.

Codul muncii, art. 111: 1 ianuarie, 7–8 ianuarie, 8 martie, prima și a doua zi de Paști, ziua de luni la o săptămână după
Paști (Paștele Blajinilor), 1 mai, 9 mai, 1 iunie, 27 august, 31 august, 25 decembrie și hramul localității.
Durata concediului de odihnă se socotește în zile calendaristice, fără sărbătorile nelucrătoare.
"""
from datetime import date, timedelta

FIXED = [
    (1, 1, "Anul Nou"), (1, 7, "Nașterea lui Isus Hristos (Crăciunul pe stil vechi)"),
    (1, 8, "Nașterea lui Isus Hristos (Crăciunul pe stil vechi)"), (3, 8, "Ziua internațională a femeii"),
    (5, 1, "Ziua internațională a solidarității oamenilor muncii"), (5, 9, "Ziua Victoriei / Ziua Europei"),
    (6, 1, "Ziua ocrotirii copilului"), (8, 27, "Ziua Independenței"), (8, 31, "Sărbătoarea „Limba noastră”"),
    (12, 25, "Nașterea lui Isus Hristos (Crăciunul pe stil nou)"),
]


def orthodox_easter(year: int) -> date:
    """Paștele ortodox (calculul iulian, mutat în calendarul gregorian: +13 zile pentru anii 1900–2099)."""
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = (d + e + 114) % 31 + 1
    return date(year, month, day) + timedelta(days=13)


def holidays_of_year(year: int) -> list:
    easter = orthodox_easter(year)
    out = [(date(year, m, d), name) for m, d, name in FIXED]
    out += [(easter, "Paștele (prima zi)"), (easter + timedelta(days=1), "Paștele (a doua zi)"),
            (easter + timedelta(days=8), "Paștele Blajinilor")]
    return sorted(out)


def ensure_year(year: int):
    """Sărbătorile anului în tabel (doar cele lipsă; cele șterse sau mutate de utilizator nu se repun)."""
    from apps.core.models import SystemSetting

    from .models import Holiday

    done = set(SystemSetting.read("holiday_years", []) or [])
    if year in done:
        return
    for day, name in holidays_of_year(year):
        Holiday.objects.get_or_create(date=day, defaults={"name": name, "auto": True})
    SystemSetting.write("holiday_years", sorted(done | {year}))


def holidays_between(start: date, end: date) -> set:
    from .models import Holiday

    for year in range(start.year, end.year + 1):
        ensure_year(year)
    return set(Holiday.objects.filter(date__gte=start, date__lte=end).values_list("date", flat=True))


def leave_days(start: date, end: date) -> int:
    """Zilele de concediu: calendaristice între date (inclusiv), fără sărbătorile nelucrătoare."""
    if end < start:
        return 0
    return (end - start).days + 1 - len(holidays_between(start, end))


def leave_end(start: date, days: int) -> date:
    """Ultima zi a concediului de `days` zile care începe la `start` (sărbătorile prelungesc concediul)."""
    if days <= 0:
        raise ValueError("Numărul de zile trebuie să fie pozitiv.")
    probe_end = start + timedelta(days=days + 40)
    holidays = holidays_between(start, probe_end)
    day, counted = start, 0
    while True:
        if day not in holidays:
            counted += 1
            if counted == days:
                return day
        day += timedelta(days=1)
