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
    "production_report": [
        ("title", "Titlul", "RAPORT DE PRODUCȚIE", "ОТЧЁТ О ВЫРАБОТКЕ", False),
        ("intro", "Textul de deasupra tabelului", "Lucrările executate în acord și primite:", "Выполненные и принятые сдельные работы:", True),
        ("members_title", "Titlul tabelului membrilor", "Împărțirea între membrii brigăzii", "Распределение между членами бригады", False),
        ("master_label", "Semnătura: a predat", "Maistrul (brigadierul)", "Мастер (бригадир)", False),
        ("accepted_label", "Semnătura: a primit", "A primit (controlul calității)", "Принял (ОТК)", False),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "meal_vouchers": [
        ("title", "Titlul", "BORDEROUL TICHETELOR DE MASĂ", "ВЕДОМОСТЬ ТАЛОНОВ НА ПИТАНИЕ", False),
        ("intro", "Textul de deasupra tabelului",
         "Tichetele de masă pentru luna lucrată, transferate pe instrumentul de plată al salariaților (Legea nr. 166/2017, "
         "HG nr. 227/2018):",
         "Талоны на питание за отработанный месяц, перечисленные на платёжный инструмент работников (Закон № 166/2017, "
         "ПП № 227/2018):", True),
        ("head_label", "Semnătura: conducătorul", "{funcția_conducătorului}", "{funcția_conducătorului}", False),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "trip_sheet": [
        ("title", "Titlul", "FOAIA DE PARCURS", "ПУТЕВОЙ ЛИСТ", False),
        ("legs_title", "Titlul tabelului țărilor", "Țările parcurse (trecerea frontierei)", "Пройденные страны (пересечение границы)", False),
        ("diem_title", "Titlul calculului diurnei", "Calculul diurnei (HG nr. 10/2012)", "Расчёт суточных (ПП № 10/2012)", False),
        ("driver_label", "Semnătura: șoferul", "Șoferul", "Водитель", False),
        ("dispatcher_label", "Semnătura: dispecerul", "Dispecerul", "Диспетчер", False),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "kpi_sheet": [
        ("title", "Titlul", "FIȘA KPI A LUNII", "ЛИСТ KPI ЗА МЕСЯЦ", False),
        ("intro", "Textul de deasupra tabelului",
         "Indicatorii de performanță ai șoferilor și prima KPI pentru luna dată, după schema din regulamentul de salarizare:",
         "Показатели эффективности водителей и премия KPI за месяц, по схеме из положения об оплате труда:", True),
        ("note", "Nota de sub tabel",
         "Prima = baza × punctajul (Σ pondere × nota / Σ ponderi; indicatorii fără date nu intră în punctaj). În calculul "
         "salariului prima se plătește proporțional cu timpul lucrat, dacă schema o cere.",
         "Премия = база × балл (Σ вес × оценка / Σ весов; показатели без данных в балл не входят). В расчёте зарплаты премия "
         "выплачивается пропорционально отработанному времени, если так задано в схеме.", True),
        ("head_label", "Semnătura: conducătorul", "{funcția_conducătorului}", "{funcția_conducătorului}", False),
        ("dispatcher_label", "Semnătura: șeful transportului", "Șeful serviciului transport", "Начальник службы транспорта", False),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "it_park_tax": [
        ("title", "Titlul", "CALCULUL IMPOZITULUI UNIC AL REZIDENTULUI PARCULUI IT", "РАСЧЁТ ЕДИНОГО НАЛОГА РЕЗИДЕНТА IT-ПАРКА", False),
        ("annex", "Mențiunea (dreapta sus)", "pentru declarația IU17\n(OMF nr. 135/2017, anexa nr. 1)", "для декларации IU17\n(ПМФ № 135/2017, приложение № 1)", True),
        ("note", "Nota de sub tabel",
         "Impozitul unic se calculează lunar, necumulativ (Codul fiscal, art. 371): 7 % din venitul din vânzări, dar cel puțin "
         "30 % din salariul mediu lunar prognozat pentru fiecare angajat cu contract individual de muncă care a activat cel puțin "
         "o zi în lună. Rândurile formularului în vigoare se verifică pe sfs.md înainte de depunere.",
         "Единый налог рассчитывается ежемесячно, без нарастающего итога (НК, ст. 371): 7 % от дохода от продаж, но не менее 30 % "
         "прогнозируемой средней зарплаты на каждого работника по индивидуальному трудовому договору, проработавшего хотя бы "
         "один день в месяце. Строки действующей формы проверяются на sfs.md перед подачей.", True),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "isapti17": [
        ("title", "Titlul", "NOTA DE INFORMARE PRIVIND SALARIILE ACHITATE DE REZIDENTUL PARCULUI IT (ISAPTI17)",
         "ИНФОРМАЦИОННАЯ СПРАВКА О ЗАРПЛАТАХ, ВЫПЛАЧЕННЫХ РЕЗИДЕНТОМ IT-ПАРКА (ISAPTI17)", False),
        ("annex", "Mențiunea (dreapta sus)", "Forma ISAPTI17\n(OMF nr. 135/2017, anexa nr. 3)", "Форма ISAPTI17\n(ПМФ № 135/2017, приложение № 3)", True),
        ("note", "Nota de sub tabel",
         "Se cuprind salariile din regimul impozitului unic, îndreptate spre achitare în anul fiscal; plățile din regimul general "
         "(lunile fără statut, contractele de prestări servicii) se declară în IALS21. Structura rubricilor — de verificat cu "
         "formularul în vigoare.",
         "Включаются зарплаты в режиме единого налога, направленные к выплате в налоговом году; выплаты в общем режиме "
         "(месяцы без статуса, договоры оказания услуг) декларируются в IALS21. Структуру граф — проверить по действующей форме.", True),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
        ("footer", "Text la sfârșit", "", "", True),
    ],
    "it_park_note": [
        ("title", "Titlul", "INFORMAȚIA PRIVIND SALARIUL ACHITAT ANGAJATULUI REZIDENTULUI PARCULUI IT",
         "ИНФОРМАЦИЯ О ЗАРПЛАТЕ, ВЫПЛАЧЕННОЙ РАБОТНИКУ РЕЗИДЕНТА IT-ПАРКА", False),
        ("annex", "Mențiunea (dreapta sus)", "OMF nr. 135/2017, anexa nr. 5", "ПМФ № 135/2017, приложение № 5", True),
        ("note", "Textul de sub tabel",
         "Salariul a fost impozitat final cu impozitul unic al rezidentului parcului IT (Codul fiscal, art. 377 alin. (1)): "
         "nu se declară în declarația persoanei fizice și nu se impozitează suplimentar.",
         "Зарплата окончательно обложена единым налогом резидента IT-парка (НК, ст. 377 ч. (1)): не декларируется в "
         "декларации физического лица и дополнительно не облагается.", True),
        ("accountant_label", "Semnătura: contabil-șef", "{funcția_contabilului}", "{funcția_contabilului}", False),
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
PLACEHOLDERS: dict = {"staff_list": ["număr", "data", "aprobat_prin"], "pay_item_change": ["număr", "data"],
                      "production_report": ["număr", "data"], "meal_vouchers": ["număr", "data"],
                      "trip_sheet": ["număr", "data"], "kpi_sheet": ["număr", "data"]}
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
