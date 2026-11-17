"""Exportul pontajului pentru 1C Salariu / contabilitate: un fișier Excel cu totalurile pe raport și zilele lunii."""
import io

from django.http import HttpResponse

from .services import CODE_LABELS


def timesheets_xlsx(timesheets, year: int, month: int) -> HttpResponse:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    rows = []
    for ts in timesheets:
        for ln in ts.lines.select_related("employment__employee", "employment__occupation", "employment__subdivision").order_by("sort"):
            rows.append((ts, ln))
    codes = sorted({c for _ts, ln in rows for c in (ln.totals or {}).get("codes", {})})
    wb = Workbook()
    ws = wb.active
    ws.title = "Pontaj"
    head = ["Nr. tabel", "Numele, prenumele", "IDNP", "Subdiviziunea", "Funcția", "Tipul angajării", "Norma (unități)",
            "Zile lucrate", "Ore lucrate", "Ore de noapte", "Ore de sărbători", "Norma de ore", "Ore suplimentare",
            "Ore nelucrate", *[f"{c} — {CODE_LABELS.get(c, c)} (zile)" for c in codes]]
    ws.append(head)
    for _ts, ln in rows:
        job, t = ln.employment, ln.totals or {}
        ws.append([job.employee.tab_number, job.employee.full_name(), job.employee.idnp, _ts.subdivision.name_ro,
                   job.occupation.name_ro, job.get_kind_display(), float(job.rate), t.get("days", 0), t.get("hours", 0),
                   t.get("night", 0), t.get("holiday", 0), t.get("norm", 0), t.get("overtime", 0), t.get("missing", 0),
                   *[t.get("codes", {}).get(c, 0) for c in codes]])
    days = ws.parent.create_sheet("Zile")
    days.append(["Nr. tabel", "Numele, prenumele", "Subdiviziunea", "Funcția", *[str(d) for d in range(1, 32)]])
    for _ts, ln in rows:
        cells = ln.days or {}
        days.append([ln.employment.employee.tab_number, ln.employment.employee.full_name(), _ts.subdivision.name_ro,
                     ln.employment.occupation.name_ro,
                     *[_cell_text(cells.get(str(d))) for d in range(1, 32)]])
    bold, fill = Font(bold=True), PatternFill("solid", fgColor="E6F4EA")
    for sheet in (ws, days):
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
