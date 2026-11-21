"""Tiparul dosarului: fișa personală (MR-2), adeverința de la locul de muncă, adeverința de vechime, lista angajaților."""
from django.utils import timezone

from apps.core.models import Company, NumberSeries
from apps.printing.renderer import company_context
from apps.printing.views import print_document

from . import services
from .models import Employee

EMPLOYEE_DOCS = {"employee_card", "certificate_work", "certificate_seniority", "certificate_salary"}
CERTIFICATES = ("certificate_work", "certificate_seniority", "certificate_salary")  # se înregistrează (numărul crește)

OPTIONS = {
    "employee_card": {"show_photo": True, "show_family": True, "show_military": True, "show_salary": False},
    "certificate_work": {"show_salary": False, "show_idnp": True},
    "certificate_seniority": {"show_periods": True},
    "certificate_salary": {"show_idnp": True},
    "employee_list": {"group_by_subdivision": True, "show_idnp": False, "show_phone": False, "show_rate": True},
}


def _d(value):
    return value.strftime("%d.%m.%Y") if value else ""


def _n(value, lang="ro"):
    if value in (None, ""):
        return ""
    text = f"{value:,.2f}".replace(",", " ")
    text = text[:-3] if text.endswith(".00") else text
    return text if lang == "en" else text.replace(".", ",")


def _lang(request):
    return request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro"


def _options(request, doc):
    out = dict(OPTIONS.get(doc, {}))
    for key in out:
        if key in request.query_params:
            out[key] = request.query_params[key] in ("1", "true")
    return out


def _name(obj, lang):
    return obj.local_name(lang) if obj else ""


def employee_context(request, emp: Employee, lang: str, options: dict, doc: str) -> dict:
    from .serializers import hidden_for

    hidden = hidden_for(request)
    jobs = []
    for job in emp.employments.select_related("subdivision", "occupation", "termination_reason").prefetch_related(
            "history__subdivision", "history__occupation"):
        history = [{"date": _d(h.date), "event": h.get_event_display(), "subdivision": _name(h.subdivision, lang),
                    "occupation": _name(h.occupation, lang), "rate": _n(h.rate, lang),
                    "salary": "" if "base_salary" in hidden else _n(h.base_salary, lang), "order": h.order}
                   for h in job.history.all()]
        jobs.append({
            "id": job.id, "kind_code": job.kind, "kind": job.get_kind_display(), "status": job.status, "subdivision": _name(job.subdivision, lang),
            "occupation": _name(job.occupation, lang), "code": job.occupation.code, "rate": _n(job.rate, lang),
            "salary": "" if "base_salary" in hidden else _n(job.base_salary, lang), "date_from": _d(job.date_from),
            "date_to": _d(job.date_to), "end_date": _d(job.end_date), "contract": job.contract_number,
            "contract_date": _d(job.contract_date), "reason": _name(job.termination_reason, lang),
            "hire_order": job.hire_order, "end_order": job.end_order, "history": history,
        })
    sen = services.seniority(emp)
    periods = [{"organization": p.organization, "position": p.position, "from": _d(p.date_from), "to": _d(p.date_to),
                "specialty": p.in_specialty} for p in emp.experience.all()]
    company = company_context(request, lang)
    periods += [{"organization": company["name"], "position": j["occupation"], "from": j["date_from"],
                 "to": j["end_date"] or "prezent", "specialty": True} for j in jobs if j["kind_code"] != "substitute"]
    main = emp.main_employment()
    show_idnp = "idnp" not in hidden
    identity = emp.documents.filter(is_identity=True).select_related("doc_type").first()
    military = getattr(emp, "military", None)
    if not Company.get().military_enabled:  # modulul „Evidența militară” e oprit: secțiunea nu apare pe fișă
        options, military = {**options, "show_military": False}, None
    return {
        "company": company, "lang": lang, "options": options, "today": _d(timezone.localdate()),
        "emp": {
            "tab_number": emp.tab_number, "full_name": emp.full_name(), "last_name": emp.last_name,
            "first_name": emp.first_name, "patronymic": emp.patronymic, "previous_names": emp.previous_names,
            "idnp": emp.idnp if show_idnp else "", "birth_date": _d(emp.birth_date),
            "birth_place": emp.birth_place if show_idnp else "", "sex": emp.get_sex_display(),
            "citizenship": emp.citizenship, "nationality": _name(emp.nationality, lang),
            "marital": _name(emp.marital_status, lang),
            "address": "" if "address" in hidden else emp.address, "address_actual": "" if "address" in hidden else emp.address_actual,
            "phone": "" if "phone" in hidden else emp.phone, "email": "" if "email" in hidden else emp.email,
            "cnam_code": emp.cnam_code if show_idnp else "", "cpas": emp.cpas if show_idnp else "",
            "photo": request.build_absolute_uri(emp.photo.url) if emp.photo and options.get("show_photo") else "",
            "status": emp.get_status_display(), "sex_code": emp.sex,
        },
        "identity": ({"name": _name(identity.doc_type, lang) or identity.title, "series": identity.series,
                      "number": identity.number, "issued_by": identity.issued_by, "issue_date": _d(identity.issue_date),
                      "expiry_date": _d(identity.expiry_date)} if identity and show_idnp else None),
        "main": next((j for j in jobs if main and j["id"] == main.id), None),
        "jobs": jobs,
        "education": [{"level": _name(e.level, lang), "institution": e.institution,
                       "specialty": _name(e.specialty, lang) or e.specialty_text, "qualification": e.qualification,
                       "form": _name(e.form, lang), "year_to": e.year_to or "",
                       "diploma": " ".join(x for x in (e.diploma_series, e.diploma_number) if x), "diploma_date": _d(e.diploma_date)}
                      for e in emp.education.select_related("level", "specialty", "form")],
        "family": ([] if "family" in request.user.hidden_fields() else
                   [{"relation": _name(f.relation, lang), "name": f.full_name, "birth_date": _d(f.birth_date),
                     "idnp": f.idnp if show_idnp else "", "dependent": f.dependent} for f in emp.family.select_related("relation")]),
        "military": ({"status": military.get_status_display(), "category": military.get_category_display(),
                      "group": _name(military.group, lang), "composition": military.get_composition_display(),
                      "rank": _name(military.rank, lang), "specialty": military.specialty_code,
                      "center": _name(military.center, lang), "fit": military.fit, "book": military.book}
                     if military else None),
        "documents": [{"name": _name(d.doc_type, lang) or d.title, "series": d.series, "number": d.number,
                       "issued_by": d.issued_by, "issue_date": _d(d.issue_date), "expiry_date": _d(d.expiry_date)}
                      for d in emp.documents.select_related("doc_type")] if show_idnp else [],
        "periods": periods,
        "seniority": {k: services.seniority_text(v, lang) for k, v in sen.items() if k != "on_date"},
        "purpose": request.query_params.get("purpose", ""),
        "placeholders": {"număr": "", "data": _d(timezone.localdate()), "angajat": emp.full_name()},
    }


