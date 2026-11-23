"""Importul în raportul de producție din Excel (apps.core.excel_import): lucrările (un rând = lucrarea, cantitățile, orele și,
la raportul individual, angajatul) și membrii brigăzii (angajatul, orele, coeficientul de participare). Rândurile se adaugă
la cele din raport; membrul existent al brigăzii se actualizează. Angajatul cu mai multe raporturi de muncă are nevoie de
coloana „Raportul de muncă” (funcția, felul — „cumul intern” — sau numărul raportului)."""
from decimal import Decimal

from apps.core.excel_import import Column, RowError, Spec, _norm
from apps.staff.models import Employment

from .models import Operation, ProductionLine, ProductionMember

TAB = Column("tab_number", "Nr. tabel", example="12", aliases=("numarul de tabel", "табельный номер", "tab"))
JOB = Column("employment", "Raportul de muncă", example="", aliases=("functia", "raport", "должность", "трудовое отношение"))


def _job(context, tab, job_text):
    from apps.staff import services as staff

    report = context["report"]
    jobs = [j for j in Employment.objects.filter(employee__tab_number=tab).select_related("employee", "occupation")
            if j.is_active_on(report.date)]
    if not jobs:
        raise RowError(f"Nr. de tabel {tab}: nu are raport de muncă activ la {report.date:%d.%m.%Y}.")
    if not staff.can_see(jobs[0].employee, context["user"], "production"):
        raise RowError(f"Nr. de tabel {tab}: angajatul nu este în subdiviziunile dvs.")
    if job_text:
        want = _norm(job_text)
        found = [j for j in jobs if want in (str(j.pk), _norm(j.occupation.name_ro), _norm(j.get_kind_display()), _norm(j.kind))]
        if len(found) != 1:
            raise RowError(f"Raportul de muncă „{job_text}” nu se găsește (sau nu e unic) pentru nr. de tabel {tab}.")
        return found[0]
    if len(jobs) > 1:
        raise RowError(f"Nr. de tabel {tab} are {len(jobs)} raporturi de muncă; completați „Raportul de muncă”.")
    return jobs[0]


def _num(values, key, title):
    v = values.get(key)
    if v is None:
        return Decimal("0")
    if v < 0:
        raise RowError(f"„{title}” nu poate fi negativ.")
    return v


def save_line(values, context):
    report = context["report"]
    code = str(values.get("operation") or "").strip().upper()
    op = Operation.objects.filter(code=code, is_active=True, deletion_mark=False).first()
    if op is None:
        raise RowError(f"Lucrarea „{code}” nu există sau nu este activă.")
    tab = str(values.get("tab_number") or "").strip()
    job = None
    if report.kind == "individual":
        if not tab:
            raise RowError("La raportul individual „Nr. tabel” este obligatoriu.")
        job = _job(context, tab, str(values.get("employment") or "").strip())
    elif tab:
        raise RowError("La raportul pe brigadă lucrările nu au angajat (lăsați „Nr. tabel” gol; membrii — în importul membrilor).")
    line = ProductionLine(report=report, employment=job, operation=op,
                          quantity=_num(values, "quantity", "Cantitatea bună"),
                          defect_nofault=_num(values, "defect_nofault", "Rebut fără vină"),
                          defect_partial=_num(values, "defect_partial", "Rebut parțial"),
                          defect_partial_pct=values.get("defect_partial_pct"),
                          defect_worker=_num(values, "defect_worker", "Rebut din vina lucrătorului"),
                          hours=values.get("hours"), note=str(values.get("note") or "")[:300])
    from .services import line_problem

    bad = line_problem(line)
    if bad:
        raise RowError(bad[0].upper() + bad[1:] + ".")
    line.sort = (report.lines.count() + 1) * 10
    line.save()
    who = f"{job.employee.full_name()}: " if job else ""
    return f"{who}{op.code} — {Decimal(line.quantity).normalize()} {op.get_unit_display()}", "created"


def save_member(values, context):
    report = context["report"]
    tab = str(values.get("tab_number") or "").strip()
    if not tab:
        raise RowError("„Nr. tabel” este obligatoriu.")
    job = _job(context, tab, str(values.get("employment") or "").strip())
    hours = values.get("hours")
    if hours is None or hours < 0 or hours > 744:
        raise RowError("Orele sunt între 0 și 744.")
    coef = values.get("coefficient")
    if coef is None:
        bm = report.brigade.members.filter(employment=job).order_by("-date_from").first() if report.brigade_id else None
        coef = bm.coefficient if bm else Decimal("1")
    if coef < 0 or coef > 10:
        raise RowError("Coeficientul de participare este între 0 și 10.")
    m = report.members.filter(employment=job).first()
    status = "updated" if m else "created"
    if m is None:
        m = ProductionMember(report=report, employment=job, sort=(report.members.count() + 1) * 10)
    m.hours, m.coefficient = hours, coef
    m.save()
    return f"{job.employee.full_name()}: {Decimal(hours).normalize()} ore, coeficientul {Decimal(coef).normalize()}", status


def lines_spec() -> Spec:
    return Spec(
        code="production_lines", title="Lucrările în raportul de producție", sheet_title="Lucrări", save_row=save_line,
        columns=[
            TAB, JOB,
            Column("operation", "Lucrarea (codul)", required=True, example="OP-01", aliases=("lucrarea", "cod", "операция", "работа")),
            Column("quantity", "Cantitatea bună", kind="decimal", example=120, aliases=("cantitatea", "cantitate", "количество", "годные")),
            Column("defect_nofault", "Rebut fără vina lucrătorului", kind="decimal", example=0, aliases=("брак не по вине",)),
            Column("defect_partial", "Rebut parțial din vina lucrătorului", kind="decimal", example=0, aliases=("частичный брак",)),
            Column("defect_partial_pct", "Plata rebutului parțial (%)", kind="decimal", example="",
                   aliases=("procentul rebutului", "оплата частичного брака")),
            Column("defect_worker", "Rebut total din vina lucrătorului", kind="decimal", example=0, aliases=("брак по вине",)),
            Column("hours", "Ore lucrate", kind="decimal", example=8, aliases=("ore", "часы")),
            Column("note", "Observații", example="", aliases=("примечание",)),
        ],
        notes=["La raportul individual fiecare rând are „Nr. tabel”; la raportul pe brigadă „Nr. tabel” rămâne gol (membrii brigăzii "
               "se importă separat).",
               "„Raportul de muncă” — doar pentru angajații cu mai multe raporturi: funcția, felul (de ex. „Cumul intern”) sau numărul "
               "raportului.",
               "Rebutul parțial cere procentul de plată din contractul colectiv (CM art. 162).",
               "Codurile lucrărilor: Setări → Lucrările în acord. Rândurile se adaugă la cele din raport."])


def members_spec() -> Spec:
    return Spec(
        code="production_members", title="Membrii brigăzii în raportul de producție", sheet_title="Membri", save_row=save_member,
        columns=[
            Column("tab_number", "Nr. tabel", required=True, example="12", aliases=("numarul de tabel", "табельный номер", "tab")),
            JOB,
            Column("hours", "Ore lucrate", required=True, kind="decimal", example=160, aliases=("ore", "часы")),
            Column("coefficient", "Coeficientul de participare (KTU)", kind="decimal", example=1,
                   aliases=("coeficientul", "ktu", "кту", "коэффициент")),
        ],
        notes=["Coeficientul gol — cel din componența brigăzii (sau 1).",
               "Membrul care e deja în raport primește orele și coeficientul din fișier."])
