"""Tiparul statelor de personal (anexa la decizia de aprobare: structura + efectivul-limită pe categorii)."""
from apps.printing.renderer import company_context
from apps.printing.views import print_document

from . import services
from .models import STAFF_CATEGORIES, StaffList

OPTIONS = {"show_salary": True, "show_fund": False, "show_categories": True}

LABELS = {
    "ro": {"effective_from": "în vigoare de la", "approved_by": "Aprobat prin", "code": "Codul funcției (CORM)",
           "occupation": "Denumirea funcției", "units": "Unități", "salary": "Salariul de funcție, lei",
           "fund": "Fondul lunar, lei", "total": "Total", "grand_total": "Total pe instituție", "category": "Categoria de personal",
           "director": "Director", "hr_head": "Șef resurse umane", "chief_accountant": "Contabil-șef"},
    "ru": {"effective_from": "действует с", "approved_by": "Утверждено", "code": "Код должности (CORM)",
           "occupation": "Наименование должности", "units": "Единиц", "salary": "Должностной оклад, лей",
           "fund": "Месячный фонд, лей", "total": "Итого", "grand_total": "Итого по учреждению", "category": "Категория персонала",
           "director": "Директор", "hr_head": "Начальник отдела кадров", "chief_accountant": "Главный бухгалтер"},
    "en": {"effective_from": "effective from", "approved_by": "Approved by", "code": "Occupation code (CORM)",
           "occupation": "Position", "units": "Units", "salary": "Base salary, MDL", "fund": "Monthly fund, MDL",
           "total": "Total", "grand_total": "Institution total", "category": "Staff category", "director": "Director",
           "hr_head": "Head of HR", "chief_accountant": "Chief accountant"},
}

CATEGORY_LABELS = {
    "ru": {"leadership": "Руководящий персонал", "physicians": "Врачи (высшее образование)", "pharmacists": "Фармацевты",
           "nurses": "Средний медицинский персонал", "junior": "Младший медицинский персонал",
           "admin": "Административно-хозяйственный персонал", "other": "Прочий персонал"},
    "en": {"leadership": "Management", "physicians": "Physicians", "pharmacists": "Pharmacists", "nurses": "Nursing staff",
           "junior": "Junior medical staff", "admin": "Administrative and support staff", "other": "Other staff"},
}


def _fmt(value, lang="ro") -> str:
    """1 / 6,50 / 1 023 322 — virgula zecimală în RO și RU (ca în actele din Moldova), punctul în EN."""
    text = f"{value:,.2f}".replace(",", " ")
    text = text[:-3] if text.endswith(".00") else text
    return text if lang == "en" else text.replace(".", ",")


def context(request, staff_list: StaffList, lang: str, options: dict) -> dict:
    lines = list(staff_list.lines.select_related("subdivision", "occupation").order_by(
        "subdivision__sort", "subdivision__name_ro", "sort", "id"))
    groups, no = [], 0
    for line in lines:
        name = line.subdivision.local_name(lang)
        if not groups or groups[-1]["id"] != line.subdivision_id:
            groups.append({"id": line.subdivision_id, "name": name, "lines": [], "units": 0, "fund": 0})
        no += 1
        fund = line.monthly_fund()
        group = groups[-1]
        group["lines"].append({"no": no, "code": line.occupation.code, "occupation": line.occupation.local_name(lang),
                               "effort_note": line.effort_note, "units": _fmt(line.units, lang), "salary": _fmt(line.base_salary, lang),
                               "fund": _fmt(fund, lang)})
        group["units"] += line.units
        group["fund"] += fund
    for group in groups:
        group["units"], group["fund"] = _fmt(group["units"], lang), _fmt(group["fund"], lang)
    totals = services.totals(staff_list)
    names = CATEGORY_LABELS.get(lang, dict(STAFF_CATEGORIES))
    from decimal import Decimal

    totals = {
        "units": _fmt(Decimal(totals["units"]), lang), "fund": _fmt(Decimal(totals["fund"]), lang),
        "categories": [{"name": names.get(c["code"], c["name"]), "units": _fmt(Decimal(c["units"]), lang)} for c in totals["categories"]],
    }
    colspan = 4 + int(bool(options.get("show_salary"))) + int(bool(options.get("show_fund")))
    return {
        "company": company_context(request, lang), "lang": lang, "options": options, "labels": LABELS.get(lang, LABELS["ro"]),
        "doc": {"number": staff_list.number, "effective_from": staff_list.effective_from.strftime("%d.%m.%Y"),
                "approved_by": staff_list.approved_by},
        "groups": groups, "totals": totals, "colspan": colspan,
        "placeholders": {"număr": staff_list.number, "data": staff_list.effective_from.strftime("%d.%m.%Y"),
                         "aprobat_prin": staff_list.approved_by},
    }


def _options(request) -> dict:
    out = dict(OPTIONS)
    for key in OPTIONS:
        if key in request.query_params:
            out[key] = request.query_params[key] in ("1", "true")
    return out


def print_staff_list(request, staff_list: StaffList):
    lang = request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro"
    ctx = context(request, staff_list, lang, _options(request))
    return print_document(request, "staff_list", ctx, template_id=request.query_params.get("template"),
                          title=f"State de personal {ctx['doc']['effective_from']}", lang=lang)


def sample(request, lang, options):
    """Previzualizarea în editorul de forme: statele în vigoare (sau ultimele create)."""
    staff_list = services.current() or StaffList.objects.first()
    if staff_list is None:
        raise ValueError("Nu există încă state de personal — creați-le în Instituția → State de personal.")
    return context(request, staff_list, lang, {**OPTIONS, **options})
