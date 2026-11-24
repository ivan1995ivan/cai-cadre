"""Borderoul tichetelor de masă (Legea 166/2017, HG 227/2018 cu modificările din 22.01.2026).

Tichetele se acordă pentru luna lucrată (de regulă precedenta), la data transferului pe instrumentul de plată:
- o zi lucrată (cu ore în pontaj) = un tichet;
- la munca în schimburi (graficul de lucru pe ture sau graficul de ture al subdiviziunii în luna lucrată) — orele lucrate în
  schimburile de zi ÷ 8 + orele lucrate în schimburile de noapte ÷ 7, rotunjit după regulile matematice (pct. 12); un schimb e
  de noapte când orele lui de noapte (22–06) sunt cel puțin `meal_voucher_night_pct` % din el.
Fiecare persoană primește tichetele pe un singur raport de muncă (cel de bază, altfel primul): ziua lucrată pe două raporturi
nu dă două tichete. Contractul de prestări servicii nu primește tichete.

Valoarea neimpozabilă a tichetului (`meal_voucher_cap`, 70 lei): partea peste ea e facilitate impozabilă (CF art. 19 lit. a¹))
— aprobat, borderoul o pune în calculul salariului lunii datei lui (tipul „meal_voucher”), cu reținerea ei („meal_voucher_offset”),
fiindcă tichetele sunt deja pe card și nu se plătesc a doua oară în bani.
"""
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.staff.models import MAIN_KINDS, Employment

from .models import MealVoucherLine, MealVoucherList, Payroll

ZERO, CENT = Decimal("0"), Decimal("0.01")


def q(value) -> Decimal:
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(value, places=2) -> str:
    v = Decimal(value or 0).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    text = format(v.normalize(), "f") if v != v.to_integral_value() else format(v.to_integral_value(), "f")
    return text.replace(".", ",")


def constants(day):
    from .engine import Constants

    c = Constants(day)
    return {"value": c("meal_voucher_value"), "min": c("meal_voucher_min", "35"), "cap": c("meal_voucher_cap", "70"),
            "night_pct": c("meal_voucher_night_pct", "50")}


def count_for(cells: dict, shifts: bool, night_pct: Decimal) -> dict:
    """Zilele, orele de zi / de noapte și numărul tichetelor din celulele pontajului unui raport de muncă."""
    days, day_h, night_h = 0, ZERO, ZERO
    for cell in cells.values():
        h = Decimal(str(cell.get("h") or 0))
        if h <= 0:
            continue
        days += 1
        n = Decimal(str(cell.get("n") or 0))
        if shifts and n * 100 >= h * night_pct:
            night_h += h
        else:
            day_h += h
    if shifts:
        raw = day_h / 8 + night_h / 7
        count = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        how = f"munca în schimburi: {fmt(day_h)} ore de zi ÷ 8 + {fmt(night_h)} ore de noapte ÷ 7 = {fmt(raw)} → {count}"
    else:
        count = days
        how = f"{days} zile lucrate"
    return {"days": days, "day_hours": day_h, "night_hours": night_h, "count": count, "how": how}


def _cells_by_job(year: int, month: int, job_ids) -> dict:
    """Celulele pontajului lunii pe raport de muncă (un raport în două tabele — zilele unite)."""
    from apps.worktime.models import TimesheetLine

    out = defaultdict(dict)
    for ln in TimesheetLine.objects.filter(timesheet__year=year, timesheet__month=month, timesheet__deletion_mark=False,
                                           employment_id__in=list(job_ids)).only("employment_id", "days"):
        for key, cell in (ln.days or {}).items():
            if Decimal(str(cell.get("h") or 0)) > 0 or key not in out[ln.employment_id]:
                out[ln.employment_id][key] = cell
    return out


def _shift_jobs(year: int, month: int, jobs) -> set:
    """Raporturile care lucrează în schimburi în luna dată: graficul lor de lucru e pe ture (ciclic) sau sunt în graficul de
    ture al subdiviziunii."""
    from apps.worktime.models import RosterLine
    from apps.worktime.services import month_days

    last = month_days(year, month)[-1]
    out = set(RosterLine.objects.filter(roster__year=year, roster__month=month, roster__deletion_mark=False,
                                        employment__in=jobs).values_list("employment_id", flat=True))
    for job in jobs:
        js = next((s for s in sorted(job.work_schedules.all(), key=lambda s: (s.date_from, s.pk), reverse=True)
                   if s.date_from <= last), None)
        if js is not None and js.schedule.kind == "cycle":
            out.add(job.pk)
    return out


