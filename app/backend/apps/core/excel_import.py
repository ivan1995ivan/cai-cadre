"""Importul din Excel, comun pentru toate modulele (clasificatoare, subdiviziuni, state, angajați, solduri).

Fiecare import se descrie cu un `Spec`: coloanele (antetul din șablon), funcția care transformă un rând într-o
înregistrare și cheia după care se recunoaște înregistrarea existentă. Fluxul e același peste tot:

1. „Descarcă șablonul” — fișier Excel cu antetul și un rând-exemplu (GET .../template/);
2. clientul completează, încarcă fișierul cu `dry_run=1` — vede ce se adaugă, ce se actualizează și erorile pe rânduri;
3. confirmă — se scrie într-o singură tranzacție (o eroare oprește tot importul, nimic pe jumătate).

Antetul se recunoaște după text, fără să conteze ordinea coloanelor, majusculele sau diacriticele.
"""
import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Callable

from django.db import transaction


class RowError(Exception):
    pass


@dataclass
class Column:
    key: str
    title: str  # antetul în șablon (RO)
    required: bool = False
    kind: str = "text"  # text | int | decimal | bool | date
    example: object = ""
    aliases: tuple = ()  # alte antete acceptate (RU, din 1C, din exportul altor programe)


@dataclass
class Spec:
    code: str
    title: str
    columns: list
    # (valori curățate, context) -> (obiect, "created" | "updated" | "skipped"); ridică RowError pentru rândul greșit
    save_row: Callable
    sheet_title: str = "Date"
    notes: list = field(default_factory=list)


def _norm(text) -> str:
    """Fără diacritice și majuscule; literele chirilice rămân (antetele în rusă: „Пробег”, „Дата”)."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return " ".join(text.replace("*", " ").replace("_", " ").split())


def _cell(value, col: Column):
    if value is None or (isinstance(value, str) and not value.strip()):
        if col.required:
            raise RowError(f"„{col.title}” este obligatoriu.")
        return None if col.kind != "text" else ""
    if col.kind == "text":
        if isinstance(value, float) and value.is_integer():
            value = int(value)  # codurile numerice citite de Excel ca 221104.0
        return str(value).strip()
    if col.kind == "int":
        try:
            return int(Decimal(str(value).replace(",", ".").strip()))
        except (InvalidOperation, ValueError):
            raise RowError(f"„{col.title}”: „{value}” nu este un număr întreg.") from None
    if col.kind == "decimal":
        text = str(value).replace("\u00a0", " ").strip()
        unit = re.match(r"^(-?[\d\s.,]+?)\s*(?:%|[^\W\d_]{1,4}\.?(?:\s*/\s*[^\W\d_]{1,4})?)$", text)  # „640,5 km”, „12 l”
        if unit:
            text = unit.group(1)
        try:
            return Decimal(text.replace(" ", "").replace(",", ".").replace("%", ""))
        except InvalidOperation:
            raise RowError(f"„{col.title}”: „{value}” nu este un număr.") from None
    if col.kind == "bool":
        return _norm(value) in ("1", "da", "yes", "true", "x", "+", "да", "da.")
    if col.kind == "date":
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        for candidate in (text, text.split(" ")[0], text.split("T")[0]):  # „02.03.2026 00:00:00” din exporturi
            for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%y"):
                try:
                    return datetime.strptime(candidate, fmt).date()
                except ValueError:
                    continue
        raise RowError(f"„{col.title}”: „{value}” nu este o dată (ZZ.LL.AAAA).")
    return value


def template(spec: Spec) -> bytes:
    """Șablonul Excel: antetul (obligatoriile cu *), un rând-exemplu și foaia „Instrucțiuni”."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = spec.sheet_title[:31]
    bold, fill = Font(bold=True), PatternFill("solid", fgColor="E6F5EC")
    for i, col in enumerate(spec.columns, start=1):
        cell = ws.cell(row=1, column=i, value=col.title + (" *" if col.required else ""))
        cell.font, cell.fill = bold, fill
        ws.cell(row=2, column=i, value=col.example if col.example != "" else None)
        ws.column_dimensions[cell.column_letter].width = max(12, min(45, len(col.title) + 4))
    ws.freeze_panes = "A2"
    info = wb.create_sheet("Instrucțiuni")
    lines = [spec.title, "", "Coloanele marcate cu * sunt obligatorii. Rândul 2 este un exemplu — înlocuiți-l.",
             "Ordinea coloanelor nu contează; antetul trebuie păstrat.", *spec.notes]
    for i, text in enumerate(lines, start=1):
        info.cell(row=i, column=1, value=text)
    info.column_dimensions["A"].width = 110
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _csv_rows(data: bytes):
    """Fișierul CSV (exportul altor programe): UTF-8 (cu sau fără BOM) sau Windows-1251; separatorul — „;”, „,” sau tab."""
    if data[:4] == b"\xd0\xcf\x11\xe0":
        raise RowError("Fișierul e în formatul Excel vechi (.xls): deschideți-l în Excel și salvați-l ca .xlsx sau .csv.")
    if b"\x00" in data[:4096]:
        raise RowError("Fișierul nu se poate citi: nu e Excel (.xlsx) și nici text CSV.")
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RowError("Fișierul nu se poate citi: nu e Excel (.xlsx) și nici CSV în UTF-8 / Windows-1251.")
    sample = text[:4096]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
    except csv.Error:
        delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    return [tuple(r) for r in csv.reader(io.StringIO(text), delimiter=delimiter)]


