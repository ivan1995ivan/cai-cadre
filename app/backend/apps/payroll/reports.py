"""Raportările fiscale și către CNAS: fișa personală anuală (anexa 8 la HG 697/2014), IPC21 (lunar), IALS21 (anual),
IRM19 (angajări, încetări, suspendări, concediile de îngrijire a copilului din ordine).

Previzualizarea, exportul Excel și declarația XML (apps.payroll.xml_export, după schemele SFS) pornesc din aceleași rânduri:
venitul achitat și impozitele reținute — din îndreptările spre plată achitate (impozitul se reține la plată), baza CAS — din
calculele aprobate, mișcările de personal — din ordinele semnate.
"""
import io
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.http import HttpResponse

from apps.core.models import SystemSetting

from .models import ExemptionRequest

ZERO = Decimal("0")
MONTHS = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie",
          "noiembrie", "decembrie"]
SETTINGS_KEY = "tax_report_settings"
# datele din antetul declarațiilor (pe lângă cele din Constante: IDNO, CAEM, denumirea, directorul, contabilul-șef)
DEFAULTS = {"income_source": "SAL", "cnas_code": "", "sfs_code": "", "cuatm": "", "email": "", "phone": ""}
SETTINGS_FIELDS = list(DEFAULTS)


def get_settings() -> dict:
    return {**DEFAULTS, **(SystemSetting.read(SETTINGS_KEY, {}) or {})}


def _f(value) -> float:
    return float(Decimal(value or 0).quantize(Decimal("0.01")))


def header_problems() -> list:
    """Ce lipsește din antetul declarațiilor (IDNO, cod CNAS, SFS, CUATM, CAEM)."""
    from apps.core.models import Company

    c, cfg = Company.get(), get_settings()
    missing = [label for label, value in (("IDNO (Constante)", c.idno), ("codul CNAS", cfg["cnas_code"]),
                                          ("codul Serviciului Fiscal de Stat", cfg["sfs_code"]), ("CUATM", cfg["cuatm"]),
                                          ("CAEM (Constante)", c.caem)) if not value]
    return missing


# --- fișa personală anuală -------------------------------------------------------------------------------------------
def annual_card(employee, year: int) -> dict:
    """Fișa personală (anexa 8, forma 2018): pe fiecare plată achitată în an — data, venitul achitat (curent și cumulat),
    scutirea, primele CNAM, venitul impozabil, impozitul calculat și cel reținut (+/−)."""
    from apps.core.models import Company

    from .models import PaymentLine

    payments = list(PaymentLine.objects.filter(employee=employee, payment__status="paid", payment__paid_on__year=year,
                                               payment__deletion_mark=False)
                    .select_related("payment").order_by("payment__paid_on", "payment_id"))
    rows, cum = [], {"gross": ZERO, "cnam": ZERO, "taxable": ZERO, "tax": ZERO}
    pct = Decimal("0.12")
    for ln in payments:
        taxable = max(ln.gross - ln.cnam - ln.exemption, ZERO)
        items = {"gross": ln.gross, "exemption": ln.exemption, "cnam": ln.cnam, "taxable": taxable, "tax": ln.income_tax}
        for k in cum:
            cum[k] += items[k]
        rows.append({"date": ln.payment.paid_on.strftime("%d.%m.%Y"), "month": ln.payment.month,
                     "month_name": MONTHS[ln.payment.month], "kind": ln.payment.get_kind_display(),
                     **{k: _f(v) for k, v in items.items()}, "tax_calc": _f(taxable * pct),
                     "cum_gross": _f(cum["gross"]), "cum_cnam": _f(cum["cnam"]), "cum_taxable": _f(cum["taxable"]),
                     "cum_tax": _f(cum["tax"])})
    req = ExemptionRequest.objects.filter(employee=employee, year=year).first()
    total = {k: _f(sum((Decimal(str(r[k])) for r in rows), ZERO)) for k in ("gross", "exemption", "cnam", "taxable", "tax", "tax_calc")}
    jobs = list(employee.employments.order_by("date_from"))
    hired = jobs[0].date_from if jobs else None
    ended = [j.end_date for j in jobs if j.end_date]
    company = Company.get()
    return {"employee": employee.pk, "name": employee.full_name(), "idnp": employee.idnp, "tab_number": employee.tab_number,
            "address": getattr(employee, "address", "") or "", "spouse_idnp": (getattr(req, "spouse_idnp", "") or "") if req else "",
            "hired": hired.strftime("%d.%m.%Y") if hired else "",
            "dismissed": max(ended).strftime("%d.%m.%Y") if ended and len(ended) == len(jobs) else "",
            "employer": company.name_ro, "employer_idno": company.idno,
            "year": year, "exemption_code": req.code() if req else "—", "exemption_date": (
                req.date_from.strftime("%d.%m.%Y") if req and req.date_from else ""),
            "rows": rows, "total": total}