def _lei(value) -> str:
    """Suma în lei pentru adeverință: mereu cu două zecimale (12 345,00), zero — 0,00."""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def salary_period(params, today=None, last_paid=None) -> tuple:
    """Perioada adeverinței privind salariul: `from` / `to` (AAAA-LL, lunile incluse) sau ultimele `months` luni (3, 6, 12;
    implicit 6) încheiate — fără luna curentă și, cu `last_paid` (ultima lună cu calcul aprobat a angajatului), până la
    ea: dacă luna trecută nu e încă aprobată, perioada are tot N luni de salariu. Întoarce ((an, lună), (an, lună))."""
    today = today or timezone.localdate()

    def ym(text):
        try:
            y, m = (int(x) for x in str(text).split("-")[:2])
        except (TypeError, ValueError):
            return None
        return (y, m) if 2000 <= y <= 2100 and 1 <= m <= 12 else None

    start, end = ym(params.get("from")), ym(params.get("to"))
    if start and end:
        if start > end:
            raise ValueError("Începutul perioadei e după sfârșitul ei.")
        if (end[0] - start[0]) * 12 + end[1] - start[1] >= 36:
            raise ValueError("Perioada e de cel mult 36 de luni.")
        return start, end
    try:
        months = int(params.get("months") or 6)
    except ValueError:
        months = 6
    months = min(max(months, 1), 36)
    last = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    if last_paid and last_paid < last:
        last = last_paid
    first_index = last[0] * 12 + last[1] - 1 - (months - 1)
    return (first_index // 12, first_index % 12 + 1), last


def salary_context(emp: Employee, start: tuple, end: tuple) -> dict:
    """Salariul pe lunile perioadei, din calculele aprobate și decontarea lunii (payments.settlement): calculat, CNAM,
    impozitul, alte rețineri, netul; totalul, media lunară și reținerile lunare pe tipuri (sindicat, pensie alimentară...)."""
    from apps.payroll.models import PayrollItem
    from apps.payroll.payments import settlement
    from apps.payroll.printing import MONTHS

    rows, total = [], {k: 0 for k in ("gross", "cnam", "income_tax", "deductions", "net")}
    y, m = start
    while (y, m) <= end:
        s = settlement(y, m, employee_ids=[emp.pk]).get(emp.pk)
        if s:
            row = {k: s[k] for k in total}
            for k in total:
                total[k] += row[k]
            rows.append({"month": MONTHS[m], "year": y, **{k: _lei(v) for k, v in row.items()}})
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    count = len(rows)
    held = {}
    items = PayrollItem.objects.filter(line__employee=emp, line__payroll__status="approved", line__payroll__deletion_mark=False,
                                       pay_type__category="deduction").exclude(pay_type__auto__in=("income_tax", "cnam", "advance"))
    for i in items.select_related("pay_type", "line__payroll"):
        p = i.line.payroll
        if start <= (p.year, p.month) <= end:
            held[i.pay_type.name_ro] = held.get(i.pay_type.name_ro, 0) + i.amount
    return {"from": f"{MONTHS[start[1]]} {start[0]}", "to": f"{MONTHS[end[1]]} {end[0]}", "rows": rows, "count": count,
            "total": {k: _lei(v) for k, v in total.items()},
            "average": {k: _lei(v / count) if count else "" for k, v in total.items()},
            "deductions": [{"name": k, "monthly": _lei(v / count)} for k, v in sorted(held.items()) if count and v]}


def print_employee(request, emp: Employee, doc: str):
    lang = _lang(request)
    options = _options(request, doc)
    ctx = employee_context(request, emp, lang, options, doc)
    if doc == "certificate_salary":
        from rest_framework.exceptions import ValidationError

        from apps.payroll.models import PayrollLine

        latest = (PayrollLine.objects.filter(employee=emp, payroll__status="approved", payroll__deletion_mark=False)
                  .order_by("-payroll__year", "-payroll__month").values_list("payroll__year", "payroll__month").first())
        try:
            start, end = salary_period(request.query_params, last_paid=tuple(latest) if latest else None)
        except ValueError as exc:
            raise ValidationError({"period": str(exc)}) from None
        ctx["salary"] = salary_context(emp, start, end)
    if doc in CERTIFICATES and request.query_params.get("preview") != "1":
        ctx["number"] = NumberSeries.next_number("certificate")  # adeverința se înregistrează (numărul crește)
    else:
        ctx["number"] = ""
    ctx["placeholders"]["număr"] = ctx["number"]
    titles = {"employee_card": "Fișa personală", "certificate_work": "Adeverință", "certificate_seniority": "Adeverință de vechime",
              "certificate_salary": "Adeverință privind salariul"}
    return print_document(request, doc, ctx, template_id=request.query_params.get("template"),
                          title=f"{titles[doc]} — {emp.full_name()}", lang=lang)


def list_context(request, employees, lang, options):
    from .serializers import hidden_for

    hidden = hidden_for(request)
    groups = {}
    rows = []
    for no, emp in enumerate(employees, start=1):
        main = emp.main_employment()
        row = {"no": no, "tab": emp.tab_number, "name": emp.full_name(), "idnp": "" if "idnp" in hidden else emp.idnp,
               "phone": "" if "phone" in hidden else emp.phone, "birth_date": _d(emp.birth_date),
               "subdivision": _name(main.subdivision, lang) if main else "", "occupation": _name(main.occupation, lang) if main else "",
               "kind": main.get_kind_display() if main else "", "rate": _n(main.rate, lang) if main else "",
               "date_from": _d(main.date_from) if main else "", "status": emp.get_status_display()}
        rows.append(row)
        groups.setdefault(row["subdivision"], []).append(row)
    return {"company": company_context(request, lang), "lang": lang, "options": options, "today": _d(timezone.localdate()),
            "rows": rows, "groups": [{"name": k, "rows": v} for k, v in sorted(groups.items())], "count": len(rows),
            "placeholders": {"data": _d(timezone.localdate())}}


def print_list(request, queryset):
    lang = _lang(request)
    options = _options(request, "employee_list")
    return print_document(request, "employee_list", list_context(request, list(queryset[:5000]), lang, options),
                          template_id=request.query_params.get("template"), title="Lista angajaților", lang=lang)


def _sample_employee():
    emp = Employee.objects.filter(employments__isnull=False).first() or Employee.objects.first()
    if emp is None:
        raise ValueError("Nu există încă angajați — adăugați sau importați un angajat.")
    return emp


def sample_builder(doc):
    def build(request, lang, options):
        emp = _sample_employee()
        ctx = employee_context(request, emp, lang, {**OPTIONS.get(doc, {}), **options}, doc)
        if doc == "certificate_salary":
            ctx["salary"] = salary_context(emp, *salary_period({}))
        ctx["number"] = "AD-0000"
        return ctx
    return build


def sample_list(request, lang, options):
    return list_context(request, list(Employee.objects.all()[:30]), lang, {**OPTIONS["employee_list"], **options})
