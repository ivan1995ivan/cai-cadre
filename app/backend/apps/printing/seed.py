from .models import PrintTemplate
from .renderer import default_body

# tip document, cod, nume, orientare, opțiunile implicite (formele livrate cresc odată cu modulele)
SYSTEM_TEMPLATES: list = [
    ("staff_list", "standard", "State de personal (structura + efectivul-limită)", "portrait",
     {"show_salary": True, "show_fund": False, "show_categories": True}),
    ("employee_card", "standard", "Fișa personală a salariatului (MR-2)", "portrait",
     {"show_photo": True, "show_family": True, "show_military": True, "show_salary": False}),
    ("certificate_work", "standard", "Adeverință de la locul de muncă", "portrait", {"show_salary": False, "show_idnp": True}),
    ("certificate_seniority", "standard", "Adeverință privind vechimea în muncă", "portrait", {"show_periods": True}),
    ("certificate_salary", "standard", "Adeverință privind salariul (pentru bancă)", "portrait", {"show_idnp": True}),
    ("order", "standard", "Ordin (individual sau colectiv)", "portrait", {}),
    ("order_extract", "standard", "Extras din ordin", "portrait", {}),
    ("orders_register", "standard", "Registrul ordinelor", "landscape", {}),
    ("timesheet", "standard", "Tabela de pontaj", "landscape", {}),
    ("payroll_sheet", "standard", "Stat de calcul al salariului", "landscape", {}),
    ("payslip", "standard", "Fișa de calcul (fluturașul)", "portrait", {}),
    ("payment_sheet", "standard", "Stat de plată (cu semnături pentru numerar)", "portrait", {}),
    ("bank_list", "standard", "Lista pentru bancă", "portrait", {}),
    ("annual_card", "standard", "Fișa personală de evidență a veniturilor (anexa 8)", "landscape", {}),
    ("roster", "standard", "Graficul de ture", "landscape", {}),
    ("leave_schedule", "standard", "Graficul concediilor de odihnă anuale", "landscape", {"show_signature": True}),
    ("employee_list", "standard", "Lista angajaților", "landscape",
     {"group_by_subdivision": True, "show_idnp": False, "show_phone": False, "show_rate": True}),
    ("report", "standard", "Raport (catalogul de rapoarte)", "landscape", {}),
]


RENAMED: set = set()  # numele vechi ale șabloanelor livrate


def _all_templates():
    """Formele livrate: (tip, cod, nume, orientare, opțiuni, coloane, texte)."""
    return [(*row, [], {}) for row in SYSTEM_TEMPLATES]


def run():
    for doc_type, code, name, orientation, options, columns, texts in _all_templates():
        body = default_body(doc_type)
        tpl, created = PrintTemplate.objects.get_or_create(
            doc_type=doc_type, code=code,
            defaults={"name": name, "body": body, "orientation": orientation, "default_options": options,
                      "is_system": True, "original_body": body, "is_default": code == "standard",
                      "columns": columns, "texts": texts},
        )
        if not created and tpl.is_system and tpl.name != name and tpl.name in RENAMED:
            # formularele vechi redenumite („Bon de plată”), cu opțiunile implicite noi
            tpl.name, tpl.default_options = name, options
            tpl.save(update_fields=["name", "default_options"])
        missing = {k: v for k, v in options.items() if k not in (tpl.default_options or {})}
        if not created and tpl.is_system and missing:
            # opțiunile noi (de ex. desenul pe fișa de debitare) intră și în formele livrate mai demult
            tpl.default_options = {**(tpl.default_options or {}), **missing}
            tpl.save(update_fields=["default_options"])
        if not created and tpl.is_system and tpl.original_body != body:
            # Versiune nouă a șablonului livrat: dacă administratorul nu l-a modificat, îl actualizăm.
            if tpl.body == tpl.original_body:
                tpl.body = body
            tpl.original_body = body
            tpl.save(update_fields=["body", "original_body"])
