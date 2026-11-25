"""Cronologia angajatului (fila „Cronologia” din fișă): tot ce s-a întâmplat cu el, pe o singură listă, cele mai noi sus —
istoria raporturilor de muncă (angajare, transferuri, salariu, suspendare, încetare), ordinele, absențele (concedii, deplasări,
staționare), certificatele medicale, sancțiunile și stimulările, formarea, cursele, salariul lunilor aprobate.

Fiecare fel de eveniment apare doar pentru cine are dreptul de vizualizare al modulului lui; salariul din istorie — doar
dacă rolul nu-l ascunde (staff.serializers.hidden_for)."""
from decimal import Decimal


def _d(day) -> str:
    return f"{day:%d.%m.%Y}" if day else ""


def _num(v) -> str:
    """Numărul fără zerouri în plus și fără notația științifică (3840, nu 3.84E+3)."""
    d = Decimal(v or 0).normalize()
    return format(d, "f").replace(".", ",")


def _money(v) -> str:
    return f"{Decimal(v or 0):,.2f}".replace(",", " ").replace(".", ",")


def events(employee, request) -> list:
    from apps.leave.models import Absence, SickLeave
    from apps.orders.models import Incentive, OrderItem, Sanction

    from .serializers import hidden_for

    user = request.user
    can = user.has_crm_perm
    hidden = hidden_for(request)
    out = []

    def add(day, kind, title, detail="", link=""):
        if day:
            out.append({"date": day, "kind": kind, "title": title, "detail": detail, "link": link})

    for job in employee.employments.select_related("occupation", "subdivision").prefetch_related(
            "history__occupation", "history__subdivision"):
        for h in job.history.all():
            parts = [h.occupation.name_ro, h.subdivision.name_ro, f"norma {_num(h.rate)}"]
            if "base_salary" not in hidden:
                parts.append(f"salariul {_money(h.base_salary)} lei")
            add(h.date, "job", f"{h.get_event_display()} — {job.get_kind_display().lower()}", "; ".join(parts)
                + (f" (ordinul {h.order})" if h.order else ""))
    if can("orders.view"):
        for it in (OrderItem.objects.filter(employee=employee).exclude(order__status="draft")
                   .exclude(order__deletion_mark=True).select_related("order__order_type")):
            o = it.order
            add(o.date, "order", f"Ordinul nr. {o.number or '—'}: {o.order_type.name_ro}"
                + (" (anulat)" if o.status == "cancelled" else ""), (it.text or "")[:300], f"/orders/{o.pk}")
        for s in Sanction.objects.filter(employee=employee).select_related("kind"):
            add(s.date, "sanction", f"Sancțiune: {s.kind.name_ro if s.kind_id else ''}".rstrip(": "))
        for s in Incentive.objects.filter(employee=employee).select_related("kind"):
            add(s.date, "incentive", f"Stimulare: {s.kind.name_ro if s.kind_id else ''}".rstrip(": "))
    if can("leave.view") or can("sick_leave.view"):
        for a in Absence.objects.filter(employee=employee).order_by("-date_from"):
            if a.kind == "sick" and not can("sick_leave.view"):
                continue
            if a.kind != "sick" and not can("leave.view"):
                continue
            days = (a.date_to - a.date_from).days + 1
            add(a.date_from, "sick" if a.kind == "sick" else "absence", a.get_kind_display(),
                f"{_d(a.date_from)} – {_d(a.date_to)}, {days} zile")
    if can("sick_leave.view"):
        for s in SickLeave.objects.filter(employee=employee, deletion_mark=False):
            add(s.issued_on or s.date_from, "sick", f"Certificat medical {s.series} {s.number}".strip(),
                f"{_d(s.date_from)} – {_d(s.date_to)}", "/sick-leave")
    if can("training.view"):
        from apps.training.models import TrainingRecord as Training

        for t in Training.objects.filter(employee=employee):
            add(t.date_from, "training", f"{t.get_kind_display()}: {t.title}"[:200],
                ", ".join(x for x in (t.provider, f"{_num(t.hours)} ore" if t.hours else "") if x))
    from apps.core.models import Company

    if can("transport.view") and getattr(Company.get(), "transport_enabled", False):
        from django.db.models import Q
        from django.utils import timezone

        from apps.transport.models import Trip

        for t in (Trip.objects.filter(Q(driver__employee=employee) | Q(co_driver__employee=employee), deletion_mark=False)
                  .select_related("vehicle")):
            add(timezone.localtime(t.departure).date(), "trip", f"Cursa {t.reference()} ({t.get_status_display().lower()})",
                f"{t.route or ''} · {t.vehicle.plate} · {_num(t.km)} km".strip(" ·"), f"/transport/trips/{t.pk}")
    if can("payroll.view"):
        from datetime import date

        from apps.payroll.models import PayrollLine

        for ln in (PayrollLine.objects.filter(employee=employee, payroll__status="approved", payroll__deletion_mark=False)
                   .select_related("payroll")):
            p = ln.payroll
            add(date(p.year, p.month, 1), "pay", f"Salariul pe {p.month:02d}.{p.year}",
                f"calculat {_money(ln.gross)} lei, de plată {_money(ln.net)} lei", f"/payroll/{p.pk}")
    out.sort(key=lambda e: (e["date"], e["kind"]), reverse=True)
    return out
