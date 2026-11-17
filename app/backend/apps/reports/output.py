"""Același raport în Excel și la tipar: rândurile de secțiune, totalul și rezumatul se pun la locul lor."""
from datetime import date


def _num(value, type_):
    if value is None or value == "":
        return ""
    if type_ == "date":
        return date.fromisoformat(value).strftime("%d.%m.%Y")
    if type_ in ("int", "num", "pct"):
        v = float(value)
        text = f"{v:,.0f}" if v == int(v) else f"{v:,.2f}"
        return text.replace(",", " ").replace(".", ",") + (" %" if type_ == "pct" else "")
    return str(value)


def xlsx_response(data: dict, filename: str):
    from apps.payroll.reports import xlsx

    cols = data["columns"]
    head = [c["title"] for c in cols]
    rows = []
    for r in data["rows"]:
        if "_section" in r:
            rows.append([r["_section"]])
            continue
        rows.append([_cell(r.get(c["key"]), c["type"]) for c in cols])
    if data.get("totals"):
        rows.append([_cell(data["totals"].get(c["key"]), c["type"]) for c in cols])
    if data.get("summary"):
        rows.append([])
        rows += [[s["label"], s["value"]] for s in data["summary"]]
    return xlsx(filename, [(data["title"][:31], head, rows)])


def _cell(value, type_):
    if value is None:
        return ""
    if type_ == "date" and value:
        return date.fromisoformat(value)
    return value


def print_context(data: dict) -> dict:
    """Rândurile gata formatate pentru șablonul „report”."""
    cols = data["columns"]
    out, no = [], 0
    for r in data["rows"]:
        if "_section" in r:
            out.append({"section": r["_section"]})
            continue
        bold = bool(r.get("_subtotal"))
        if not bold:
            no += 1
        out.append({"no": "" if bold else no, "bold": bold,
                    "cells": [{"text": _num(r.get(c["key"]), c["type"]), "num": c["type"] in ("int", "num", "pct")} for c in cols]})
    totals = data.get("totals")
    return {
        "report": {
            "title": data["title"], "subtitle": data.get("subtitle", ""), "columns": cols, "colspan": len(cols) + 1, "rows": out,
            "totals": [{"text": _num(totals.get(c["key"]), c["type"]), "num": c["type"] in ("int", "num", "pct")} for c in cols]
            if totals else None,
            "summary": [{"label": s["label"], "value": _num(s["value"], "num") if isinstance(s["value"], (int, float)) else s["value"]}
                        for s in data.get("summary", [])],
            # semnăturile proprii ale raportului (cartea de salarii: contabilul-șef și conducătorul); altfel — șeful cadrelor
            "signatures": data.get("signatures") or [],
        },
        "count": no,
    }
