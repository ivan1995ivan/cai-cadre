"""Fișa decontărilor cu angajatul (raportul „employee_settlement”): soldul salarial la începutul perioadei, fiecare document
din perioadă — calculul salariului (de plătit: brutul minus celelalte rețineri) și plata (achitat: brutul plătit minus
reținerile făcute la plată), soldul după fiecare, soldul de la sfârșit și concluzia în cuvinte.

Aceeași bază ca soldul din îndreptările spre plată (apps.payroll.payments.debts): înainte de impozitul pe venit și CNAM, care se
rețin din el la plată. Datele: calculul — ultima zi a lunii lui; plata — data achitării (altfel data documentului); datoriile
salariale iau plata pe luna pentru care s-a plătit, fișa — în ziua în care s-a plătit, deci la o dată din mijlocul lunii soldurile
pot diferi, iar după plată se închid la fel. Doar calculele aprobate și plățile achitate, nemarcate pentru ștergere."""
from datetime import date
from decimal import Decimal

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from .registry import GROUPS, col, report

GROUPS.setdefault("payroll", ("Salarizarea", "Зарплата", "Payroll"))
ZERO = Decimal("0")


def _end(year, month) -> date:
    """Ultima zi a lunii."""
    return date.fromordinal(date(year + (month == 12), month % 12 + 1, 1).toordinal() - 1)


def _money(v) -> str:
    return f"{Decimal(v):,.2f}".replace(",", " ").replace(".", ",")


def documents(employee_id):
    """[(data, felul, documentul, de plătit, achitat, detaliile, legătura)] — toate, în ordinea datelor."""
    from apps.payroll.models import PaymentLine, PayrollLine

    out = []
    per_payroll = {}
    for ln in PayrollLine.objects.filter(employee_id=employee_id, payroll__status="approved", payroll__deletion_mark=False) \
            .select_related("payroll"):
        p = ln.payroll
        row = per_payroll.setdefault(p.pk, {"p": p, "gross": ZERO, "deductions": ZERO})
        row["gross"] += ln.gross
        row["deductions"] += ln.deductions
    for row in per_payroll.values():
        p = row["p"]
        out.append((_end(p.year, p.month), "payroll", f"Calculul salariului nr. {p.number or '—'} pe {p.month:02d}.{p.year}",
                    row["gross"] - row["deductions"], ZERO,
                    f"calculat {_money(row['gross'])}, rețineri {_money(row['deductions'])}", f"/payroll/{p.pk}"))
    for pl in PaymentLine.objects.filter(Q(employee_id=employee_id), payment__status="paid", payment__deletion_mark=False) \
            .select_related("payment"):
        pay = pl.payment
        out.append((pay.paid_on or pay.date, "payment",
                    f"{pay.get_kind_display()} nr. {pay.number or '—'} pe {pay.month:02d}.{pay.year}", ZERO, pl.gross - pl.deductions,
                    f"net {_money(pl.amount)}, impozit {_money(pl.income_tax)}, CNAM {_money(pl.cnam)}", f"/payroll/payments/{pay.pk}"))
    out.sort(key=lambda x: (x[0], 0 if x[1] == "payroll" else 1, x[2]))
    return out


@report("employee_settlement", "payroll",
        ("Fișa decontărilor cu angajatul", "Карточка расчётов с сотрудником", "Employee settlement statement"),
        ("Soldul salarial la începutul perioadei, calculele aprobate și plățile achitate din perioadă cu soldul după fiecare, soldul "
         "de la sfârșit și concluzia. Sumele sunt înainte de impozitul pe venit și CNAM (se rețin la plată). Dublu clic — documentul.",
         "Сальдо по зарплате на начало периода, утверждённые расчёты и выплаты за период с сальдо после каждого, сальдо на конец "
         "и вывод. Суммы до подоходного налога и CNAM (удерживаются при выплате). Двойной щелчок — документ.",
         "The salary balance at the start, the approved payrolls and payments of the period with the balance after each, the "
         "closing balance and a conclusion. Amounts are before income tax and CNAM (withheld on payment). Double-click opens it."),
        ["employee", "period"], perm="payroll.view")
