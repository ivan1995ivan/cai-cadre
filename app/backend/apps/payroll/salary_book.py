"""Cartea privind salariul („Fișa de evidență a retribuției”, ca raportul „Книга по ЗП” din POLARIS / 1C Contabilitate):
pe angajat — nr. de tabel, numele, funcția, salariul, anul angajării, datoria la începutul perioadei, apoi câte o coloană
pentru fiecare acumulare și fiecare reținere folosită în perioadă, totalurile și suma de plată. Pe mai multe luni —
rândul fiecărei luni sub angajat. Acumulările, reținerile și CAS — din calculele aprobate; CNAM și impozitul pe venit — din
îndreptările spre plată ale lunii (aprobate sau achitate), unde se rețin. Semnează contabilul-șef și conducătorul.
Lunile în regimul IT Park: salariul din CIM e impozitat final — coloanele de impozit apar doar dacă s-a reținut ceva (de ex.
la contractele de prestări servicii), iar rezumatul arată lunile din regim."""
from collections import defaultdict
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.reports.registry import GROUPS, col, report, subtitle_parts
from apps.staff.models import MAIN_KINDS

ZERO = Decimal("0")
GROUPS.setdefault("payroll", ("Salarizare", "Зарплата", "Payroll"))
MONTHS = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie",
          "noiembrie", "decembrie"]