def read_rows(spec: Spec, data: bytes):
    """Citește foaia (Excel .xlsx sau CSV): (antetul găsit, coloanele lipsă, rânduri [(nr. rând, {cheie: valoare brută})])."""
    wb = None
    if data[:2] == b"PK":
        from openpyxl import load_workbook

        try:
            wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        except Exception as exc:  # noqa: BLE001 – fișier stricat sau alt format
            raise RowError(f"Fișierul nu se poate citi ca Excel (.xlsx): {exc}") from exc
        ws = wb[spec.sheet_title] if spec.sheet_title in wb.sheetnames else wb.worksheets[0]
        rows = ws.iter_rows(values_only=True)
    else:
        rows = iter(_csv_rows(data))
    header = next(rows, None) or ()
    lookup = {}
    for col in spec.columns:
        for name in (col.title, col.key, *col.aliases):
            lookup[_norm(name)] = col.key
    positions = {}
    for idx, title in enumerate(header):
        key = lookup.get(_norm(title))
        if key and key not in positions:
            positions[key] = idx
    missing = [c.title for c in spec.columns if c.required and c.key not in positions]
    out = []
    for n, values in enumerate(rows, start=2):
        if not values or all(v is None or (isinstance(v, str) and not v.strip()) for v in values):
            continue
        out.append((n, {key: (values[i] if i < len(values) else None) for key, i in positions.items()}))
    if wb is not None:
        wb.close()
    return list(positions), missing, out


def run(spec: Spec, data: bytes, *, dry_run: bool, context: dict | None = None) -> dict:
    """Importul: în modul „încercare” se face tot, apoi tranzacția se anulează — rezultatul e exact ce s-ar scrie."""
    context = dict(context or {})
    try:
        found, missing, rows = read_rows(spec, data)
    except RowError as exc:
        return {"ok": False, "detail": str(exc), "errors": [], "created": 0, "updated": 0, "skipped": 0, "rows": 0}
    if missing:
        return {"ok": False, "detail": "Lipsesc coloanele obligatorii: " + ", ".join(missing),
                "errors": [], "created": 0, "updated": 0, "skipped": 0, "rows": len(rows)}
    by_key = {c.key: c for c in spec.columns}
    result = {"created": 0, "updated": 0, "skipped": 0, "errors": [], "rows": len(rows), "preview": []}

    class _Rollback(Exception):
        pass

    try:
        with transaction.atomic():
            for n, raw in rows:
                try:
                    values = {k: _cell(raw.get(k), col) for k, col in by_key.items() if k in raw}
                    for col in spec.columns:
                        if col.required and col.key not in values:
                            raise RowError(f"„{col.title}” este obligatoriu.")
                    with transaction.atomic():
                        obj, status = spec.save_row(values, context)
                    result[status] += 1
                    if len(result["preview"]) < 30:
                        result["preview"].append({"row": n, "status": status, "text": str(obj)})
                except RowError as exc:
                    result["errors"].append({"row": n, "error": str(exc)})
                except Exception as exc:  # noqa: BLE001 – eroare neprevăzută pe un rând: o arătăm, nu cădem
                    result["errors"].append({"row": n, "error": f"Eroare: {exc}"})
            if dry_run or result["errors"]:
                raise _Rollback
    except _Rollback:
        pass
    result["ok"] = not result["errors"]
    result["dry_run"] = dry_run
    result["saved"] = not dry_run and not result["errors"]
    if result["errors"] and not dry_run:
        result["detail"] = "Importul nu s-a făcut: corectați rândurile cu erori și încărcați din nou."
    return result
