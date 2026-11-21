"""Rapoartele despre concedii, timpul de muncă și ordine, plus indicatorii pentru BNS (Munca 1)."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum

from apps.leave.models import ABSENCE_KINDS, Absence
from apps.orders.models import Order, OrderItem

from apps.staff.models import Employment

from .personnel import COMMON, MAIN_KINDS, Lookup, _d, _occupancy, jobs_on, load_jobs, snapshot
from .registry import col, report, subtitle_parts

ABSENCE_T = {
    "annual": ("Concediu de odihnă anual", "Ежегодный отпуск", "Annual leave"),
    "extra": ("Concediu suplimentar plătit", "Дополнительный оплачиваемый отпуск", "Extra paid leave"),
    "unpaid": ("Concediu neplătit", "Отпуск без сохранения", "Unpaid leave"),
    "maternity": ("Concediu de maternitate", "Отпуск по беременности и родам", "Maternity leave"),
    "paternity": ("Concediu paternal", "Отцовский отпуск", "Paternity leave"),
    "childcare": ("Îngrijirea copilului (plătit parțial)", "Уход за ребёнком (частично оплачиваемый)", "Childcare (partly paid)"),
    "childcare_unpaid": ("Îngrijirea copilului (neplătit)", "Уход за ребёнком (неоплачиваемый)", "Childcare (unpaid)"),
    "study": ("Concediu de studii", "Учебный отпуск", "Study leave"),
    "days_off": ("Zile libere plătite", "Оплачиваемые выходные дни", "Paid days off"),
    "travel": ("Deplasare în interes de serviciu", "Командировка", "Business trip"),
    "training": ("Perfecționare / EMC", "Повышение квалификации", "Training"),
    "sick": ("Concediu medical", "Больничный", "Sick leave"),
}
CHILDCARE = ("maternity", "childcare", "childcare_unpaid")


def _overlap(a_from, a_to, b_from, b_to) -> int:
    lo, hi = max(a_from, b_from), min(a_to, b_to)
    return (hi - lo).days + 1 if hi >= lo else 0


# --- concediile pe perioadă -------------------------------------------------------------------------------------------------
@report("leave_period", "time", ("Concediile și absențele pe perioadă", "Отпуска и отсутствия за период", "Leave and absences by period"),
        ("Cine a fost în concediu, deplasare sau pe foaie de boală în perioadă: tipul, datele, zilele din perioadă; totalul pe tipuri.",
         "Кто был в отпуске, командировке или на больничном в периоде: вид, даты, дни в периоде; итоги по видам.",
         "Who was on leave, a trip or sick leave in the period: type, dates, days in the period; totals by type."),
        ["period", "subdivision", "category", "absence_kind"], perm="reports.view")
def leave_period(p):
    look = Lookup(p.lang)
    qs = (Absence.objects.filter(date_from__lte=p.date_to, date_to__gte=p.date_from)
          .select_related("employee", "employment").prefetch_related("employment__history", "employee__employments__history"))
    if p.absence_kind:
        qs = qs.filter(kind=p.absence_kind)
    rows, by_kind = [], Counter()
    for a in qs.order_by("date_from", "employee__last_name"):
        job = a.employment or next((e for e in a.employee.employments.all() if e.kind in MAIN_KINDS), None) \
            or next(iter(a.employee.employments.all()), None)
        if job is None:
            continue
        snap = snapshot(job, max(a.date_from, p.date_from))
        if not p.allowed(snap["subdivision_id"]) or not look.in_category(snap["occupation_id"], p.category):
            continue
        inside = _overlap(a.date_from, a.date_to, p.date_from, p.date_to)
        by_kind[a.kind] += inside
        rows.append({"tab": a.employee.tab_number, "name": a.employee.full_name(), "sub": look.sub(snap["subdivision_id"]),
                     "occ": look.occ(snap["occupation_id"]), "kind": p.t(ABSENCE_T.get(a.kind, (a.kind,))), "date_from": _d(a.date_from),
                     "date_to": _d(a.date_to), "days": a.days, "inside": inside})
    return {
        "subtitle": subtitle_parts(p, p.period_text(), p.t(ABSENCE_T[p.absence_kind]) if p.absence_kind in ABSENCE_T else ""),
        "columns": [col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("sub", p.t(COMMON["sub"])),
                    col("occ", p.t(COMMON["occ"])), col("kind", p.t(COMMON["kind"])),
                    col("date_from", p.t(("De la", "С", "From")), "date"), col("date_to", p.t(("Până la", "По", "To")), "date"),
                    col("days", p.t(("Zile", "Дней", "Days")), "int"), col("inside", p.t(("Zile în perioadă", "Дней в периоде", "Days in period")), "int")],
        "rows": rows,
        "totals": {"tab": p.t(COMMON["total"]), "inside": sum(by_kind.values())},
        "summary": [{"label": p.t(ABSENCE_T[k]), "value": by_kind[k]} for k, _ in ABSENCE_KINDS if by_kind[k]],
    }


# --- pontajul consolidat ----------------------------------------------------------------------------------------------------
@report("timesheet_summary", "time", ("Pontajul consolidat", "Сводный табель", "Consolidated timesheet"),
        ("Totalurile tabelelor lunii pe subdiviziuni: zile și ore lucrate, noaptea, sărbătorile, suplimentarele, absențele pe coduri.",
         "Итоги табелей месяца по подразделениям: дни и часы, ночные, праздничные, сверхурочные, неявки по кодам.",
         "Monthly timesheet totals by department: days and hours worked, night, holidays, overtime, absences by code."),
        ["month", "subdivision"], perm="reports.view")
def timesheet_summary(p):
    from apps.worktime.models import Timesheet

    look = Lookup(p.lang)
    nums = ("days", "hours", "night", "holiday", "overtime", "missing")
    rows, totals, all_codes = [], defaultdict(Decimal), Counter()
    sheets = Timesheet.objects.filter(year=p.year, month=p.month, deletion_mark=False).prefetch_related("lines")
    for ts in sorted(sheets, key=lambda t: (look.subs[t.subdivision_id].sort, look.sub(t.subdivision_id))):
        if not p.allowed(ts.subdivision_id):
            continue
        sums, codes = defaultdict(Decimal), Counter()
        lines = list(ts.lines.all())
        for ln in lines:
            t = ln.totals or {}
            for k in nums:
                sums[k] += Decimal(str(t.get(k) or 0))
            codes.update(t.get("codes") or {})
        all_codes.update(codes)
        for k in nums:
            totals[k] += sums[k]
        totals["people"] += len(lines)
        rows.append({"sub": look.sub(ts.subdivision_id), "status": ts.get_status_display(), "people": len(lines),
                     **{k: float(sums[k]) for k in nums}, "codes": ", ".join(f"{c}: {n}" for c, n in sorted(codes.items()))})
    return {
        "subtitle": subtitle_parts(p, p.month_name()),
        "columns": [col("sub", p.t(COMMON["sub"])), col("status", p.t(("Starea", "Статус", "Status"))),
                    col("people", p.t(("Rânduri", "Строк", "Rows")), "int"), col("days", p.t(("Zile lucrate", "Отработано дней", "Days worked")), "num"),
                    col("hours", p.t(("Ore lucrate", "Отработано часов", "Hours worked")), "num"),
                    col("night", p.t(("Ore de noapte", "Ночные часы", "Night hours")), "num"),
                    col("holiday", p.t(("Ore de sărbătoare", "Праздничные часы", "Holiday hours")), "num"),
                    col("overtime", p.t(("Peste normă", "Сверх нормы", "Overtime")), "num"),
                    col("missing", p.t(("Sub normă", "Недоработка", "Under norm")), "num"),
                    col("codes", p.t(("Absențe (zile pe coduri)", "Неявки (дни по кодам)", "Absences (days by code)")))],
        "rows": rows,
        "totals": {"sub": p.t(COMMON["total"]), "people": int(totals["people"]), **{k: float(totals[k]) for k in nums},
                   "codes": ", ".join(f"{c}: {n}" for c, n in sorted(all_codes.items()))},
    }


# --- ordinele -----------------------------------------------------------------------------------------------------------------
def _signed(p):
    return Order.objects.filter(status="signed", date__range=(p.date_from, p.date_to))


def _visible_item(item, p):
    if p.sub_ids is None:
        return True
    job = item.employment
    if job is None and item.employee_id:
        job = next(iter(item.employee.employments.all()), None)
    return job is not None and p.allowed(snapshot(job, item.order.date)["subdivision_id"])


@report("orders_payroll", "orders", ("Extrasul din ordine pentru contabilitate", "Выписка из приказов для бухгалтерии",
                                     "Order extract for accounting"),
        ("Ordinele semnate în perioadă care schimbă salariul (angajări, transferuri, sporuri, premii, concedii, eliberări), "
         "cu textul punctului.",
         "Подписанные за период приказы, влияющие на зарплату, с текстом пункта.",
         "Signed orders in the period that affect pay, with the item text."),
        ["period", "subdivision"])
def orders_payroll(p):
    items = (OrderItem.objects.filter(order__in=_signed(p).filter(order_type__payroll_effect=True))
             .select_related("order__order_type", "employee", "employment").prefetch_related("employment__history", "employee__employments__history")
             .order_by("order__date", "order__seq", "sort", "id"))
    rows = []
    for it in items:
        if not _visible_item(it, p):
            continue
        rows.append({"number": it.order.number, "date": _d(it.order.date), "type": it.order.order_type.local_name(p.lang),
                     "tab": it.employee.tab_number if it.employee_id else "", "name": it.employee.full_name() if it.employee_id else "",
                     "text": it.text})
    return {
        "subtitle": subtitle_parts(p, p.period_text()),
        "columns": [col("number", p.t(("Nr. ordinului", "№ приказа", "Order no."))), col("date", p.t(COMMON["date"]), "date"),
                    col("type", p.t(("Tipul ordinului", "Вид приказа", "Order type"))), col("tab", p.t(COMMON["tab"])),
                    col("name", p.t(COMMON["name"])), col("text", p.t(("Conținutul", "Содержание", "Content")))],
        "rows": rows,
    }


@report("orders_by_type", "orders", ("Ordinele pe tipuri", "Приказы по видам", "Orders by type"),
        ("Câte ordine semnate și câte puncte (persoane) sunt pe fiecare tip în perioadă.",
         "Сколько подписанных приказов и пунктов (лиц) по каждому виду за период.",
         "Signed orders and items (persons) per type in the period."),
        ["period"])
def orders_by_type(p):
    qs = (_signed(p).values("order_type__name_ro", "order_type__name_ru", "order_type__name_en", "order_type__group")
          .annotate(orders=Count("id", distinct=True), items=Count("items")).order_by("order_type__group", "order_type__name_ro"))
    rows = []
    for r in qs:
        name = {"ru": r["order_type__name_ru"], "en": r["order_type__name_en"]}.get(p.lang) or r["order_type__name_ro"]
        rows.append({"group": r["order_type__group"], "type": name, "orders": r["orders"], "items": r["items"]})
    return {
        "subtitle": p.period_text(),
        "columns": [col("group", p.t(("Grupa", "Группа", "Group"))), col("type", p.t(("Tipul ordinului", "Вид приказа", "Order type"))),
                    col("orders", p.t(("Ordine", "Приказов", "Orders")), "int"), col("items", p.t(("Puncte", "Пунктов", "Items")), "int")],
        "rows": rows,
        "totals": {"type": p.t(COMMON["total"]), "orders": sum(r["orders"] for r in rows), "items": sum(r["items"] for r in rows)},
    }


# --- Munca 1 (BNS) ---------------------------------------------------------------------------------------------------------------
@report("munca1", "external", ("Munca 1 — indicatorii lunii (BNS)", "Труд 1 — показатели месяца (НБС)", "Labour 1 — monthly indicators (NBS)"),
        ("Efectivul la sfârșitul lunii, numărul mediu scriptic (fără concediile de maternitate și îngrijire a copilului), cumularzii "
         "externi, angajările și eliberările, posturile vacante, fondul de salarizare și orele lucrate — cifrele pentru formularul "
         "statistic.",
         "Численность на конец месяца, среднесписочная (без отпусков по беременности и уходу за ребёнком), внешние совместители, "
         "приём и увольнение, вакансии, фонд оплаты труда и отработанные часы — данные для статистической формы.",
         "Headcount at month end, average headcount, external part-timers, hires and exits, vacancies, payroll fund and hours worked."),
        ["month", "subdivision"])
def munca1(p):
    import calendar

    look = Lookup(p.lang)
    first = date(p.year, p.month, 1)
    last = date(p.year, p.month, calendar.monthrange(p.year, p.month)[1])
    p.kinds = "main"
    end_jobs = jobs_on(p, last, look)
    end_people = {e.employee_id for e, _ in end_jobs}
    women = sum(1 for e, _ in end_jobs if e.employee.sex == "F")
    away = defaultdict(set)
    for a in Absence.objects.filter(kind__in=CHILDCARE, date_from__lte=last, date_to__gte=first):
        d = max(a.date_from, first)
        while d <= min(a.date_to, last):
            away[d].add(a.employee_id)
            d += timedelta(days=1)
    month_jobs = load_jobs(p, first, last)
    daily, d = [], first
    while d <= last:
        daily.append(len({e.employee_id for e, _ in jobs_on(p, d, look, preloaded=month_jobs)} - away[d]))
        d += timedelta(days=1)
    average = round(sum(daily) / len(daily), 1) if daily else 0
    external = {e.employee_id for e, _ in jobs_on(p, last, look, kinds="all") if e.kind == "external"}
    def count(field):
        n = 0
        for e in Employment.objects.filter(kind__in=MAIN_KINDS, **{f"{field}__range": (first, last)}).prefetch_related("history"):
            if p.allowed(snapshot(e, getattr(e, field))["subdivision_id"]):
                n += 1
        return n

    saved = p.on_date
    p.on_date = last
    vacant = sum((max(Decimal(r["vacant"]), Decimal("0")) for r in _occupancy(p)), Decimal("0"))
    p.on_date = saved
    from apps.worktime.models import TimesheetLine

    hours = overtime = Decimal("0")
    for ln in TimesheetLine.objects.filter(timesheet__year=p.year, timesheet__month=p.month, employment__kind__in=MAIN_KINDS) \
            .select_related("timesheet"):
        if p.allowed(ln.timesheet.subdivision_id):
            hours += Decimal(str((ln.totals or {}).get("hours") or 0))
            overtime += Decimal(str((ln.totals or {}).get("overtime") or 0))
    fund = None
    if p.user.has_crm_perm("payroll.view"):
        from apps.payroll.models import PayrollLine

        lines = PayrollLine.objects.filter(payroll__year=p.year, payroll__month=p.month, payroll__status="approved")
        if p.sub_ids is not None:
            lines = lines.filter(Q(employment__subdivision_id__in=p.sub_ids))
        fund = float(lines.aggregate(s=Sum("gross"))["s"] or 0)
    t = p.t
    rows = [
        {"code": "1", "label": t(("Efectivul salariaților la sfârșitul lunii (persoane)", "Списочная численность на конец месяца",
                                  "Headcount at month end")), "value": len(end_people)},
        {"code": "1.1", "label": t(("din care femei", "из них женщин", "of which women")), "value": women},
        {"code": "2", "label": t(("Numărul mediu scriptic al salariaților", "Среднесписочная численность", "Average headcount")), "value": average},
        {"code": "3", "label": t(("Cumularzi externi la sfârșitul lunii", "Внешние совместители на конец месяца",
                                  "External part-timers at month end")), "value": len(external)},
        {"code": "4", "label": t(("Angajați în lună", "Принято за месяц", "Hired in the month")), "value": count("date_from")},
        {"code": "5", "label": t(("Eliberați în lună", "Уволено за месяц", "Left in the month")), "value": count("end_date")},
        {"code": "6", "label": t(("Unități vacante la sfârșitul lunii", "Вакантные единицы на конец месяца",
                                  "Vacant units at month end")), "value": float(vacant)},
        {"code": "7", "label": t(("Ore lucrate (din pontaj)", "Отработано часов (по табелю)", "Hours worked (timesheets)")), "value": float(hours)},
        {"code": "7.1", "label": t(("din care peste normă", "из них сверх нормы", "of which overtime")), "value": float(overtime)},
    ]
    if fund is not None:
        rows.append({"code": "8", "label": t(("Fondul de salarizare calculat (lei, din calculele aprobate)",
                                              "Начисленный фонд оплаты труда (лей, по утверждённым расчётам)",
                                              "Payroll fund (MDL, approved payrolls)")), "value": fund})
    return {
        "subtitle": subtitle_parts(p, p.month_name()),
        "columns": [col("code", t(("Rândul", "Строка", "Row"))), col("label", t(("Indicatorul", "Показатель", "Indicator"))),
                    col("value", t(("Valoarea", "Значение", "Value")), "num")],
        "rows": rows,
    }
