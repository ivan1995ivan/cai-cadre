"""Declarațiile electronice în XML, după schemele SFS / CNAS (dosarul „xml file”): IPC21 (lunar), IALS21 (anual), IRM19.

Regulile de completare vin din instrucțiunile oficiale:
- IPC21 — anexa nr. 2 la OMF 94/2020 (modificată prin OMF 109/2025): tabelul 1 rândul 11 „SAL” și 61 „TOTAL”, anexa pe
  subdiviziuni (CUATM), tabelul 2 pe persoane și categorii (clasificatorul CNAS al categoriilor persoanelor asigurate),
  rândul 1.1 a) 29 % sau b) 24 % (instituțiile medico-sanitare — 24 %);
- IALS21 — anexa nr. 2 la OMF 95/2020: scutirile pe coduri P / M / Sm / N / H, suma de control = totalul impozitului (col. 16),
  anexa cu persoanele întreținute;
- IRM19 — anexa nr. 4 la OMF 126/2017: col. 5–7 categoria riscului (157, 158, 165) cu perioada, col. 8 codul raportului de
  muncă (01 angajare pe durată nedeterminată, 02 încetare, 03 suspendare, 04 reluare, 05 angajare pe durată determinată),
  col. 9 motivul eliberării (111–116), col. 10 data.
Rubricile pe care schema le cere, dar care nu privesc o instituție medicală (dividende, royalty, nerezidenți...), se pun 0.
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from xml.etree import ElementTree as ET

from django.http import HttpResponse
from django.utils import timezone

from apps.core.models import Company
from apps.leave.models import Absence
from apps.orders.models import OrderItem

from .engine import Constants, month_bounds
from .models import ExemptionRequest, PayrollLine
from .reports import get_settings

ZERO = Decimal("0")
CENT = Decimal("0.01")

# categoria persoanei asigurate (IPC21, tabelul 2, col. 7) după tipul raportului de muncă
KIND_CATEGORY = {"main": "101", "main_student": "101", "substitute": "101", "internal": "101",
                 "external": "123", "contractor": "105"}
# absențele declarate ca perioade separate (col. 5–7) — codul categoriei
ABSENCE_CATEGORY = {"annual": "160", "extra": "16012", "study": "16011", "unpaid": "159", "childcare": "157",
                    "childcare_unpaid": "158", "paternity": "165"}
SICK_EMPLOYER_CATEGORY = "15311"  # indemnizația pentru incapacitate temporară plătită din mijloacele angajatorului
# IRM19: categoria riscului asigurat (col. 5) după tipul ordinului de concediu
IRM_CATEGORY = {"leave_childcare": "157", "leave_childcare_unpaid": "158", "leave_paternity": "165"}
# IRM19: motivul eliberării (col. 9) după codul din clasificatorul nostru (DictItem.extra["irm19"] are prioritate)
TERMINATION_CODES = {"resignation": "114", "agreement": "115", "term_end": "115", "staff_cut": "113", "unfit": "116",
                     "disciplinary": "116", "retirement": "115", "death": "116", "transfer_out": "115"}

IPC_T1_ROWS = ["r11c4", "r11c5", "r11c6", "r12c4", "r12c5", "r12c6", "r21c4", "r21c5", "r22c4", "r22c5", "r23c4", "r23c5",
               "r31c4", "r31c5", "r32c4", "r41c4", "r41c5", "r42c4", "r42c5", "r43c4", "r43c5", "r44c4", "r44c5", "r45c4",
               "r45c5", "r46c4", "r46c5", "r47c4", "r47c5", "r48c4", "r48c5", "r49c4", "r49c5", "r491c4", "r491c5", "r51c4",
               "r51c5", "r52c4", "r52c5", "r53c4", "r53c5", "r54c4", "r54c5", "r55c4", "r55c5", "r56c4", "r56c5", "r61c6",
               "r61c5", "r61c4"]
IPC_T2_ROWS = ["r11ac9", "r11ac11", "r11bc9", "r11bc11", "r12ac9", "r12ac11", "r12bc9", "r12bc11", "r13c9", "r13c11", "r14ac9",
               "r14ac11", "r14bc11", "r15c11", "r16c11", "r17c9", "r17c11", "r2c10", "r21c10", "r22c10", "r23c10", "r24c10",
               "r3c10", "r31c10", "r32c10", "r33c10", "r34c10"]


def money(value) -> str:
    return str(Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP))


def _sub(parent, tag, text=None):
    el = ET.SubElement(parent, tag)
    el.text = "" if text is None else str(text)
    return el


def _row(parent, number: int):
    """Rândul tabelului dinamic: schema cere atributul line (numărul rândului)."""
    el = ET.SubElement(parent, "row")
    el.set("line", str(number))
    return el


def _response(root, filename: str) -> HttpResponse:
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode", xml_declaration=False)
    response = HttpResponse('<?xml version="1.0" encoding="UTF-8"?>\n' + body, content_type="application/xml; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _company():
    c = Company.get()
    cfg = get_settings()
    return c, cfg


def present_date() -> str:
    return timezone.localdate().strftime("%d.%m.%Y")


# --- IPC21 ---------------------------------------------------------------------------------------------------------
def paid_in_month(year: int, month: int) -> dict:
    """Sumele îndreptărilor spre plată achitate în lună (după data achitării): venitul, impozitul, CNAM."""
    from .models import PaymentLine

    first, last = month_bounds(year, month)
    out = {"gross": ZERO, "income_tax": ZERO, "cnam": ZERO}
    for ln in PaymentLine.objects.filter(payment__status="paid", payment__deletion_mark=False, payment__paid_on__gte=first,
                                         payment__paid_on__lte=last):
        for f in out:
            out[f] += getattr(ln, f)
    return out


def ipc21_rows(year: int, month: int) -> dict:
    """Tabelul 2 pe persoane și categorii (baza CAS din calculele aprobate ale lunii) + tabelul 1 (venitul achitat în lună
    și impozitele reținute la achitare, din îndreptările spre plată)."""
    first, last = month_bounds(year, month)
    cas_pct = Constants(last)("cas_employer_pct", "24")
    lines = (PayrollLine.objects.filter(payroll__status="approved", payroll__year=year, payroll__month=month)
             .select_related("employee", "employment__occupation").prefetch_related("items__pay_type")
             .order_by("employee__last_name", "employee__first_name", "employment_id"))
    by_person = defaultdict(list)
    for ln in lines:
        by_person[ln.employee_id].append(ln)
    paid = paid_in_month(year, month)
    gross, tax, cnam = paid["gross"], paid["income_tax"], paid["cnam"]
    rows, n = [], 0
    for emp_lines in by_person.values():
        e = emp_lines[0].employee
        n += 1
        absences = list(Absence.objects.filter(employee=e, date_from__lte=last, date_to__gte=first))
        leave_base = ZERO
        groups = defaultdict(lambda: {"base": ZERO, "start": None, "end": None, "code": ""})
        sick = ZERO
        for ln in emp_lines:
            job = ln.employment
            category = KIND_CATEGORY.get(job.kind, "101")
            g = groups[category]
            start, end = max(job.date_from, first), min(job.end_date or last, last)
            g["start"] = min(g["start"] or start, start)
            g["end"] = max(g["end"] or end, end)
            g["code"] = g["code"] or (job.occupation.code if job.occupation_id else "")
            for it in ln.items.all():
                t = it.pay_type
                if t.category != "accrual":
                    continue
                if t.auto == "sick":
                    sick += it.amount
                elif t.auto == "leave":
                    leave_base += it.amount if t.cas else ZERO
                elif t.cas:
                    g["base"] += it.amount
        main_code = next((g["code"] for g in groups.values() if g["code"]), "")
        for category, g in groups.items():
            rows.append(_t2(n, e, g["start"], g["end"], category, cas_pct, g["code"] or main_code, g["base"], ZERO))
        for a in absences:
            cat = ABSENCE_CATEGORY.get(a.kind)
            if cat is None:
                continue
            base = leave_base if a.kind == "annual" else ZERO
            leave_base = ZERO if a.kind == "annual" else leave_base
            rows.append(_t2(n, e, max(a.date_from, first), min(a.date_to, last), cat, cas_pct if base else ZERO, main_code,
                            base, ZERO))
        if leave_base:  # concediul plătit fără absență în lună (de ex. calculat înainte) — cu salariul
            rows.append(_t2(n, e, first, last, "160", cas_pct, main_code, leave_base, ZERO))
        if sick:
            s = next((a for a in absences if a.kind == "sick"), None)
            rows.append(_t2(n, e, max(s.date_from, first) if s else first, min(s.date_to, last) if s else last,
                            SICK_EMPLOYER_CATEGORY, ZERO, main_code, ZERO, sick))
    t9 = sum((r["c9"] for r in rows), ZERO)
    t10 = sum((r["c10"] for r in rows), ZERO)
    t11 = sum((r["c11"] for r in rows), ZERO)
    return {"year": year, "month": month, "rows": rows, "gross": gross, "tax": tax, "cnam": cnam, "t9": t9, "t10": t10,
            "t11": t11, "cas_pct": cas_pct}


def _t2(n, e, start, end, category, pct, code, base, sick) -> dict:
    base = Decimal(base).quantize(CENT, rounding=ROUND_HALF_UP)
    return {"c1": n, "c2": e.full_name(), "c3": e.idnp or "0", "c4": e.cpas or "0", "c5": start, "c6": end, "c7": category,
            "c71": pct, "c8": code, "c9": base, "c10": Decimal(sick).quantize(CENT), "c11": (base * Decimal(pct) / 100).quantize(CENT, rounding=ROUND_HALF_UP)}


def ipc21_xml(year: int, month: int) -> HttpResponse:
    c, cfg = _company()
    data = ipc21_rows(year, month)
    root = ET.Element("dec", TypeName="IPC21")
    fc = _sub(root, "fiscCod")
    for tag, value in (("fiscal", c.idno), ("name", c.name_ro), ("cuatm", cfg["cuatm"]), ("fisc", cfg["sfs_code"]),
                       ("caem", cfg["caem"]), ("email", cfg["email"] or c.email), ("telefon", cfg["phone"] or c.phone),
                       ("cnas", cfg["cnas_code"])):
        _sub(fc, tag, value)
    _sub(_sub(root, "peroidnalog"), "datefisc", f"L/{month:02d}/{year}")
    d = _sub(root, "director")
    _sub(d, "director", c.director)
    _sub(d, "contabil", c.chief_accountant)
    t1 = _sub(root, "table1")
    ds = _sub(t1, "ds")
    _sub(ds, "flag", "1")  # primară
    _sub(ds, "flag1", "0")  # de corectare
    _sub(ds, "flag2", "0")
    _sub(_sub(t1, "it"), "flag1", "0")
    cf = _sub(t1, "cf")
    _sub(cf, "flag1", "0")
    _sub(cf, "flag2", "0")
    row = _sub(t1, "row")
    values = {"r11c4": data["gross"], "r11c5": data["tax"], "r11c6": data["cnam"],
              "r61c4": data["gross"], "r61c5": data["tax"], "r61c6": data["cnam"]}
    for tag in IPC_T1_ROWS:
        _sub(row, tag, money(values.get(tag, ZERO)))
    _sub(root, "summContr", money(data["tax"]))  # col.5 codul 61 − col.5 (codurile 41…49¹) = impozitul din salarii
    annex = _sub(root, "dinamicTable")
    r = _row(annex, 1)
    for tag, value in (("c1", "1"), ("c2", cfg["cuatm"]), ("c3", money(data["tax"])), ("c4", money(0)), ("c5", money(0))):
        _sub(r, tag, value)
    tot = _sub(annex, "total")
    _sub(tot, "tot1c3", money(data["tax"]))
    _sub(tot, "tot1c4", money(0))
    _sub(tot, "tot1c5", money(0))
    t11 = _sub(root, "table11")
    for i in range(1, 5):
        rr = _sub(t11, f"row{i}")
        for col in ("c3", "c4", "c5", "c6", "c7"):
            _sub(rr, col, money(0))
    t2 = _sub(root, "dinamicTable2")
    for i, x in enumerate(data["rows"], start=1):
        rr = _row(t2, i)
        for tag in ("c1", "c2", "c3", "c4"):
            _sub(rr, tag, x[tag])
        _sub(rr, "c5", x["c5"].isoformat())
        _sub(rr, "c6", x["c6"].isoformat())
        _sub(rr, "c7", x["c7"])
        _sub(rr, "c71", format(Decimal(x["c71"]).normalize(), "f"))
        _sub(rr, "c8", x["c8"])
        _sub(rr, "c81", "")
        for tag in ("c9", "c10", "c11"):
            _sub(rr, tag, money(x[tag]))
    tot = _sub(t2, "total")
    _sub(tot, "tot2c9", money(data["t9"]))
    _sub(tot, "tot2c10", money(data["t10"]))
    _sub(tot, "tot2c11", money(data["t11"]))
    t2s = _sub(_sub(root, "table2"), "row")
    big = data["cas_pct"] >= 29  # autoritățile bugetare 29 %; instituțiile medico-sanitare 24 %
    summary = {("r11ac9" if big else "r11bc9"): data["t9"], ("r11ac11" if big else "r11bc11"): data["t11"]}
    for tag in IPC_T2_ROWS:
        _sub(t2s, tag, money(summary.get(tag, ZERO)))
    return _response(root, f"IPC21-{year}-{month:02d}.xml")


# --- IALS21 --------------------------------------------------------------------------------------------------------
def ials21_rows(year: int) -> dict:
    """Pe persoane: venitul achitat în an, scutirile pe coduri (P, M, Sm, N, H), CNAM și impozitul reținute — din îndreptările
    spre plată achitate în an; anexa cu întreținuții."""
    from .models import PaymentLine

    people = defaultdict(lambda: {"income": ZERO, "P": ZERO, "M": ZERO, "Sm": ZERO, "N": ZERO, "H": ZERO, "cnam": ZERO, "tax": ZERO})
    names = {}
    requests = {r.employee_id: r for r in ExemptionRequest.objects.filter(year=year)}
    for ln in PaymentLine.objects.filter(payment__status="paid", payment__deletion_mark=False,
                                         payment__paid_on__year=year).select_related("employee", "payment"):
        p = people[ln.employee_id]
        names[ln.employee_id] = ln.employee
        p["income"] += ln.gross
        p["cnam"] += ln.cnam
        p["tax"] += ln.income_tax
        if ln.exemption:
            for code, share in _split(requests.get(ln.employee_id), Constants(ln.payment.paid_on)).items():
                p[code] += (ln.exemption * share).quantize(CENT, rounding=ROUND_HALF_UP)
    rows, deps = [], []
    for n, (pk, p) in enumerate(sorted(people.items(), key=lambda kv: names[kv[0]].full_name()), start=1):
        e, req = names[pk], requests.get(pk)
        total = p["P"] + p["M"] + p["Sm"] + p["N"] + p["H"]
        rows.append({"number": n, "idnp": e.idnp, "name": e.full_name(), "spouse": (req.spouse_idnp if req and p["Sm"] else ""),
                     "source": get_settings()["income_source"] or "SAL", **p, "total": total})
        for d in (req.dependents if req else []):
            deps.append({"employee": e.idnp, "N": "" if d.get("disabled") else d.get("idnp", ""), "H": d.get("idnp", "") if d.get("disabled") else ""})
    return {"year": year, "rows": rows, "dependents": deps}


def _split(req, const) -> dict:
    """Ponderea fiecărui cod de scutire în scutirea lunară (după sumele anuale din constante)."""
    if req is None:
        return {"P": Decimal(1)}
    parts = {"P": const("exemption_personal") if req.kind == "personal" else ZERO,
             "M": const("exemption_major") if req.kind == "major" else ZERO,
             "Sm": const("exemption_spouse") if req.spouse else ZERO,
             "N": const("exemption_dependent") * sum(1 for d in req.dependents if not d.get("disabled")),
             "H": const("exemption_dependent_disabled") * sum(1 for d in req.dependents if d.get("disabled"))}
    total = sum(parts.values(), ZERO)
    return {k: v / total for k, v in parts.items() if v} if total else {"P": Decimal(1)}


def ials21_xml(year: int) -> HttpResponse:
    c, cfg = _company()
    data = ials21_rows(year)
    root = ET.Element("dec", TypeName="IALS21")
    fc = _sub(root, "fiscCod")
    for tag, value in (("fiscal", c.idno), ("name", c.name_ro[:127]), ("datefisc", f"A/{year}"), ("cuatm", cfg["cuatm"]),
                       ("fisc", cfg["sfs_code"]), ("caem", cfg["caem"])):
        _sub(fc, tag, value)
    _sub(root, "nrinscr", len(data["rows"]))
    _sub(root, "dataPrezent", present_date())
    dt = _sub(root, "dinamicTable")
    totals = defaultdict(lambda: ZERO)
    for i, x in enumerate(data["rows"], start=1):
        r = _row(dt, i)
        for tag, value in (("number", x["number"]), ("tinsalcds", x["idnp"]), ("namettl", x["name"]), ("tinsotcds", x["spouse"]),
                           ("codsurcdc", x["source"]), ("sumvencur", money(x["income"])), ("alpha3cod", ""),
                           ("sumscpcur", money(x["P"])), ("sumscmcur", money(x["M"])), ("sumscsmcur", money(x["Sm"])),
                           ("sumscncur", money(x["N"])), ("sumschcur", money(x["H"])), ("sumsctotcur", money(x["total"])),
                           ("summedcur", money(x["cnam"])), ("sumded2cur", money(0)), ("sumimpcur", money(x["tax"]))):
            _sub(r, tag, value)
        for k in ("income", "P", "M", "Sm", "N", "H", "total", "cnam", "tax"):
            totals[k] += x[k]
    tr = _sub(dt, "totalRow")
    for tag, k in (("ventotcur", "income"), ("scpcur", "P"), ("scmcur", "M"), ("scsmcur", "Sm"), ("scncur", "N"),
                   ("schcur", "H"), ("sctotcur", "total"), ("medcur", "cnam")):
        _sub(tr, tag, money(totals[k]))
    _sub(tr, "ded2cur", money(0))
    _sub(tr, "impreticur", money(totals["tax"]))
    _sub(_sub(root, "GroupsummContr"), "summContr", money(totals["tax"]))  # suma totală pe Notă, col. 16
    d = _sub(root, "director")
    _sub(d, "director", c.director)
    _sub(d, "contabil", c.chief_accountant)
    dt2 = _sub(root, "dinamicTable2")
    for n, x in enumerate(data["dependents"], start=1):
        r = _row(dt2, n)
        for tag, value in (("number", n), ("tinang", x["employee"]), ("tinpin", x["N"]), ("tinpih", x["H"])):
            _sub(r, tag, value)
    return _response(root, f"IALS21-{year}.xml")


# --- IRM19 ---------------------------------------------------------------------------------------------------------
def irm19_entries(date_from: date, date_to: date) -> list:
    """Înscrierile IRM19 din ordinele semnate în perioadă (doar cele cu cod: angajare, încetare, suspendare, reluare,
    concediile de îngrijire a copilului și paternal)."""
    items = (OrderItem.objects.filter(order__status="signed", employee__isnull=False, order__date__gte=date_from,
                                      order__date__lte=date_to)
             .select_related("order__order_type", "employee", "employment").order_by("order__date", "order__seq", "sort"))
    out = []
    for it in items:
        ot, e, p = it.order.order_type, it.employee, it.params or {}
        job = it.employment
        start = _d(p.get("date_from")) or it.order.date
        entry = {"employee": e.pk, "name": e.full_name(), "idnp": e.idnp, "cpas": e.cpas or "0", "c5": "", "c6": None,
                 "c7": None, "c8": "", "c9": "", "c10": None, "order": it.order.reference(), "order_id": it.order_id,
                 "order_date": it.order.date, "type": ot.name_ro}
        if ot.code in IRM_CATEGORY:
            entry.update({"c5": IRM_CATEGORY[ot.code], "c6": start, "c7": _d(p.get("date_to"))})
        elif ot.effect in ("hire", "substitution"):
            fixed = bool(p.get("date_to")) or (job is not None and job.date_to)
            entry.update({"c8": "05" if fixed else "01", "c10": start})
        elif ot.effect == "terminate":
            entry.update({"c8": "02", "c9": _reason(p.get("reason")), "c10": start})
        elif ot.effect == "suspend":
            entry.update({"c8": "03", "c10": start})
        elif ot.effect == "resume":
            entry.update({"c8": "04", "c10": start})
        else:
            continue
        out.append(entry)
    return out


def _d(value):
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _reason(pk) -> str:
    from apps.org.models import DictItem

    item = DictItem.objects.filter(pk=pk).first() if pk else None
    if item is None:
        return "116"
    return str((item.extra or {}).get("irm19") or TERMINATION_CODES.get(item.code, "116"))


def irm19_xml(date_from: date, date_to: date) -> HttpResponse:
    c, cfg = _company()
    root = ET.Element("dec", TypeName="IRM19")
    fc = _sub(root, "fiscCod")
    for tag, value in (("fiscal", c.idno), ("name", c.name_ro), ("cnas", cfg["cnas_code"]), ("fisc", cfg["sfs_code"]),
                       ("email", cfg["email"] or c.email), ("telefon", cfg["phone"] or c.phone)):
        _sub(fc, tag, value)
    _sub(root, "dataPrezent", present_date())
    ds = _sub(_sub(root, "table"), "ds")
    _sub(ds, "primara", "1")
    _sub(ds, "corectare", "0")
    _sub(root, "dlncds", "")
    dt = _sub(root, "dinamicTable")
    for n, x in enumerate(irm19_entries(date_from, date_to), start=1):
        r = _row(dt, n)
        for tag, value in (("c1", n), ("c2", x["name"]), ("c3", x["idnp"]), ("c4", x["cpas"]), ("c5", x["c5"]),
                           ("c6", x["c6"].isoformat() if x["c6"] else ""), ("c7", x["c7"].isoformat() if x["c7"] else ""),
                           ("c8", x["c8"]), ("c9", x["c9"]), ("c10", x["c10"].isoformat() if x["c10"] else ""),
                           ("c11", ""), ("c12", "")):
            _sub(r, tag, value)
    return _response(root, f"IRM19-{date_from.isoformat()}-{date_to.isoformat()}.xml")
