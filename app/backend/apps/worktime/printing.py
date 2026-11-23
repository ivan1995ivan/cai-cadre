"""Tiparul tabelei de pontaj și al graficului de ture al subdiviziunii."""
from decimal import Decimal

from django.utils import timezone

from apps.printing.renderer import company_context
from apps.printing.views import print_document

from . import services
from .models import Roster, ShiftType, Timesheet

MONTHS = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie",
          "noiembrie", "decembrie"]


def _d(value):
    return value.strftime("%d.%m.%Y") if value else ""


def _n(value) -> str:
    return f"{value:g}".replace(".", ",") if value else ""


def _lang(request):
    return request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro"


PAY_SHORT = {"salary": "salariu", "hourly": "tarif orar", "hour_types": "tarife pe tipuri de ore", "mixed": "salariu + tarife",
             "piece": "în acord"}
COMBINATION_SHORT = {"combination": "cumulare", "substitution": "suplinire", "acting": "interimat"}


def pay_label(row) -> str:
    """„salariu + tarife; cumulare: Instructor 30 %” — remunerarea liniei pentru tipar."""
    parts = [PAY_SHORT.get(row.get("pay_mode"), "")]
    for c in row.get("combinations") or []:
        v = format(Decimal(str(c["value"])).normalize(), "f").replace(".", ",")
        unit = {"pct_own": " %", "pct_other": " %", "fixed": " lei", "hourly": " lei/oră"}.get(c["pay_mode"], "")
        parts.append(f"{COMBINATION_SHORT.get(c['kind'], '')}: {c['occupation']} {v}{unit}")
    return "; ".join(p for p in parts if p)


def _typed(s) -> str:
    """Celula tipului de ore în tipar: orele efective și, dacă diferă, cele de plată (cu garanția)."""
    if not s:
        return ""
    text = _n(s["hours"]) or "0"
    if s.get("guaranteed") is not None and s["paid"] != s["hours"]:
        text += f" → {_n(s['paid'])}"
    return text


def _top(cell) -> str:
    if not cell:
        return ""
    return _n(cell["h"]) if cell.get("h") else cell.get("c", "")


def timesheet_context(request, ts: Timesheet, lang="ro") -> dict:
    report = services.timesheet_report(ts)
    numbers = range(1, len(report["days"]) + 1)
    rows = []
    for n, r in enumerate(report["rows"], start=1):
        cells, t = r["days"], r["totals"]
        rows.append({"no": n, "name": r["name"], "tab_number": r["tab_number"], "occupation": r["occupation"],
                     "kind": r["kind_label"] if r["kind"] != "main" else "", "rate": f"{r['rate'] * 100:g}%",
                     "top": [_top(cells.get(str(d))) for d in numbers],
                     "night": [_n((cells.get(str(d)) or {}).get("n")) for d in numbers],
                     "days": t.get("days", 0), "hours": _n(t.get("hours")), "night_total": _n(t.get("night")),
                     "holiday": _n(t.get("holiday")), "norm": _n(t.get("norm")), "overtime": _n(t.get("overtime")),
                     "codes": ", ".join(f"{k} {v}" for k, v in (t.get("codes") or {}).items()),
                     "hour_types": [_typed(r["hour_types"].get(c["code"])) for c in report["hour_types"]],
                     "pay": pay_label(r)})
    used = sorted({k for r in report["rows"] for k in (r["totals"].get("codes") or {})})
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "rows": rows, "days": report["days"],
            "hour_types": [{"code": c["code"], "name": c["name_ro"]} for c in report["hour_types"]],
            "legend": [{"code": c, "label": services.CODE_LABELS.get(c, c)} for c in used],
            "doc": {"subdivision": ts.subdivision.name_ro, "month": MONTHS[ts.month], "year": ts.year,
                    "status": ts.get_status_display(), "head_name": ts.subdivision.head_name},
            "today": _d(timezone.localdate()), "placeholders": {"luna": MONTHS[ts.month], "an": ts.year}}


def roster_context(request, roster: Roster, lang="ro") -> dict:
    report = services.roster_report(roster)
    numbers = range(1, len(report["days"]) + 1)
    rows = [{"no": n, "name": r["name"], "occupation": r["occupation"], "rate": f"{r['rate'] * 100:g}%",
             "cells": [r["days"].get(str(d)) or r["absences"].get(str(d), "") for d in numbers],
             "hours": _n(r["hours"]), "nights": r["nights"] or "", "norm": _n(r["norm"])}
            for n, r in enumerate(report["rows"], start=1)]
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "rows": rows, "days": report["days"],
            "shifts": [{"code": s.code, "name": s.name} for s in ShiftType.objects.filter(is_active=True)],
            "doc": {"subdivision": roster.subdivision.name_ro, "month": MONTHS[roster.month], "year": roster.year,
                    "status": roster.get_status_display(), "head_name": roster.subdivision.head_name},
            "today": _d(timezone.localdate()), "placeholders": {"luna": MONTHS[roster.month], "an": roster.year}}


def print_timesheet(request, ts: Timesheet):
    return print_document(request, "timesheet", timesheet_context(request, ts, _lang(request)),
                          template_id=request.query_params.get("template"),
                          title=f"Tabela de pontaj {ts.month:02d}.{ts.year} — {ts.subdivision.name_ro}", lang=_lang(request))


def print_roster(request, roster: Roster):
    return print_document(request, "roster", roster_context(request, roster, _lang(request)),
                          template_id=request.query_params.get("template"),
                          title=f"Graficul {roster.month:02d}.{roster.year} — {roster.subdivision.name_ro}", lang=_lang(request))


def sample(request, lang, options):
    ts = Timesheet.objects.first()
    if ts is None:
        raise ValueError("Nu există încă tabele de pontaj.")
    return timesheet_context(request, ts, lang)


def sample_roster(request, lang, options):
    roster = Roster.objects.first()
    if roster is None:
        raise ValueError("Nu există încă grafice lunare.")
    return roster_context(request, roster, lang)