# --- IPC21 (lunar) ---------------------------------------------------------------------------------------------------
def ipc21(year: int, month: int) -> dict:
    """Tabelul 1 (SAL) și tabelul 2 pe persoane și categorii, exact cum intră în declarația XML."""
    from .xml_export import ipc21_rows

    data = ipc21_rows(year, month)
    rows = [{"no": r["c1"], "idnp": r["c3"], "name": r["c2"], "cpas": r["c4"], "date_from": r["c5"], "date_to": r["c6"],
             "category": r["c7"], "tariff": _f(r["c71"]), "occupation_code": r["c8"], "base": _f(r["c9"]), "sick": _f(r["c10"]),
             "cas": _f(r["c11"]), "missing_idnp": r["c3"] in ("", "0"), "missing_code": not r["c8"]} for r in data["rows"]]
    persons = len({r["no"] for r in rows})
    return {"year": year, "month": month, "rows": rows, "header_missing": header_problems(),
            "table1": {"income": _f(data["gross"]), "tax": _f(data["tax"]), "cnam": _f(data["cnam"])},
            "total": {"persons": persons, "base": _f(data["t9"]), "sick": _f(data["t10"]), "cas": _f(data["t11"])},
            "missing_idnp": len({r["no"] for r in rows if r["missing_idnp"]})}


# --- IALS21 (anual) --------------------------------------------------------------------------------------------------
def ials21(year: int) -> dict:
    from .xml_export import ials21_rows

    data = ials21_rows(year)
    rows = [{"no": r["number"], "idnp": r["idnp"], "name": r["name"], "spouse_idnp": r["spouse"], "source": r["source"],
             "income": _f(r["income"]), "P": _f(r["P"]), "M": _f(r["M"]), "Sm": _f(r["Sm"]), "N": _f(r["N"]), "H": _f(r["H"]),
             "exemption": _f(r["total"]), "cnam": _f(r["cnam"]), "tax": _f(r["tax"]), "missing_idnp": not r["idnp"]}
            for r in data["rows"]]
    total = {k: _f(sum((Decimal(str(r[k])) for r in rows), ZERO)) for k in ("income", "P", "M", "Sm", "N", "H", "exemption", "cnam", "tax")}
    return {"year": year, "rows": rows, "dependents": data["dependents"], "header_missing": header_problems(),
            "total": {**total, "persons": len(rows)}, "missing_idnp": sum(1 for r in rows if r["missing_idnp"])}


# --- IRM19 (CNAS) ----------------------------------------------------------------------------------------------------
CODE_LABELS = {"01": "Angajare pe durată nedeterminată", "02": "Încetarea raporturilor de muncă", "03": "Suspendarea CIM",
               "04": "Ridicarea suspendării CIM", "05": "Angajare pe durată determinată"}
CATEGORY_LABELS = {"157": "Concediu de îngrijire a copilului până la 3 ani", "158": "Concediu neplătit de îngrijire a copilului 3–4 ani",
                   "165": "Concediu paternal"}


def irm19(date_from: date, date_to: date) -> dict:
    """Înscrierile din ordinele semnate în perioadă, cu codurile IRM19 și termenul de depunere."""
    from .xml_export import irm19_entries

    rows = []
    for n, x in enumerate(irm19_entries(date_from, date_to), start=1):
        order_date = x["c10"] or x["c6"]
        rows.append({"no": n, "employee": x["employee"], "idnp": x["idnp"], "cpas": x["cpas"], "name": x["name"],
                     "category": x["c5"], "period_from": x["c6"], "period_to": x["c7"], "code": x["c8"], "reason": x["c9"],
                     "date": x["c10"], "event": CODE_LABELS.get(x["c8"]) or CATEGORY_LABELS.get(x["c5"], ""), "type": x["type"],
                     "order": x["order"], "order_id": x["order_id"], "deadline": _deadline(x["order_date"]).isoformat(),
                     "missing_idnp": not x["idnp"]})
    return {"date_from": date_from, "date_to": date_to, "rows": rows, "header_missing": header_problems()}


