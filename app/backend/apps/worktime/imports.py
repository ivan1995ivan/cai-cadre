"""Importul orelor pe tipuri (instruire, examinare, zbor…) din Excel în tabela de pontaj (apps.core.excel_import).

Un rând = un angajat, tipul de ore, ziua (gol — totalul pe lună) și orele. Angajatul cu mai multe raporturi de muncă în tabelă
are nevoie de coloana „Raportul de muncă” (funcția, felul — „cumul intern” — sau numărul raportului). Rândurile cu zi pun ora
zilei (celelalte zile rămân); rândul fără zi pune totalul lunii (zilele tipului se înlocuiesc). În același fișier, pentru
același tip și același raport, nu se amestecă zilele cu totalul.
"""
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.core.excel_import import Column, RowError, Spec, _norm

from . import hour_types
from .models import HourType


def _line(ts, tab, job_text):
    lines = [ln for ln in ts.lines.select_related("employment__employee", "employment__occupation")
             if ln.employment.employee.tab_number == tab]
    if not lines:
        raise RowError(f"Angajatul cu nr. de tabel {tab} nu este în această tabelă de pontaj.")
    if job_text:
        want = _norm(job_text)
        found = [ln for ln in lines if want in (str(ln.employment_id), _norm(ln.employment.occupation.name_ro),
                                                 _norm(ln.employment.get_kind_display()), _norm(ln.employment.kind))]
        if len(found) != 1:
            raise RowError(f"Raportul de muncă „{job_text}” nu se găsește (sau nu e unic) pentru nr. de tabel {tab}.")
        return found[0]
    if len(lines) > 1:
        raise RowError(f"Nr. de tabel {tab} are {len(lines)} raporturi de muncă în tabelă; completați „Raportul de muncă”.")
    return lines[0]


def _set(line, ht, **kw):
    try:
        hour_types.set_hours(line, ht, **kw)
    except ValidationError as exc:
        detail = exc.detail
        if isinstance(detail, dict):
            detail = next(iter(detail.values()))
        raise RowError(str(detail[0] if isinstance(detail, list) else detail)) from None


def save_row(values, context):
    ts = context["timesheet"]
    tab = str(values.get("tab_number") or "").strip()
    line = _line(ts, tab, str(values.get("employment") or "").strip())
    code = str(values.get("hour_type") or "").strip().upper()
    ht = HourType.objects.filter(code=code, is_active=True, deletion_mark=False).first()
    if ht is None:
        raise RowError(f"Tipul de ore „{code}” nu există sau nu este activ.")
    hours = values.get("hours")
    if hours is None or hours < 0 or hours > 744:
        raise RowError("Orele sunt între 0 și 744.")
    day = values.get("day")
    seen = context.setdefault("_seen", {})
    key = (line.pk, ht.code)
    mode = "day" if day is not None else "month"
    if seen.get(key, mode) != mode:
        raise RowError(f"{ht.code}: pentru același raport, în fișier se scriu zilele sau totalul pe lună, nu amândouă.")
    seen[key] = mode
    entry = dict((line.typed_hours or {}).get(ht.code) or {})
    if mode == "day":
        if ht.entry == "month":
            raise RowError(f"Tipul {ht.code} se scrie doar ca total pe lună (lăsați „Ziua” goală).")
        if hours > 24:
            raise RowError("Orele zilei sunt între 0 și 24.")
        days = dict(entry.get("days") or {}) if entry.get("month") in (None, "") else {}
        status = "updated" if str(day) in days else "created"
        days[str(day)] = float(hours)
        _set(line, ht, days=days)
    else:
        status = "updated" if entry else "created"
        _set(line, ht, month=hours)
    who = f"{line.employment.employee.full_name()} ({line.employment.occupation.name_ro})"
    return f"{who}: {ht.code} {'ziua ' + str(day) if day is not None else 'total pe lună'} — {Decimal(hours).normalize()} ore", status


def hours_spec() -> Spec:
    return Spec(
        code="hours", title="Orele pe tipuri în tabela de pontaj (instruire, examinare, zbor…)", sheet_title="Ore",
        save_row=save_row,
        columns=[
            Column("tab_number", "Nr. tabel", required=True, example="12", aliases=("numarul de tabel", "табельный номер", "tab")),
            Column("employment", "Raportul de muncă", example="", aliases=("functia", "raport", "должность", "трудовое отношение")),
            Column("hour_type", "Tipul de ore (codul)", required=True, example="INSTR", aliases=("tipul", "cod", "вид часов", "код")),
            Column("day", "Ziua (gol — total pe lună)", kind="int", example=5, aliases=("ziua", "zi", "день")),
            Column("hours", "Ore", required=True, kind="decimal", example=2, aliases=("ore", "часы")),
        ],
        notes=["„Raportul de muncă” — doar pentru angajații cu mai multe raporturi în tabelă: funcția, felul (de ex. „Cumul intern”) "
               "sau numărul raportului.",
               "Rândul cu zi pune orele zilei; rândul fără zi — totalul pe lună (zilele tipului se înlocuiesc).",
               "Codurile tipurilor de ore: Setări → Tipuri de ore."])
