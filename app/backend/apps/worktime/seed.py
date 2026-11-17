"""Turele și graficele de lucru uzuale într-un spital (se creează doar dacă lipsesc; se schimbă din interfață)."""
from datetime import time
from decimal import Decimal

from .models import ShiftType, WorkSchedule

# cod, denumire, ore, din ele noaptea (22–06), începe la, gardă, culoare
SHIFTS = [
    ("8", "Zi de 8 ore (08:00–16:00)", "8", "0", time(8), False, ""),
    ("7", "Zi de 7 ore (08:00–15:00)", "7", "0", time(8), False, ""),
    ("6", "Zi de 6 ore (08:00–14:00)", "6", "0", time(8), False, ""),
    ("Z12", "Tură de zi, 12 ore (08:00–20:00)", "12", "0", time(8), False, "#fadb14"),
    ("N12", "Tură de noapte, 12 ore (20:00–08:00)", "12", "8", time(20), False, "#2f54eb"),
    ("G24", "Gardă de 24 de ore (08:00–08:00)", "24", "8", time(8), True, "#f5222d"),
    ("G16", "Gardă după program (16:00–08:00)", "16", "8", time(16), True, "#fa541c"),
]

# cod, denumire, tipul, ore pe săptămână, turele săptămânii (luni–duminică) sau ale ciclului
SCHEDULES = [
    ("5x8", "5 zile × 8 ore (40 h pe săptămână)", "week", "40", ["8", "8", "8", "8", "8", "", ""]),
    ("5x7", "5 zile × 7 ore (35 h pe săptămână)", "week", "35", ["7", "7", "7", "7", "7", "", ""]),
    ("5x6", "5 zile × 6 ore (30 h pe săptămână)", "week", "30", ["6", "6", "6", "6", "6", "", ""]),
    ("6z", "6 zile (35 h: 5 × 6 + sâmbăta 5)", "week", "35", ["6", "6", "6", "6", "6", "5", ""]),
    ("ZN", "Ture de 12 ore: zi, noapte, 2 zile libere", "cycle", "40", ["Z12", "N12", "", ""]),
    ("G24", "Gardă de 24 de ore, 3 zile libere", "cycle", "40", ["G24", "", "", ""]),
]


def run():
    for i, (code, name, hours, night, start, duty, color) in enumerate(SHIFTS, start=1):
        ShiftType.objects.get_or_create(code=code, defaults={
            "name": name, "hours": Decimal(hours), "night_hours": Decimal(night), "start": start, "is_duty": duty,
            "color": color, "sort": i * 10})
    for code, name, kind, hours, codes in SCHEDULES:
        WorkSchedule.objects.get_or_create(code=code, defaults={
            "name": name, "kind": kind, "weekly_hours": Decimal(hours),
            **({"week": codes} if kind == "week" else {"cycle": codes, "holidays_off": False})})
