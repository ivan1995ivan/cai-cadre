"""Rapoartele formării în catalogul general: creditele EMC, activitățile pe perioadă, calendarul atestării."""
from collections import Counter

from apps.reports.personnel import COMMON, Lookup, _d
from apps.reports.registry import LINKS, Link, col, report, subtitle_parts

from . import services
from .models import KINDS, TrainingRecord

STATUS_T = {"risk": ("Risc: atestarea fără credite", "Риск: аттестация без кредитов", "At risk"),
            "behind": ("În urmă", "Отстаёт", "Behind"), "ok": ("În grafic", "По графику", "On track"),
            "done": ("Acumulate", "Набраны", "Done")}


@report("emc_credits", "training", ("Creditele EMC în perioada de atestare", "Кредиты НМО за аттестационный период",
                                    "CME credits in the attestation period"),
        ("Pe angajat: categoria, perioada, creditele acumulate față de cele cerute, cât lipsește; cei în risc — primii.",
         "По работнику: категория, период, набранные и требуемые кредиты, сколько не хватает.",
         "Per employee: category, period, credits earned vs required, missing."),
        ["on_date", "subdivision", "category"])
def emc_credits(p):
    rows = services.credits_rows(p.on_date, p.sub_ids, p.category, p.lang)
    order = {"risk": 0, "behind": 1, "ok": 2, "done": 3}
    rows.sort(key=lambda r: (order[r["status"]], r["subdivision"], r["name"]))
    counts = Counter(r["status"] for r in rows)
    out = [{"tab": r["tab"], "name": r["name"], "sub": r["subdivision"], "occ": r["occupation"], "category": r["category"],
            "expiry": _d(r["expiry"]), "period_from": _d(r["period_from"]), "credits": r["credits"], "required": r["required"],
            "missing": r["missing"], "status": p.t(STATUS_T[r["status"]])} for r in rows]
    return {
        "subtitle": subtitle_parts(p, f"{p.t(('la data de', 'на', 'as of'))} {p.on_date:%d.%m.%Y}"),
        "columns": [col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("sub", p.t(COMMON["sub"])),
                    col("occ", p.t(COMMON["occ"])), col("category", p.t(("Categoria", "Категория", "Category"))),
                    col("period_from", p.t(("Perioada de la", "Период с", "Period from")), "date"),
                    col("expiry", p.t(("Expiră la", "Истекает", "Expires")), "date"),
                    col("credits", p.t(("Acumulate", "Набрано", "Earned")), "num"), col("required", p.t(("Cerute", "Требуется", "Required")), "num"),
                    col("missing", p.t(("Lipsesc", "Не хватает", "Missing")), "num"), col("status", p.t(("Situația", "Состояние", "Status")))],
        "rows": out,
        "summary": [{"label": p.t(STATUS_T[s]), "value": counts[s]} for s in ("risk", "behind", "ok", "done")],
    }


KIND_T = dict(KINDS)


@report("training_period", "training", ("Formarea pe perioadă", "Обучение за период", "Training by period"),
        ("Activitățile de formare (cursuri, conferințe, stagii) din perioadă: orele, creditele, certificatele; totalul pe tipuri — "
         "și pentru raportul statistic FORPRO.",
         "Мероприятия обучения за период: часы, кредиты, сертификаты; итоги по видам.",
         "Training activities in the period: hours, credits, certificates; totals by type."),
        ["period", "subdivision", "category"])
def training_period(p):
    look = Lookup(p.lang)
    from apps.reports.personnel import jobs_on

    visible = {e.employee_id: snap for e, snap in jobs_on(p, p.date_to, look, kinds="all")}
    rows, by_kind = [], Counter()
    hours = credits = 0.0
    for r in TrainingRecord.objects.filter(date_from__lte=p.date_to, deletion_mark=False).select_related("employee").order_by("date_from"):
        if (r.date_to or r.date_from) < p.date_from or r.employee_id not in visible:
            continue
        snap = visible[r.employee_id]
        by_kind[r.kind] += 1
        hours += float(r.hours)
        credits += float(r.credits)
        rows.append({"date_from": _d(r.date_from), "date_to": _d(r.date_to), "tab": r.employee.tab_number, "name": r.employee.full_name(),
                     "sub": look.sub(snap["subdivision_id"]), "kind": KIND_T.get(r.kind, r.kind), "title": r.title,
                     "provider": r.provider, "hours": float(r.hours), "credits": float(r.credits), "cert": r.certificate_number})
    return {
        "subtitle": subtitle_parts(p, p.period_text()),
        "columns": [col("date_from", p.t(("De la", "С", "From")), "date"), col("date_to", p.t(("Până la", "По", "To")), "date"),
                    col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("sub", p.t(COMMON["sub"])),
                    col("kind", p.t(COMMON["kind"])), col("title", p.t(("Cursul / activitatea", "Курс / мероприятие", "Course"))),
                    col("provider", p.t(("Organizatorul", "Организатор", "Provider"))), col("hours", p.t(("Ore", "Часы", "Hours")), "num"),
                    col("credits", p.t(("Credite", "Кредиты", "Credits")), "num"), col("cert", p.t(("Certificatul", "Сертификат", "Certificate")))],
        "rows": rows,
        "totals": {"tab": p.t(COMMON["total"]), "hours": hours, "credits": credits},
        "summary": [{"label": p.t(("Persoane instruite", "Обучено человек", "People trained")), "value": len({r["tab"] for r in rows})}]
        + [{"label": KIND_T[k], "value": n} for k, _ in KINDS if (n := by_kind[k])],
    }


LINKS.extend([
    Link("attestation", "training", ("Calendarul atestării", "Календарь аттестации", "Attestation calendar"),
         ("Categoriile care expiră, lista candidaților și ordinul de conferire.", "Истекающие категории, список кандидатов, приказ.",
          "Expiring categories, candidate list and award order."), "/training?tab=attestation", "training.view"),
    Link("training_plan", "training", ("Planul anual de formare", "Годовой план обучения", "Annual training plan"),
         ("Planul instituției pe angajați, cu realizarea.", "План учреждения по работникам, с выполнением.", "Institution plan with completion."),
         "/training?tab=plans", "training.view"),
])