def _months(p):
    y, m = p.date_from.year, p.date_from.month
    out = []
    while (y, m) <= (p.date_to.year, p.date_to.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


@report("salary_book", "payroll", ("Cartea privind salariul", "Книга по зарплате", "Payroll book"),
        ("Fișa de evidență a retribuției: pe angajat — fiecare acumulare și reținere din calculele aprobate, CNAM și impozitul "
         "reținute la plată, totalurile și suma de plată; pe mai multe luni — și rândul fiecărei luni.",
         "Карточка учёта заработной платы: по сотруднику — каждое начисление и удержание, итоги и сумма к выплате.",
         "Per employee: every accrual and deduction from the approved payrolls, totals and net pay."),
        ["period", "subdivision"], perm="payroll.view")
def salary_book(p):
    from apps.core import license
    from apps.core.models import Company

    from .models import PaymentLine, PayrollItem, PayType
    from .payments import debts

    if not license.module_enabled("payroll"):
        raise ValidationError({"detail": "Întreprinderea lucrează fără modulul de salarizare."})
    months = _months(p)
    keys = {y * 100 + m for y, m in months}
    items = (PayrollItem.objects.filter(line__payroll__status="approved", line__payroll__year__gte=months[0][0],
                                        line__payroll__year__lte=months[-1][0])
             .select_related("pay_type", "line__payroll", "line__employee", "line__employment__occupation"))
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: ZERO)))  # angajat → luna → cod → suma
    used = {}
    people, jobs = {}, {}
    for it in items:
        ln = it.line
        if ln.payroll.year * 100 + ln.payroll.month not in keys or not p.allowed(ln.employment.subdivision_id):
            continue
        t = it.pay_type
        if t.category not in ("accrual", "deduction", "employer"):
            continue
        used[t.code] = t
        data[ln.employee_id][(ln.payroll.year, ln.payroll.month)][t.code] += it.amount
        people[ln.employee_id] = ln.employee
        if ln.employee_id not in jobs or ln.employment.kind in MAIN_KINDS:
            jobs[ln.employee_id] = ln.employment
    # CNAM și impozitul pe venit: reținute la plată, pe luna pentru care s-a plătit
    taxes = {t.auto: t for t in PayType.objects.filter(auto__in=("cnam", "income_tax")).order_by("id")}
    for pl in PaymentLine.objects.filter(employee_id__in=list(people), payment__status__in=("approved", "paid"),
                                         payment__deletion_mark=False, payment__year__gte=months[0][0],
                                         payment__year__lte=months[-1][0]).select_related("payment"):
        if pl.payment.year * 100 + pl.payment.month not in keys:
            continue
        for field, auto in (("cnam", "cnam"), ("income_tax", "income_tax")):
            t = taxes.get(auto)
            if t is not None and getattr(pl, field):
                used[t.code] = t
                data[pl.employee_id][(pl.payment.year, pl.payment.month)][t.code] += getattr(pl, field)
    order = sorted(used.values(), key=lambda t: (t.sort, t.code))
    acc = [t for t in order if t.category == "accrual"]
    ded = [t for t in order if t.category == "deduction"]
    emp_cols = [t for t in order if t.category == "employer"]
    name = lambda t: t.name_ru if p.lang == "ru" and getattr(t, "name_ru", "") else t.name_ro  # noqa: E731
    columns = [col("tab", p.t(("Nr. tabel", "Таб. №", "No."))), col("name", p.t(("Numele, prenumele", "ФИО", "Name"))),
               col("occupation", p.t(("Funcția", "Должность", "Position"))), col("salary", p.t(("Salariul", "Оклад", "Salary")), "num"),
               col("hired", p.t(("Anul angajării", "Год приёма", "Hired")), "int"),
               col("opening", p.t(("Sold la început (înainte de impozit)", "Остаток на начало (до налога)", "Opening balance (before tax)")), "num")]
    columns += [col(f"a_{t.code}", name(t), "num") for t in acc]
    columns.append(col("gross", p.t(("Total calculat", "Итого начислено", "Total accrued")), "num"))
    columns += [col(f"d_{t.code}", name(t), "num") for t in ded]
    columns.append(col("withheld", p.t(("Total reținut", "Итого удержано", "Total withheld")), "num"))
    columns.append(col("net", p.t(("De plată", "К выплате", "Net pay")), "num"))
    columns += [col(f"e_{t.code}", name(t) + p.t((" (angajator)", " (работодатель)", " (employer)")), "num") for t in emp_cols]

    prev = (months[0][0] - 1, 12) if months[0][1] == 1 else (months[0][0], months[0][1] - 1)
    opening = {r["employee"]: r["debt"] for r in debts(*prev, employee_ids=list(people))}

    def amounts(by_code) -> dict:
        row = {f"a_{t.code}": float(by_code.get(t.code, ZERO)) for t in acc}
        row |= {f"d_{t.code}": float(by_code.get(t.code, ZERO)) for t in ded}
        row |= {f"e_{t.code}": float(by_code.get(t.code, ZERO)) for t in emp_cols}
        gross = sum((by_code.get(t.code, ZERO) for t in acc), ZERO)
        withheld = sum((by_code.get(t.code, ZERO) for t in ded), ZERO)
        return row | {"gross": float(gross), "withheld": float(withheld), "net": float(gross - withheld)}

    rows = []
    total = defaultdict(float)
    for emp_id, e in sorted(people.items(), key=lambda x: (x[1].last_name, x[1].first_name)):
        job = jobs[emp_id]
        head = {"tab": e.tab_number, "name": e.full_name(), "occupation": job.occupation.name_ro if job.occupation_id else "",
                "salary": float(job.base_salary), "hired": job.date_from.year, "opening": opening.get(emp_id, 0.0)}
        summed = defaultdict(lambda: ZERO)
        for by_code in data[emp_id].values():
            for code, v in by_code.items():
                summed[code] += v
        full = amounts(summed)
        if len(months) > 1:
            rows.append({"_section": f"{e.full_name()} · {e.tab_number}"})
            for (y, m) in months:
                if (y, m) in data[emp_id]:
                    rows.append({"name": f"{MONTHS[m]} {y}", **amounts(data[emp_id][(y, m)])})
            rows.append({**head, **full, "_subtotal": True})
        else:
            rows.append({**head, **full})
        for k, v in full.items():
            total[k] += v
        total["opening"] += head["opening"]
    company = Company.get()
    from datetime import date

    from . import it_park

    it_months = sorted(it_park.it_park_months(date(*months[0], 1), date(*months[-1], 1)))
    summary = [{"label": p.t(("Angajați", "Сотрудников", "Employees")), "value": len(people)}]
    if it_months:
        summary.append({"label": p.t(("Regimul IT Park", "Режим IT-парка", "IT Park regime")),
                        "value": ", ".join(f"{m:02d}.{y}" for y, m in it_months) + p.t((
                            " — impozitat final, impozit unic IT Park (CF art. 377): CNAM și impozitul pe venit nu se rețin din salariul CIM",
                            " — окончательно обложено единым налогом IT-парка (НК, ст. 377): CNAM и подоходный налог с зарплаты по ИТД не удерживаются",
                            " — final taxation, IT Park single tax (Tax Code art. 377): no income tax or health insurance withheld from employment salary"))})
    return {
        "title": p.t(("FIȘA DE EVIDENȚĂ A RETRIBUȚIEI (cartea privind salariul)", "КНИГА ПО ЗАРПЛАТЕ", "PAYROLL BOOK")),
        "subtitle": subtitle_parts(p, f"{company.name_ro}, cod fiscal {company.idno}" if company.idno else company.name_ro,
                                   p.t(("pe perioada ", "за период ", "period ")) + p.period_text()),
        "columns": columns, "rows": rows, "totals": dict(total) if rows else None,
        "summary": summary,
        "signatures": [{"label": p.t(("Contabil-șef", "Главный бухгалтер", "Chief accountant")), "name": company.chief_accountant},
                       {"label": p.t(("Conducătorul", "Руководитель", "Head")), "name": company.director}],
    }
