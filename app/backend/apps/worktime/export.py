"""Exportul pontajului pentru 1C Salariu / contabilitate: un fișier Excel cu totalurile pe raport (și orele pe tipuri:
efective, garantate, de plată), zilele lunii și foaia orelor pe tipuri pe zile."""
import io

from django.http import HttpResponse

from .services import CODE_LABELS, timesheet_report


def timesheets_xlsx(timesheets, year: int, month: int) -> HttpResponse:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    rows, summaries, types = [], {}, {}
    for ts in timesheets:
        report = timesheet_report(ts)
        for r in report["rows"]:
            summaries[r["id"]] = r["hour_types"]
        for c in report["hour_types"]:
            types.setdefault(c["code"], c["name_ro"])
        for ln in ts.lines.select_related("employment__employee", "employment__occupation", "employment__subdivision").order_by("sort"):
            rows.append((ts, ln))
    codes = sorted({c for _ts, ln in rows for c in (ln.totals or {}).get("codes", {})})
    typed = list(types)
    wb = Workbook()
    ws = wb.active
    ws.title = "Pontaj"
    head = ["Nr. tabel", "Numele, prenumele", "IDNP", "Subdiviziunea", "Funcția", "Tipul angajării", "Norma (unități)",
            "Zile lucrate", "Ore lucrate", "Ore de noapte", "Ore de sărbători", "Norma de ore", "Ore suplimentare",
            "Ore nelucrate", *[f"{c} — {CODE_LABELS.get(c, c)} (zile)" for c in codes],
            *[f"{c} — {types[c]} ({what})" for c in typed for what in ("efective", "garantate", "de plată")]]
    ws.append(head)
    for _ts, ln in rows:
        job, t = ln.employment, ln.totals or {}
        summary = summaries.get(ln.id, {})
        extra = []
        for c in typed:
            s_ = summary.get(c) or {}
            extra += [s_.get("hours", 0), s_.get("guaranteed"), s_.get("paid", 0)]
        ws.append([job.employee.tab_number, job.employee.full_name(), job.employee.idnp, _ts.subdivision.name_ro,
                   job.occupation.name_ro, job.get_kind_display(), float(job.rate), t.get("days", 0), t.get("hours", 0),
                   t.get("night", 0), t.get("holiday", 0), t.get("norm", 0), t.get("overtime", 0), t.get("missing", 0),
                   *[t.get("codes", {}).get(c, 0) for c in codes], *extra])
    days = ws.parent.create_sheet("Zile")
    days.append(["Nr. tabel", "Numele, prenumele", "Subdiviziunea", "Funcția", *[str(d) for d in range(1, 32)]])
    for _ts, ln in rows:
        cells = ln.days or {}
        days.append([ln.employment.employee.tab_number, ln.employment.employee.full_name(), _ts.subdivision.name_ro,
                     ln.employment.occupation.name_ro,
                     *[_cell_text(cells.get(str(d))) for d in range(1, 32)]])
    sheets = [ws, days]
    if typed:
        per_day = ws.parent.create_sheet("Ore pe tipuri")
        per_day.append(["Nr. tabel", "Numele, prenumele", "Funcția", "Tipul de ore", "Total pe lună", *[str(d) for d in range(1, 32)]])
        for _ts, ln in rows:
            for c, entry in sorted((ln.typed_hours or {}).items()):
                total = entry.get("month")
                cells = entry.get("days") or {}
                per_day.append([ln.employment.employee.tab_number, ln.employment.employee.full_name(),
                                ln.employment.occupation.name_ro, c, total if total is not None else sum(cells.values()),
                                *[cells.get(str(d)) for d in range(1, 32)]])
        sheets.append(per_day)
    bold, fill = Font(bold=True), PatternFill("solid", fgColor="E6F4EA")
    for sheet in sheets:
        for cell in sheet[1]:
            cell.font, cell.fill = bold, fill
        for i, col in enumerate(sheet.columns, start=1):
            width = max(len(str(c.value or "")) for c in col)
            sheet.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 5), 40)
        sheet.freeze_panes = "C2"
    buf = io.BytesIO()
    wb.save(buf)
    response = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="pontaj-{year}-{month:02d}.xlsx"'
    return response


def _cell_text(cell) -> str:
    if not cell:
        return ""
    if cell.get("h"):
        night = f"/{cell['n']:g}" if cell.get("n") else ""
        return f"{cell['h']:g}{night}"
    return cell.get("c", "")
