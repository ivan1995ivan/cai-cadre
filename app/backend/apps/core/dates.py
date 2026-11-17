"""Filtrarea coloanelor dată+oră pe zile, fără `__date`.

`col__date__gte=zi` se face în SQL ca CAST(col AS date) pe fiecare rând: indexul coloanei nu se folosește, iar pe
MS SQL Server conversia la ora locală se face cu decalajul de iarnă, deci vara înregistrările dintre 21:00 și 22:00
(UTC) cădeau în ziua greșită. Aici zilele locale devin un interval [început, sfârșit) în ora serverului.
"""
import datetime

from django.utils import timezone


def to_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def day_start(value):
    """Începutul zilei locale (00:00) ca moment cu fus orar; None dacă data lipsește sau e greșită."""
    day = to_date(value)
    if day is None:
        return None
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))


def day_end(value):
    """Începutul zilei următoare: pentru `col__lt=day_end(zi)` („până la zi inclusiv”)."""
    day = to_date(value)
    if day is None:
        return None
    return day_start(day + datetime.timedelta(days=1))


def on_days(field: str, date_from=None, date_to=None) -> dict:
    """Filtrul pentru zilele [date_from, date_to] pe o coloană dată+oră: {"at__gte": ..., "at__lt": ...}."""
    result = {}
    if day_start(date_from):
        result[f"{field}__gte"] = day_start(date_from)
    if day_end(date_to):
        result[f"{field}__lt"] = day_end(date_to)
    return result