def employee_settlement(p):
    from apps.staff.models import Employee

    if not p.employee:
        raise ValidationError({"employee": "Alegeți angajatul."})
    emp = Employee.objects.get(pk=p.employee)
    docs = documents(emp.pk)
    opening = sum((owed - paid for day, _k, _doc, owed, paid, _det, _l in docs if day < p.date_from), ZERO)
    rows = [{"date": None, "doc": p.t(("Soldul la începutul perioadei", "Сальдо на начало периода", "Opening balance")),
             "owed": None, "paid": None, "balance": float(opening), "detail": "", "_subtotal": True}]
    balance, owed_sum, paid_sum = opening, ZERO, ZERO
    for day, _kind, doc, owed, paid, detail, link in docs:
        if not (p.date_from <= day <= p.date_to):
            continue
        balance += owed - paid
        owed_sum += owed
        paid_sum += paid
        rows.append({"date": day.isoformat(), "doc": doc, "owed": float(owed) or None, "paid": float(paid) or None,
                     "balance": float(balance), "detail": detail, "_link": link})
    name = emp.full_name()
    end = f"{p.date_to:%d.%m.%Y}"
    if balance > 0:
        conclusion = p.t((f"La {end} întreprinderea datorează lui {name} {_money(balance)} lei (înainte de impozitul pe venit și "
                          f"CNAM, care se rețin la plată).",
                          f"На {end} предприятие должно {name} {_money(balance)} лей (до подоходного налога и CNAM, которые "
                          f"удерживаются при выплате).",
                          f"On {end} the company owes {name} {_money(balance)} lei (before income tax and CNAM, withheld on payment)."))
    elif balance < 0:
        conclusion = p.t((f"La {end} {name} a primit cu {_money(-balance)} lei mai mult decât i s-a calculat (avans neacoperit "
                          f"încă de calcul).",
                          f"На {end} {name} получил(а) на {_money(-balance)} лей больше начисленного (аванс, ещё не покрытый "
                          f"расчётом).",
                          f"On {end} {name} has received {_money(-balance)} lei more than calculated (an advance not yet covered)."))
    else:
        conclusion = p.t((f"La {end} decontările cu {name} sunt închise.", f"На {end} расчёты с {name} закрыты.",
                          f"On {end} the settlements with {name} are closed."))
    return {
        "title": p.t(("Fișa decontărilor cu angajatul", "Карточка расчётов с сотрудником", "Employee settlement statement")),
        "subtitle": f"{name} ({emp.tab_number}) · {p.period_text()}",
        "columns": [col("date", p.t(("Data", "Дата", "Date")), "date"), col("doc", p.t(("Documentul", "Документ", "Document"))),
                    col("owed", p.t(("De plătit", "Начислено к выплате", "Owed")), "num"),
                    col("paid", p.t(("Achitat", "Выплачено", "Paid")), "num"),
                    col("balance", p.t(("Soldul", "Сальдо", "Balance")), "num"),
                    col("detail", p.t(("Detalii", "Подробности", "Details")))],
        "rows": rows,
        "totals": {"doc": p.t(("Rulajul perioadei și soldul final", "Обороты за период и конечное сальдо",
                               "Turnover and closing balance")), "owed": float(owed_sum), "paid": float(paid_sum),
                   "balance": float(balance)},
        "summary": [{"label": p.t(("Sold inițial", "Начальное сальдо", "Opening")), "value": float(opening)},
                    {"label": p.t(("De plătit în perioadă", "Начислено за период", "Owed in the period")), "value": float(owed_sum)},
                    {"label": p.t(("Achitat în perioadă", "Выплачено за период", "Paid in the period")), "value": float(paid_sum)},
                    {"label": p.t(("Sold final", "Конечное сальдо", "Closing")), "value": float(balance)}],
        "conclusion": conclusion,
    }