def _deadline(day: date) -> date:
    """Termenul de depunere: 10 zile lucrătoare începând cu ziua de după data ordinului (fără weekend și sărbători)."""
    from apps.org import calendar

    holidays = calendar.holidays_between(day, day + timedelta(days=30))
    d, left = day, 10
    while left:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in holidays:
            left -= 1
    return d


# --- exportul Excel ---------------------------------------------------------------------------------------------------
def xlsx(filename: str, sheets: list) -> HttpResponse:
    """sheets: [(titlu, antet, rânduri)] → fișier Excel cu antetul îngroșat și lățimile potrivite."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    wb.remove(wb.active)
    for title, head, rows in sheets:
        ws = wb.create_sheet(title[:31])
        ws.append(head)
        for r in rows:
            ws.append(r)
        for cell in ws[1]:
            cell.font, cell.fill = Font(bold=True), PatternFill("solid", fgColor="E6F4EA")
        for i, col in enumerate(ws.columns, start=1):
            width = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 6), 50)
        ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    response = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _iso(d) -> str:
    return d.isoformat() if d else ""


def ipc21_xlsx(data: dict) -> HttpResponse:
    t1 = data["table1"]
    head1 = ["Cod", "Tipul sursei de venit", "Codul sursei", "Venitul calculat și îndreptat spre achitare", "Impozitul pe venit reținut",
             "Prime CNAM reținute"]
    rows1 = [[11, "Plăți salariale, art.88 din Codul fiscal", "SAL", t1["income"], t1["tax"], t1["cnam"]],
             [61, "TOTAL", "", t1["income"], t1["tax"], t1["cnam"]]]
    head2 = ["Nr. crt.", "Numele, prenumele", "IDNP", "CPAS", "De la data", "Până la data", "Categoria persoanei asigurate",
             "Tariful (%)", "Codul funcției", "Baza de calcul CAS", "Indemnizația de incapacitate", "CAS calculată"]
    rows2 = [[r["no"], r["name"], r["idnp"], r["cpas"], _iso(r["date_from"]), _iso(r["date_to"]), r["category"], r["tariff"],
              r["occupation_code"], r["base"], r["sick"], r["cas"]] for r in data["rows"]]
    return xlsx(f"IPC21-{data['year']}-{data['month']:02d}.xlsx", [("Tabelul 1", head1, rows1), ("Tabelul 2", head2, rows2)])


def ials21_xlsx(data: dict) -> HttpResponse:
    head = ["Nr.", "Codul fiscal al angajatului", "Numele și prenumele", "Codul fiscal al soțului (soției)", "Codul sursei de venit",
            "Venitul îndreptat spre achitare", "P", "M", "Sm", "N", "H", "Total scutiri", "Prime CNAM", "Impozitul reținut"]
    rows = [[r["no"], r["idnp"], r["name"], r["spouse_idnp"], r["source"], r["income"], r["P"], r["M"], r["Sm"], r["N"], r["H"],
             r["exemption"], r["cnam"], r["tax"]] for r in data["rows"]]
    deps = [[n, d["employee"], d["N"], d["H"]] for n, d in enumerate(data["dependents"], start=1)]
    return xlsx(f"IALS21-{data['year']}.xlsx", [("IALS21", head, rows),
                                                ("Persoanele întreținute", ["Nr.", "Codul fiscal al angajatului", "N", "H"], deps)])


def irm19_xlsx(data: dict) -> HttpResponse:
    head = ["Nr.", "Numele, prenumele", "IDNP", "CPAS", "Categoria (col.5)", "De la (col.6)", "Până la (col.7)",
            "Codul raporturilor de muncă (col.8)", "Motivul eliberării (col.9)", "Data (col.10)", "Ordinul", "Termenul de depunere"]
    rows = [[r["no"], r["name"], r["idnp"], r["cpas"], r["category"], _iso(r["period_from"]), _iso(r["period_to"]), r["code"],
             r["reason"], _iso(r["date"]), r["order"], r["deadline"]] for r in data["rows"]]
    return xlsx(f"IRM19-{data['date_from']}-{data['date_to']}.xlsx", [("IRM19", head, rows)])
