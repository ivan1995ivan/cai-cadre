"""Turele și graficele de lucru uzuale (se creează doar dacă lipsesc; se schimbă din interfață).

Turele de 12 ore (Z12 / N12) sunt pentru munca în schimburi (CM art. 101): graficul de ture se aduce la cunoștință cu cel
puțin 14 zile înainte, două ture la rând sunt interzise, iar odihna dintre ture e cel puțin dublul turei anterioare.
"""
from datetime import time
from decimal import Decimal

from .models import HourType, ShiftType, WorkSchedule

# cod, denumire, ore, din ele noaptea (22–06), începe la, culoare
SHIFTS = [
    ("8", "Zi de 8 ore (08:00–16:00)", "8", "0", time(8), ""),
    ("7", "Zi de 7 ore (08:00–15:00)", "7", "0", time(8), ""),
    ("6", "Zi de 6 ore (08:00–14:00)", "6", "0", time(8), ""),
    ("Z12", "Tură de zi, 12 ore (08:00–20:00)", "12", "0", time(8), "#fadb14"),
    ("N12", "Tură de noapte, 12 ore (20:00–08:00)", "12", "8", time(20), "#2f54eb"),
]

# cod, denumire, tipul, ore pe săptămână, turele săptămânii (luni–duminică) sau ale ciclului
SCHEDULES = [
    ("5x8", "5 zile × 8 ore (40 h pe săptămână)", "week", "40", ["8", "8", "8", "8", "8", "", ""]),
    ("5x7", "5 zile × 7 ore (35 h pe săptămână)", "week", "35", ["7", "7", "7", "7", "7", "", ""]),
    ("5x6", "5 zile × 6 ore (30 h pe săptămână)", "week", "30", ["6", "6", "6", "6", "6", "", ""]),
    ("6z", "6 zile (35 h: 5 × 6 + sâmbăta 5)", "week", "35", ["6", "6", "6", "6", "6", "5", ""]),
    ("ZN", "Ture de 12 ore: zi, noapte, 2 zile libere", "cycle", "40", ["Z12", "N12", "", ""]),
]

# tipurile de ore generale (S4b); cele de fabrică / aviație / transport le aduc profilurile lor, iar utilizatorul își adaugă
# altele (de ex. ZBOR) din Setări → Tipuri de ore. Cod, RO, RU, EN, grupa, legătura cu orele lucrate, se introduc.
HOUR_TYPES = [
    ("INSTR", "Ore de instruire", "Часы инструктажа / обучения", "Training hours", "training", "within", "day"),
    ("EXAM", "Ore de examinare", "Часы экзаменов / проверок", "Examination hours", "exam", "within", "day"),
]


def run():
    for i, (code, ro, ru, en, group, work_time, entry) in enumerate(HOUR_TYPES, start=1):
        HourType.objects.get_or_create(code=code, defaults={
            "name_ro": ro, "name_ru": ru, "name_en": en, "group": group, "work_time": work_time, "entry": entry,
            "profile": "general", "sort": i * 10, "is_system": True})
    for i, (code, name, hours, night, start, color) in enumerate(SHIFTS, start=1):
        ShiftType.objects.get_or_create(code=code, defaults={
            "name": name, "hours": Decimal(hours), "night_hours": Decimal(night), "start": start, "color": color,
            "sort": i * 10})
    for code, name, kind, hours, codes in SCHEDULES:
        WorkSchedule.objects.get_or_create(code=code, defaults={
            "name": name, "kind": kind, "weekly_hours": Decimal(hours),
            **({"week": codes} if kind == "week" else {"cycle": codes, "holidays_off": False})})