def _jobs(doc: MealVoucherList):
    """Un raport de muncă pe persoană (cel de bază, altfel primul), activ în luna lucrată, fără prestări servicii; cu
    subdiviziunea — doar cei din ea (cu sub-subdiviziunile)."""
    from apps.worktime.services import month_days

    days = month_days(doc.year, doc.month)
    qs = (Employment.objects.filter(date_from__lte=days[-1]).exclude(end_date__lt=days[0]).exclude(kind="contractor")
          .select_related("employee", "occupation", "subdivision").prefetch_related("work_schedules__schedule"))
    if doc.subdivision_id:
        qs = qs.filter(subdivision_id__in=doc.subdivision.descendant_ids())
    by_person = {}
    for job in sorted(qs, key=lambda j: (j.kind not in MAIN_KINDS, j.date_from, j.pk)):
        by_person.setdefault(job.employee_id, job)
    return sorted(by_person.values(), key=lambda j: (j.employee.last_name, j.employee.first_name, j.pk))


def price(line: MealVoucherLine, doc: MealVoucherList) -> None:
    line.amount = q(line.count * doc.value)
    line.taxable = q(line.count * max(doc.value - doc.cap, ZERO))


@transaction.atomic
def fill(doc: MealVoucherList, keep_manual: bool = True) -> int:
    """Completează borderoul din pontajul lunii lucrate: rândurile lipsă se adaugă, cele socotite se refac (numărul scris de
    mână rămâne); rândurile celor care n-au mai lucrat în lună se scot. Întoarce câte rânduri are."""
    editable(doc)
    c = constants(doc.date)
    jobs = _jobs(doc)
    cells = _cells_by_job(doc.year, doc.month, [j.pk for j in jobs])
    shifts = _shift_jobs(doc.year, doc.month, jobs)
    existing = {ln.employment_id: ln for ln in MealVoucherLine.objects.filter(voucher_list=doc)}  # nu rândurile preîncărcate
    keep = set()
    for n, job in enumerate(jobs, start=1):
        r = count_for(cells.get(job.pk, {}), job.pk in shifts, c["night_pct"])
        ln = existing.get(job.pk)
        if not r["days"] and not (ln is not None and ln.manual and keep_manual):
            continue
        if ln is None:
            ln = MealVoucherLine(voucher_list=doc, employee=job.employee, employment=job)
        ln.days, ln.day_hours, ln.night_hours, ln.shifts = r["days"], q(r["day_hours"]), q(r["night_hours"]), job.pk in shifts
        if not (ln.manual and keep_manual):
            ln.count, ln.manual = r["count"], False
        ln.note = r["how"][:300]
        ln.sort = n * 10
        price(ln, doc)
        ln.save()
        keep.add(job.pk)
    MealVoucherLine.objects.filter(voucher_list=doc).exclude(employment_id__in=keep).delete()
    return len(keep)


def editable(doc: MealVoucherList):
    from apps.core.deletion import ensure_not_marked

    ensure_not_marked(doc)
    if doc.status != "draft":
        raise ValidationError({"detail": "Borderoul este aprobat; anulați întâi aprobarea."})


def payroll_closed(doc: MealVoucherList):
    """Calculul salariului lunii datei e aprobat pentru acești angajați: borderoul nu se aprobă / nu se anulează (partea
    impozabilă n-ar mai corespunde)."""
    jobs = list(MealVoucherLine.objects.filter(voucher_list=doc).values_list("employment_id", flat=True))
    closed = Payroll.objects.filter(year=doc.date.year, month=doc.date.month, status="approved", deletion_mark=False,
                                    lines__employment_id__in=jobs).distinct()
    if closed.exists():
        refs = ", ".join(f"nr. {p.number}" for p in closed[:3])
        raise ValidationError({"detail": f"Calculul salariului pe {doc.date:%m.%Y} ({refs}) e aprobat pentru acești angajați; "
                                         f"redeschideți-l întâi, apoi recalculați-l după borderou."})


