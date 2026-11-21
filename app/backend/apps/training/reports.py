"""Rapoartele formării în catalogul general: activitățile pe perioadă, certificatele care expiră, planul anual."""
from collections import Counter

from apps.reports.personnel import COMMON, Lookup, _d, jobs_on
from apps.reports.registry import LINKS, Link, col, report, subtitle_parts

from . import services
from .models import KINDS, TrainingRecord

KIND_T = dict(KINDS)


@report("training_period", "training", ("Formarea pe perioadă", "Обучение за период", "Training by period"),
        ("Activitățile de formare (cursuri, instruiri, seminare, stagii) din perioadă: orele, certificatele și termenul lor; "
         "totalul pe tipuri — și pentru raportările statistice despre formarea profesională.",
         "Мероприятия обучения за период: часы, сертификаты и срок их действия; итоги по видам.",
         "Training activities in the period: hours, certificates and their validity; totals by type."),
        ["period", "subdivision", "category"])
def training_period(p):
    look = Lookup(p.lang)
    visible = {e.employee_id: snap for e, snap in jobs_on(p, p.date_to, look, kinds="all")}
    rows, by_kind = [], Counter()
    hours = 0.0
    for r in TrainingRecord.objects.filter(date_from__lte=p.date_to, deletion_mark=False).select_related("employee").order_by("date_from"):
        if (r.date_to or r.date_from) < p.date_from or r.employee_id not in visible:
            continue
        snap = visible[r.employee_id]
        by_kind[r.kind] += 1
        hours += float(r.hours)
        rows.append({"date_from": _d(r.date_from), "date_to": _d(r.date_to), "tab": r.employee.tab_number, "name": r.employee.full_name(),
                     "sub": look.sub(snap["subdivision_id"]), "kind": KIND_T.get(r.kind, r.kind), "title": r.title,
                     "provider": r.provider, "hours": float(r.hours), "cert": r.certificate_number, "valid_until": _d(r.valid_until)})
    return {
        "subtitle": subtitle_parts(p, p.period_text()),
        "columns": [col("date_from", p.t(("De la", "С", "From")), "date"), col("date_to", p.t(("Până la", "По", "To")), "date"),
                    col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("sub", p.t(COMMON["sub"])),
                    col("kind", p.t(COMMON["kind"])), col("title", p.t(("Cursul / activitatea", "Курс / мероприятие", "Course"))),
                    col("provider", p.t(("Organizatorul", "Организатор", "Provider"))), col("hours", p.t(("Ore", "Часы", "Hours")), "num"),
                    col("cert", p.t(("Certificatul", "Сертификат", "Certificate"))),
                    col("valid_until", p.t(("Valabil până la", "Действует до", "Valid until")), "date")],
        "rows": rows,
        "totals": {"tab": p.t(COMMON["total"]), "hours": hours},
        "summary": [{"label": p.t(("Persoane instruite", "Обучено человек", "People trained")), "value": len({r["tab"] for r in rows})}]
        + [{"label": KIND_T[k], "value": n} for k, _ in KINDS if (n := by_kind[k])],
    }


@report("training_expiry", "training", ("Certificatele de formare care expiră", "Истекающие сертификаты обучения",
                                        "Expiring training certificates"),
        ("Certificatele cursurilor cu termen de valabilitate care expiră în perioadă (sau au expirat), fără un curs reînnoit "
         "după ele — cine trebuie trimis din nou la instruire.",
         "Сертификаты курсов со сроком действия, истекающие в периоде, без повторного курса — кого направить снова.",
         "Course certificates expiring in the period with no renewal — who must be retrained."),
        ["period", "subdivision", "category"])
def training_expiry(p):
    look = Lookup(p.lang)
    visible = {e.employee_id: snap for e, snap in jobs_on(p, p.date_to, look, kinds="all")}
    rows = []
    for r in services.expiring(p.date_from, p.date_to, employee_ids=set(visible)):
        snap = visible[r.employee_id]
        rows.append({"valid_until": _d(r.valid_until), "tab": r.employee.tab_number, "name": r.employee.full_name(),
                     "sub": look.sub(snap["subdivision_id"]), "occ": look.occ(snap["occupation_id"]), "title": r.title,
                     "provider": r.provider, "cert": r.certificate_number, "date_from": _d(r.date_from)})
    return {
        "subtitle": subtitle_parts(p, p.period_text()),
        "columns": [col("valid_until", p.t(("Valabil până la", "Действует до", "Valid until")), "date"),
                    col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("sub", p.t(COMMON["sub"])),
                    col("occ", p.t(COMMON["occ"])), col("title", p.t(("Cursul / activitatea", "Курс / мероприятие", "Course"))),
                    col("provider", p.t(("Organizatorul", "Организатор", "Provider"))),
                    col("cert", p.t(("Certificatul", "Сертификат", "Certificate"))),
                    col("date_from", p.t(("Cursul din", "Курс от", "Course of")), "date")],
        "rows": rows,
        "summary": [{"label": p.t(("Certificate", "Сертификатов", "Certificates")), "value": len(rows)}],
    }


LINKS.append(Link("training_plan", "training", ("Planul anual de formare", "Годовой план обучения", "Annual training plan"),
                  ("Planul întreprinderii pe angajați, cu realizarea.", "План предприятия по работникам, с выполнением.",
                   "The company plan by employee, with completion."), "/training?tab=plans", "training.view"))
