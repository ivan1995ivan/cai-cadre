"""Textele formularelor pe care le schimbă oricine, fără HTML (editorul simplu din „Forme de tipar”).

Fiecare tip de document are câteva texte cu nume (titlul, semnăturile, textul de la sfârșit), în română și rusă, cu
valori implicite. Șablonul le folosește ca {{ texts.title }}; în text se pot pune valorile documentului ({număr},
{data} …) și datele din Constante ({întreprinderea}, {funcția_conducătorului}, {conducătorul} …) — semnăturile iau
implicit funcțiile semnatarilor scrise în Constante. Stilul: mărimea scrisului și logo-ul (da / nu).
"""

# tip document → [(cheia, eticheta în editor, implicit RO, implicit RU, mai multe rânduri)]
FIELDS: dict = {
    "staff_list": [
        ("annex", "Mențiunea „Anexa” (dreapta sus)", "Anexa nr. 1\n{aprobat_prin}", "Приложение № 1\n{aprobat_prin}", True),
        ("title", "Titlul", "STATELE DE PERSONAL", "ШТАТНОЕ РАСПИСАНИЕ", False),
        ("limit_title", "Titlul tabelului pe categorii", "Efectivul-limită al unităților de personal",
         "Предельная численность штатных единиц", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "employee_card": [
        ("title", "Titlul", "FIȘA PERSONALĂ A SALARIATULUI", "ЛИЧНАЯ КАРТОЧКА РАБОТНИКА", False),
        ("subtitle", "Sub titlu", "formular MR-2", "форма MR-2", False),
        ("hr_label", "Semnătura: resurse umane", "{funcția_resurse_umane}", "{funcția_resurse_umane}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "certificate_work": [
        ("title", "Titlul", "ADEVERINȚĂ", "СПРАВКА", False),
        ("hr_label", "Semnătura: resurse umane", "{funcția_resurse_umane}", "{funcția_resurse_umane}", False),
        ("footer", "Text după conținut", "", "", True),
    ],
    "certificate_seniority": [
        ("title", "Titlul", "ADEVERINȚĂ PRIVIND VECHIMEA ÎN MUNCĂ", "СПРАВКА О ТРУДОВОМ СТАЖЕ", False),
        ("hr_label", "Semnătura: resurse umane", "{funcția_resurse_umane}", "{funcția_resurse_umane}", False),
        ("footer", "Text la sfârșit", "Vechimea s-a calculat în baza carnetului de muncă (până la 01.01.2019), a "
                                    "certificatelor prezentate și a ordinelor întreprinderii.", "", True),
    ],
    "certificate_salary": [
        ("title", "Titlul", "ADEVERINȚĂ PRIVIND SALARIUL", "СПРАВКА О ЗАРАБОТНОЙ ПЛАТЕ", False),
        ("footer", "Text după tabel", "Întreprinderea nu se află în proces de insolvabilitate sau lichidare. Ne asumăm răspunderea "
                                      "pentru veridicitatea datelor din prezenta adeverință. Adeverința este valabilă 30 de zile "
                                      "de la data eliberării.", "", True),
    ],
    "employee_list": [
        ("title", "Titlul", "LISTA ANGAJAȚILOR", "СПИСОК СОТРУДНИКОВ", False),
        ("hr_label", "Semnătura", "{funcția_resurse_umane}", "{funcția_resurse_umane}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "report": [
        ("signer_label", "Semnătura", "{funcția_resurse_umane}", "{funcția_resurse_umane}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "order": [
        ("title", "Titlul documentului", "ORDIN", "ПРИКАЗ", False),
        ("city", "Localitatea (sub titlu)", "mun. Chișinău", "мун. Кишинэу", False),
        ("ordain", "Cuvântul dinaintea punctelor", "ORDON:", "ПРИКАЗЫВАЮ:", False),
        ("acquaint", "Titlul tabelului de luare la cunoștință", "Am luat cunoștință:", "С приказом ознакомлены:", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "order_extract": [
        ("title", "Titlul", "EXTRAS", "ВЫПИСКА", False),
        ("true_copy", "Mențiunea de conformitate", "Extras conform originalului", "Выписка верна", False),
    ],
    "payroll_sheet": [
        ("title", "Titlul", "STAT DE CALCUL AL SALARIULUI", "РАСЧЁТНАЯ ВЕДОМОСТЬ", False),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("made_by", "Semnătura: a calculat", "A calculat (contabil salarii)", "Рассчитал (бухгалтер по зарплате)", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "payment_sheet": [
        ("title", "Titlul", "STAT DE PLATĂ", "ПЛАТЁЖНАЯ ВЕДОМОСТЬ", False),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("cashier_label", "Semnătura: casierul", "A plătit (casierul)", "Выплатил (кассир)", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "bank_list": [
        ("title", "Titlul", "LISTA PENTRU BANCĂ", "СПИСОК ДЛЯ БАНКА", False),
        ("intro", "Textul de sub titlu", "privind transferul salariilor pe conturile de card ale angajaților",
         "о перечислении заработной платы на карточные счета работников", True),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "annual_card": [
        ("title", "Titlul", "FIȘA PERSONALĂ DE EVIDENȚĂ A VENITURILOR SUB FORMĂ DE SALARIU ȘI A IMPOZITULUI PE VENIT REȚINUT",
         "ЛИЧНАЯ КАРТОЧКА УЧЁТА ДОХОДОВ В ВИДЕ ЗАРАБОТНОЙ ПЛАТЫ И УДЕРЖАННОГО ПОДОХОДНОГО НАЛОГА", False),
        ("annex", "Mențiunea „Anexa” (dreapta sus)", "Anexa nr. 8\nla Regulamentul aprobat prin HG nr. 697/2014",
         "Приложение № 8\nк Положению, утверждённому ПП № 697/2014", True),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "exemption_request": [
        ("title", "Titlul", "CEREREA ANGAJATULUI PRIVIND ACORDAREA SCUTIRILOR LA IMPOZITUL PE VENIT REȚINUT DIN SALARIU",
         "ЗАЯВЛЕНИЕ РАБОТНИКА О ПРЕДОСТАВЛЕНИИ ОСВОБОЖДЕНИЙ ОТ ПОДОХОДНОГО НАЛОГА, УДЕРЖИВАЕМОГО ИЗ ЗАРАБОТНОЙ ПЛАТЫ", False),
        ("annex", "Mențiunea „Anexa” (dreapta sus)", "Anexa nr. 6\nla Regulamentul aprobat prin HG nr. 697/2014",
         "Приложение № 6\nк Положению, утверждённому ПП № 697/2014", True),
        ("declaration", "Declarația angajatului",
         "Declar că datele sunt adevărate, că persoanele întreținute nu au venituri anuale peste plafonul din Codul fiscal "
         "(art. 35) și că scutirile cerute nu se aplică la alt loc de muncă. La orice schimbare depun o cerere nouă în 10 zile.",
         "Заявляю, что данные верны, что иждивенцы не имеют годового дохода выше предела Налогового кодекса (ст. 35) и что "
         "запрошенные освобождения не применяются на другом месте работы. При любом изменении подаю новое заявление в течение 10 дней.", True),
        ("employer_note", "Mențiunea angajatorului", "Numele, codul fiscal și dreptul angajatului la scutiri pe categorii sunt verificate.",
         "Фамилия, фискальный код и право работника на освобождения по категориям проверены.", True),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "pay_item_change": [
        ("title", "Titlul", "MODIFICAREA ACUMULĂRILOR PLANIFICATE", "ИЗМЕНЕНИЕ ПЛАНОВЫХ НАЧИСЛЕНИЙ", False),
        ("intro", "Textul de deasupra tabelului", "Se stabilesc, se modifică sau se opresc acumulările și reținerile angajaților:",
         "Устанавливаются, изменяются или прекращаются начисления и удержания работников:", True),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("made_by", "Semnătura: a întocmit", "A întocmit", "Составил", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "payslip": [
        ("title", "Titlul", "Fișa de calcul a salariului", "Расчётный листок", False),
        ("footer", "Text la sfârșit", "Fișa este confidențială; se înmânează doar angajatului.", "Листок конфиденциален; выдаётся только работнику.", True),
    ],
    "timesheet": [
        ("title", "Titlul", "TABELA DE PONTAJ", "ТАБЕЛЬ УЧЁТА РАБОЧЕГО ВРЕМЕНИ", False),
        ("head_label", "Semnătura: șeful subdiviziunii", "Șeful subdiviziunii", "Руководитель подразделения", False),
        ("made_by", "Semnătura: a întocmit", "A întocmit", "Составил", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "roster": [
        ("approve", "Mențiunea „Aprob” (dreapta sus)", "APROB\nȘeful subdiviziunii ______________",
         "УТВЕРЖДАЮ\nРуководитель ______________", True),
        ("title", "Titlul", "GRAFICUL DE TURE", "ГРАФИК СМЕН", False),
        ("head_label", "Semnătura: șeful subdiviziunii", "Șeful subdiviziunii", "Руководитель подразделения", False),
        ("hr_label", "Semnătura: resurse umane", "{funcția_resurse_umane}", "{funcția_resurse_umane}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "leave_schedule": [
        ("approve", "Mențiunea „Aprob” (dreapta sus)", "APROB\n{funcția_conducătorului} ______________ {conducătorul}",
         "УТВЕРЖДАЮ\n{funcția_conducătorului} ______________ {conducătorul}",
         True),
        ("title", "Titlul", "GRAFICUL CONCEDIILOR DE ODIHNĂ ANUALE", "ГРАФИК ЕЖЕГОДНЫХ ОТПУСКОВ", False),
        ("head_label", "Semnătura: șeful subdiviziunii", "Șeful subdiviziunii", "Руководитель подразделения", False),
        ("hr_label", "Semnătura: resurse umane", "{funcția_resurse_umane}", "{funcția_resurse_umane}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "orders_register": [
        ("title", "Titlul", "REGISTRUL ORDINELOR", "ЖУРНАЛ РЕГИСТРАЦИИ ПРИКАЗОВ", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
}

# Ce se poate scrie în texte (în acolade) — arătat în editor: ale documentului și cele din Constante (în toate formele)
PLACEHOLDERS: dict = {"staff_list": ["număr", "data", "aprobat_prin"], "pay_item_change": ["număr", "data"]}
COMPANY_PLACEHOLDERS = {
    "întreprinderea": "full_name", "conducătorul": "director", "funcția_conducătorului": "director_position",
    "contabilul": "chief_accountant", "funcția_contabilului": "chief_accountant_position",
    "resurse_umane": "hr_head", "funcția_resurse_umane": "hr_head_position",
}


def placeholders_for(doc_type: str) -> list:
    return [*PLACEHOLDERS.get(doc_type, []), *COMPANY_PLACEHOLDERS]

FONT_SIZES = {"small": "11px", "normal": "12.5px", "large": "14px"}


def fields_for(doc_type: str) -> list:
    return [{"key": k, "label": label, "ro": ro, "ru": ru, "multiline": multi} for k, label, ro, ru, multi in FIELDS.get(doc_type, [])]


def resolve(doc_type: str, stored: dict | None, lang: str, values: dict | None = None) -> dict:
    """Textele pentru tipar: cele scrise în șablon (pe limbă), altfel cele implicite; cu {număr} etc. înlocuite."""
    stored = stored or {}
    out = {}
    for key, _label, ro, ru, _multi in FIELDS.get(doc_type, []):
        text = (stored.get(lang) or {}).get(key)
        if text is None or text == "":
            text = (stored.get("ro") or {}).get(key) if lang != "ro" and not (ru if lang == "ru" else ro) else None
        if text is None or text == "":
            text = ru if lang == "ru" else ro
        for name, value in (values or {}).items():
            text = text.replace("{" + name + "}", str(value or ""))
        out[key] = text
    return out


def apply(context: dict, doc_type: str, texts: dict | None, style: dict | None, lang: str) -> dict:
    """Pune în context textele (`texts`) și stilul (`style`): fără logo, dacă așa s-a ales."""
    style = {"font_size": "normal", "show_logo": True, **(style or {})}
    company = context.get("company") or {}
    values = {name: company.get(key, "") for name, key in COMPANY_PLACEHOLDERS.items()}
    values.update(context.get("placeholders") or {})
    context = {**context, "texts": resolve(doc_type, texts, lang, values), "style": style}
    if not style.get("show_logo") and context.get("company"):
        context["company"] = {**context["company"], "logo": ""}
    return context


def style_css(style: dict | None) -> str:
    size = FONT_SIZES.get((style or {}).get("font_size") or "normal", FONT_SIZES["normal"])
    return f"body {{ font-size: {size}; }}"