def problems(doc: MealVoucherList) -> list:
    out = []
    c = constants(doc.date)
    if doc.value <= 0:
        out.append("Valoarea nominală a tichetului e 0: scrieți-o în borderou (sau în Constante → „meal_voucher_value”).")
    elif c["min"] and doc.value < c["min"]:
        out.append(f"Valoarea nominală {fmt(doc.value)} lei e sub minimul de {fmt(c['min'])} lei.")
    if (doc.date.year, doc.date.month) < (doc.year, doc.month):
        out.append("Data transferului e înaintea lunii lucrate.")
    lines = list(MealVoucherLine.objects.filter(voucher_list=doc).select_related("employee"))
    if not lines:
        out.append("Borderoul nu are rânduri: completați-l din pontaj.")
    dup = (MealVoucherLine.objects.filter(voucher_list__status="approved", voucher_list__deletion_mark=False,
                                          voucher_list__year=doc.year, voucher_list__month=doc.month,
                                          employment_id__in=[ln.employment_id for ln in lines])
           .exclude(voucher_list=doc).select_related("employee", "voucher_list"))
    for d in dup[:5]:
        out.append(f"{d.employee.full_name()} are deja tichetele pe {doc.month:02d}.{doc.year} în borderoul "
                   f"{d.voucher_list.reference()}.")
    return out


def approve(doc: MealVoucherList, user):
    editable(doc)
    found = problems(doc)
    if found:
        raise ValidationError({"detail": " ".join(found)})
    for ln in MealVoucherLine.objects.filter(voucher_list=doc):  # valoarea poate fi schimbată după completare
        price(ln, doc)
        ln.save(update_fields=["amount", "taxable"])
    payroll_closed(doc)
    doc.status, doc.approved_by, doc.approved_at = "approved", user, timezone.now()
    doc.save(update_fields=["status", "approved_by", "approved_at"])


def unapprove(doc: MealVoucherList):
    if doc.status != "approved":
        raise ValidationError({"detail": "Borderoul nu este aprobat."})
    payroll_closed(doc)
    doc.status, doc.approved_by, doc.approved_at = "draft", None, None
    doc.save(update_fields=["status", "approved_by", "approved_at"])


def totals(doc: MealVoucherList) -> dict:
    lines = list(doc.lines.all())
    return {"people": len(lines), "count": sum(ln.count for ln in lines), "amount": float(sum((ln.amount for ln in lines), ZERO)),
            "taxable": float(sum((ln.taxable for ln in lines), ZERO))}


def month_lines(first, last) -> dict:
    """{employment_id: [rândurile borderourilor aprobate cu data în lună]} — pentru calculul salariului."""
    out = defaultdict(list)
    for ln in (MealVoucherLine.objects.filter(voucher_list__status="approved", voucher_list__deletion_mark=False,
                                              voucher_list__date__gte=first, voucher_list__date__lte=last)
               .select_related("voucher_list").order_by("voucher_list__date", "voucher_list_id")):
        out[ln.employment_id].append(ln)
    return dict(out)


# --- tiparul ---------------------------------------------------------------------------------------------------------
def context(request, doc: MealVoucherList, lang="ro") -> dict:
    from apps.printing.renderer import company_context

    from .payment_printing import _d
    from .printing import _money

    rows = []
    for n, ln in enumerate(doc.lines.select_related("employee", "employment__occupation", "employment__subdivision")
                           .order_by("sort", "id"), start=1):
        rows.append({"no": n, "tab_number": ln.employee.tab_number, "name": ln.employee.full_name(),
                     "occupation": ln.employment.occupation.name_ro, "subdivision": ln.employment.subdivision.name_ro,
                     "days": ln.days, "hours": fmt(ln.day_hours + ln.night_hours) if ln.shifts else "",
                     "count": ln.count, "amount": _money(ln.amount), "taxable": _money(ln.taxable) if ln.taxable else "",
                     "note": ln.note})
    t = totals(doc)
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "rows": rows,
            "doc": {"number": doc.number, "date": _d(doc.date), "period": f"{doc.month:02d}.{doc.year}",
                    "value": _money(doc.value), "cap": _money(doc.cap), "status": doc.get_status_display(), "note": doc.note,
                    "approved": doc.status == "approved",
                    "subdivision": doc.subdivision.name_ro if doc.subdivision_id else ""},
            "totals": {"count": t["count"], "amount": _money(Decimal(str(t["amount"]))),
                       "taxable": _money(Decimal(str(t["taxable"]))) if t["taxable"] else ""},
            "today": _d(timezone.localdate()), "placeholders": {"număr": doc.number, "data": _d(doc.date)}}


def print_list(request, doc: MealVoucherList):
    from apps.printing.views import print_document

    from .payment_printing import _lang

    lang = _lang(request)
    return print_document(request, "meal_vouchers", context(request, doc, lang), template_id=request.query_params.get("template"),
                          title=f"Borderoul tichetelor de masă nr. {doc.number}", lang=lang)


def sample(request, lang, options):
    doc = MealVoucherList.objects.filter(lines__isnull=False).first()
    if doc is None:
        raise ValueError("Nu există încă borderouri ale tichetelor de masă.")
    return context(request, doc, lang)
