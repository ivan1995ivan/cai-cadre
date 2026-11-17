"""Datele inițiale ale clasificatoarelor. Idempotente: adaugă doar ce lipsește și nu schimbă ce a modificat clientul.

Surse: configurația 1C „Cadre” (Personal.cf) pentru enumerări și ordine, decizia de aprobare a statelor IMSP CS Căzănești
(2026) pentru codurile CORM marcate „verificat”, Codul muncii nr. 154/2003 pentru temeiurile legale. Codurile CORM ale
funcțiilor de spital fără cod se completează la instalare (import din Excel al clasificatorului CORM 006-21).
"""
from .models import DictItem, LegalBasis, Occupation, OrderType, Specialty

# (cod CORM, RO, RU, EN, categoria, ore/săpt.)
OCCUPATIONS = [
    # codurile din statele aprobate ale unui IMSP (Decizia CR Telenești nr. 1/2026, anexa 1)
    ("221104", "Medic de familie", "Семейный врач", "Family physician", "physicians", 35),
    ("322101", "Asistent medical de familie", "Семейная медсестра", "Family nurse", "nurses", 35),
    ("322101.06", "Asistent medical superior", "Старшая медсестра", "Head nurse", "nurses", 35),
    ("321203", "Felcer laborant", "Фельдшер-лаборант", "Laboratory feldsher", "nurses", 35),
    ("322102", "Laborant", "Лаборант", "Laboratory assistant", "nurses", 35),
    ("325501", "Asistent medical fizioterapie", "Медсестра по физиотерапии", "Physiotherapy nurse", "nurses", 35),
    ("532102", "Infermieră", "Санитарка", "Nurse aide", "junior", 40),
    ("121103", "Contabil-șef", "Главный бухгалтер", "Chief accountant", "admin", 40),
    ("832202", "Conducător auto", "Водитель", "Driver", "admin", 40),
    ("962202", "Muncitor auxiliar", "Подсобный рабочий", "Auxiliary worker", "admin", 40),
    ("818206", "Operator sala de cazane", "Оператор котельной", "Boiler room operator", "admin", 40),
    # funcțiile tipice ale unui spital de traumatologie — codul CORM se completează din clasificator
    ("", "Director", "Директор", "Director", "leadership", 40),
    ("", "Director adjunct medical", "Заместитель директора по медицинской части", "Deputy medical director", "leadership", 40),
    ("", "Șef secție — medic", "Заведующий отделением — врач", "Head of department (physician)", "physicians", 35),
    ("", "Medic traumatolog-ortoped", "Врач травматолог-ортопед", "Orthopaedic trauma surgeon", "physicians", 35),
    ("", "Medic anesteziolog-reanimatolog", "Врач анестезиолог-реаниматолог", "Anaesthesiologist", "physicians", 35),
    ("", "Medic chirurg", "Врач-хирург", "Surgeon", "physicians", 35),
    ("", "Medic neurochirurg", "Врач-нейрохирург", "Neurosurgeon", "physicians", 35),
    ("", "Medic combustiolog", "Врач-комбустиолог", "Burns surgeon", "physicians", 35),
    ("", "Medic radiolog-imagist", "Врач-рентгенолог", "Radiologist", "physicians", 30),
    ("", "Medic de laborator", "Врач-лаборант", "Laboratory physician", "physicians", 35),
    ("", "Medic reabilitolog", "Врач-реабилитолог", "Rehabilitation physician", "physicians", 35),
    ("", "Medic de gardă", "Дежурный врач", "On-call physician", "physicians", 35),
    ("", "Medic rezident", "Врач-резидент", "Resident physician", "physicians", 35),
    ("", "Farmacist", "Фармацевт", "Pharmacist", "pharmacists", 40),
    ("", "Asistent medical de secție", "Палатная медсестра", "Ward nurse", "nurses", 35),
    ("", "Asistent medical anestezist", "Медсестра-анестезист", "Nurse anaesthetist", "nurses", 35),
    ("", "Asistent medical de operație", "Операционная медсестра", "Theatre nurse", "nurses", 35),
    ("", "Asistent medical de proceduri", "Процедурная медсестра", "Procedure nurse", "nurses", 35),
    ("", "Laborant radiolog", "Рентгенолаборант", "Radiology technician", "nurses", 30),
    ("", "Infermieră de operație", "Операционная санитарка", "Theatre aide", "junior", 40),
    ("", "Contabil", "Бухгалтер", "Accountant", "admin", 40),
    ("", "Economist", "Экономист", "Economist", "admin", 40),
    ("", "Specialist resurse umane", "Специалист по кадрам", "HR specialist", "admin", 40),
    ("", "Jurist", "Юрист", "Lawyer", "admin", 40),
    ("", "Inginer", "Инженер", "Engineer", "admin", 40),
    ("", "Bucătar", "Повар", "Cook", "admin", 40),
    ("", "Îngrijitor încăperi", "Уборщик помещений", "Cleaner", "admin", 40),
]

# (cod, RO, RU, EN, tip)
SPECIALTIES = [
    ("", "Ortopedie și traumatologie", "Ортопедия и травматология", "Orthopaedics and traumatology", "medical"),
    ("", "Anesteziologie și reanimatologie", "Анестезиология и реаниматология", "Anaesthesiology and intensive care", "medical"),
    ("", "Chirurgie", "Хирургия", "Surgery", "medical"),
    ("", "Neurochirurgie", "Нейрохирургия", "Neurosurgery", "medical"),
    ("", "Combustiologie", "Комбустиология", "Burns care", "medical"),
    ("", "Radiologie și imagistică", "Радиология и визуализация", "Radiology and imaging", "medical"),
    ("", "Medicină de laborator", "Лабораторная медицина", "Laboratory medicine", "medical"),
    ("", "Reabilitare medicală și medicină fizică", "Медицинская реабилитация и физическая медицина",
     "Physical and rehabilitation medicine", "medical"),
    ("", "Medicină internă", "Внутренние болезни", "Internal medicine", "medical"),
    ("", "Neurologie", "Неврология", "Neurology", "medical"),
    ("", "Cardiologie", "Кардиология", "Cardiology", "medical"),
    ("", "Medicină de urgență", "Неотложная медицина", "Emergency medicine", "medical"),
    ("", "Medicină de familie", "Семейная медицина", "Family medicine", "medical"),
    ("", "Sănătate publică și management", "Общественное здоровье и менеджмент", "Public health and management", "medical"),
    ("", "Farmacie", "Фармация", "Pharmacy", "pharmacy"),
    ("", "Asistent medical generalist", "Медсестра общего профиля", "General nurse", "nursing"),
    ("", "Asistent medical în anestezie", "Медсестра-анестезист", "Anaesthesia nursing", "nursing"),
    ("", "Laborant", "Лаборант", "Laboratory technician", "nursing"),
    ("", "Fizioterapie", "Физиотерапия", "Physiotherapy", "nursing"),
    ("", "Radiologie (studii medii)", "Рентгенология (среднее образование)", "Radiography", "nursing"),
]

# tip: [(cod, RO, RU, EN, extra)]
DICTS = {
    "qualification": [
        ("none", "Fără categorie", "Без категории", "No category", {}),
        ("second", "Categoria a doua", "Вторая категория", "Second category", {}),
        ("first", "Categoria întâi", "Первая категория", "First category", {}),
        ("superior", "Categoria superioară", "Высшая категория", "Higher category", {}),
    ],
    "degree": [
        ("dr", "Doctor în științe medicale", "Доктор медицинских наук", "PhD in medical sciences", {}),
        ("dr_hab", "Doctor habilitat în științe medicale", "Доктор хабилитат медицинских наук", "Habilitated doctor", {}),
    ],
    "title": [
        ("conf", "Conferențiar universitar", "Доцент", "Associate professor", {}),
        ("prof", "Profesor universitar", "Профессор", "Professor", {}),
    ],
    "education": [  # din enumerarea 1C „Studii”, completată cu rezidențiatul
        ("primary", "Primare", "Начальное", "Primary", {}),
        ("secondary", "Medii", "Среднее", "Secondary", {}),
        ("vocational", "Medii de specialitate", "Среднее специальное", "Vocational (post-secondary)", {}),
        ("higher", "Superioare", "Высшее", "Higher", {}),
        ("residency", "Rezidențiat", "Резидентура", "Residency", {}),
        ("postgraduate", "Postuniversitare", "Послевузовское", "Postgraduate", {}),
        ("doctorate", "Doctorat", "Докторантура", "Doctorate", {}),
    ],
    "education_form": [  # din enumerarea 1C „FormaDeInvatamint”
        ("full", "La zi", "Дневная", "Full-time", {}),
        ("reduced", "Frecvență redusă", "Сокращённое посещение", "Reduced attendance", {}),
        ("distance", "Fără frecvență", "Заочная", "Distance", {}),
        ("evening", "Serală", "Вечерняя", "Evening", {}),
    ],
    "document": [
        ("id_card", "Buletin de identitate", "Удостоверение личности", "Identity card", {"has_expiry": True}),
        ("passport", "Pașaport", "Паспорт", "Passport", {"has_expiry": True}),
        ("residence", "Permis de ședere", "Вид на жительство", "Residence permit", {"has_expiry": True}),
        ("diploma", "Diplomă de studii", "Диплом об образовании", "Diploma", {}),
        ("residency_cert", "Certificat de rezidențiat / secundariat", "Сертификат резидентуры", "Residency certificate", {}),
        ("category_cert", "Certificat de categorie de calificare", "Сертификат квалификационной категории",
         "Qualification category certificate", {"has_expiry": True}),
        ("cme_cert", "Certificat de educație medicală continuă", "Сертификат НМО", "CME certificate", {}),
        ("medical_book", "Carnet medical", "Медицинская книжка", "Health record book", {"has_expiry": True}),
        ("military_book", "Livret militar", "Военный билет", "Military record book", {}),
        ("recruit_cert", "Certificat de recrutare", "Приписное свидетельство", "Recruitment certificate", {}),
        ("criminal_record", "Certificat de cazier judiciar", "Справка о несудимости", "Criminal record certificate",
         {"has_expiry": True}),
    ],
    "family": [  # din enumerarea 1C „Membrul”
        ("husband", "Soț", "Муж", "Husband", {}), ("wife", "Soție", "Жена", "Wife", {}),
        ("son", "Fiu", "Сын", "Son", {}), ("daughter", "Fiică", "Дочь", "Daughter", {}),
        ("mother", "Mamă", "Мать", "Mother", {}), ("father", "Tată", "Отец", "Father", {}),
    ],
    "marital": [
        ("married", "Căsătorit(ă)", "Женат / замужем", "Married", {}),
        ("single", "Necăsătorit(ă)", "Холост / не замужем", "Single", {}),
        ("divorced", "Divorțat(ă)", "Разведён(а)", "Divorced", {}),
        ("widowed", "Văduv(ă)", "Вдовец / вдова", "Widowed", {}),
    ],
    "nationality": [
        ("md", "Moldovean", "Молдаванин", "Moldovan", {}), ("ro", "Român", "Румын", "Romanian", {}),
        ("ua", "Ucrainean", "Украинец", "Ukrainian", {}), ("ru", "Rus", "Русский", "Russian", {}),
        ("gag", "Găgăuz", "Гагауз", "Gagauz", {}), ("bg", "Bulgar", "Болгарин", "Bulgarian", {}),
        ("other", "Altă naționalitate", "Другая", "Other", {}),
    ],
    "termination": [
        ("resignation", "Demisie", "По собственному желанию", "Resignation", {"legal_basis": "CM-85"}),
        ("agreement", "Acordul părților", "По соглашению сторон", "Mutual agreement", {}),
        ("term_end", "Expirarea termenului contractului", "Истечение срока договора", "End of fixed term", {}),
        ("staff_cut", "Reducerea numărului sau a statelor de personal", "Сокращение штата",
         "Staff reduction", {"legal_basis": "CM-86"}),
        ("unfit", "Necorespunderea funcției deținute", "Несоответствие занимаемой должности", "Unsuitability", {"legal_basis": "CM-86"}),
        ("disciplinary", "Concediere disciplinară", "Дисциплинарное увольнение", "Disciplinary dismissal", {"legal_basis": "CM-86"}),
        ("retirement", "Pensionare", "Выход на пенсию", "Retirement", {}),
        ("death", "Decesul salariatului", "Смерть работника", "Death of employee", {"legal_basis": "CM-82"}),
        ("transfer_out", "Transfer la altă unitate", "Перевод в другую организацию", "Transfer to another employer", {}),
    ],
    "sanction": [  # Codul muncii, art. 206
        ("warning", "Avertisment", "Замечание", "Warning", {}),
        ("reprimand", "Mustrare", "Выговор", "Reprimand", {}),
        ("severe", "Mustrare aspră", "Строгий выговор", "Severe reprimand", {}),
        ("dismissal", "Concediere", "Увольнение", "Dismissal", {}),
    ],
    "incentive": [
        ("bonus", "Premiu unic", "Единовременная премия", "One-off bonus", {}),
        ("thanks", "Mulțumire", "Благодарность", "Letter of thanks", {}),
        ("diploma", "Diplomă de onoare", "Почётная грамота", "Certificate of honour", {}),
        ("aid", "Ajutor material", "Материальная помощь", "Financial aid", {}),
    ],
    "vaccine": [  # extra: months — revaccinarea (0 = fără), required — obligatoriu pentru personalul medical
        ("hepatitis_b", "Hepatita virală B", "Вирусный гепатит B", "Hepatitis B", {"months": 0, "required": True}),
        ("influenza", "Gripa sezonieră", "Сезонный грипп", "Seasonal influenza", {"months": 12}),
        ("covid19", "COVID-19", "COVID-19", "COVID-19", {"months": 12}),
        ("dt", "Difterie-tetanos (dT)", "Дифтерия-столбняк (АДС-м)", "Diphtheria-tetanus (dT)", {"months": 120}),
        ("mmr", "Rujeolă-oreion-rubeolă (ROR)", "Корь-паротит-краснуха (КПК)", "Measles-mumps-rubella (MMR)", {"months": 0}),
        ("other", "Alt vaccin", "Другая вакцина", "Other vaccine", {"months": 0}),
    ],
    "employment": [  # din enumerarea 1C „TipAngajare”, completată cu suplinirea
        ("main", "De bază", "Основное место работы", "Main job", {}),
        ("main_student", "De bază (student)", "Основное (студент)", "Main job (student)", {}),
        ("external", "Cumul extern", "Внешнее совместительство", "External second job", {}),
        ("internal", "Cumul intern", "Внутреннее совместительство", "Internal second job", {}),
        ("resident", "Rezident", "Резидент", "Resident", {}),
        ("substitute", "Suplinire temporară", "Временное замещение", "Temporary substitution", {}),
    ],
    "military_group": [  # din enumerarea 1C „GrupaEvidentei”
        ("army", "Forțele Armate", "Вооружённые силы", "Armed Forces", {}),
        ("border", "Poliția de Frontieră (grăniceri)", "Пограничная полиция", "Border Police", {}),
        ("carabinieri", "Carabinieri", "Карабинеры", "Carabinieri", {}),
    ],
    "checklist": [  # din catalogul 1C „CecList” (angajare — eliberare), adaptat pentru spital
        ("contract", "CIM semnat și înregistrat", "Трудовой договор подписан", "Contract signed", {}),
        ("job_desc", "Fișa postului semnată", "Должностная инструкция подписана", "Job description signed", {}),
        ("ssm", "Instructajul SSM și PSI", "Инструктаж по охране труда и ПБ", "Health and safety briefing", {}),
        ("medical_book", "Carnetul medical / examenul la angajare", "Медкнижка / медосмотр", "Medical check at hiring", {}),
        ("gdpr", "Declarația privind datele cu caracter personal", "Согласие на обработку персональных данных",
         "Personal data declaration", {}),
        ("badge", "Ecusonul / legitimația", "Бейдж / удостоверение", "Badge / ID card", {"returnable": True}),
        ("uniform", "Uniforma (halat, costum)", "Униформа (халат, костюм)", "Uniform", {"returnable": True}),
        ("locker", "Cheia dulapului", "Ключ от шкафчика", "Locker key", {"returnable": True}),
        ("system_access", "Acces în sistemul informațional (SIA AMP)", "Доступ в информационную систему",
         "Information system access", {"returnable": True}),
    ],
    "military_rank": [
        ("soldier", "Soldat", "Солдат", "Private", {}), ("corporal", "Caporal", "Капрал", "Corporal", {}),
        ("sergeant", "Sergent", "Сержант", "Sergeant", {}), ("lieutenant", "Locotenent", "Лейтенант", "Lieutenant", {}),
        ("captain", "Căpitan", "Капитан", "Captain", {}), ("major", "Maior", "Майор", "Major", {}),
        ("ltcol", "Locotenent-colonel", "Подполковник", "Lieutenant colonel", {}),
        ("colonel", "Colonel", "Полковник", "Colonel", {}),
    ],
}

# Codul muncii nr. 154/2003 — articolele de bază. Textul din ordin se poate scrie / corecta din interfață.
# (cod, articol, alineat, literă, RO, RU, EN)
CM = "Codul muncii nr. 154/2003"
LEGAL_BASES = [
    ("CM-55", "55", "", "", "Contractul individual de muncă pe durată determinată", "Срочный трудовой договор", "Fixed-term contract"),
    ("CM-60", "60", "", "", "Perioada de probă", "Испытательный срок", "Probation period"),
    ("CM-65", "65", "", "", "Ordinul de angajare", "Приказ о приёме на работу", "Hiring order"),
    ("CM-68", "68", "", "", "Modificarea contractului individual de muncă", "Изменение трудового договора", "Amendment of the contract"),
    ("CM-74", "74", "", "", "Transferul la o altă muncă", "Перевод на другую работу", "Transfer to another job"),
    ("CM-76", "76", "", "", "Suspendarea CIM în circumstanțe ce nu depind de voința părților",
     "Приостановление договора по не зависящим от сторон обстоятельствам", "Suspension beyond the parties' control"),
    ("CM-77", "77", "", "", "Suspendarea CIM prin acordul părților", "Приостановление договора по соглашению сторон",
     "Suspension by agreement"),
    ("CM-78", "78", "", "", "Suspendarea CIM la inițiativa uneia dintre părți", "Приостановление договора по инициативе одной из сторон",
     "Suspension at one party's initiative"),
    ("CM-82", "82", "", "", "Încetarea CIM în circumstanțe ce nu depind de voința părților",
     "Прекращение договора по не зависящим от сторон обстоятельствам", "Termination beyond the parties' control"),
    ("CM-AGR", "", "", "", "Încetarea CIM prin acordul scris al părților", "Прекращение договора по соглашению сторон",
     "Termination by mutual agreement"),
    ("CM-85", "85", "", "", "Demisia", "Увольнение по собственному желанию", "Resignation"),
    ("CM-86", "86", "", "", "Concedierea (la inițiativa angajatorului)", "Увольнение по инициативе работодателя",
     "Dismissal by the employer"),
    ("CM-112", "112", "", "", "Concediul de odihnă anual", "Ежегодный оплачиваемый отпуск", "Annual paid leave"),
    ("CM-120", "120", "", "", "Concediul neplătit", "Отпуск без сохранения заработной платы", "Unpaid leave"),
    ("CM-121", "121", "", "", "Concediul de odihnă anual suplimentar", "Ежегодный дополнительный отпуск", "Additional annual leave"),
    ("CM-123", "123", "", "", "Concediul medical", "Отпуск по болезни", "Sick leave"),
    ("CM-124", "124", "", "", "Concediul de maternitate și concediul parțial plătit pentru îngrijirea copilului",
     "Отпуск по беременности и родам и частично оплачиваемый отпуск по уходу за ребёнком", "Maternity and childcare leave"),
    ("CM-124-1", "124¹", "", "", "Concediul de paternitate", "Отцовский отпуск", "Paternity leave"),
    ("CM-STUDY", "", "", "", "Concediul de studii", "Учебный отпуск", "Study leave"),
    ("CM-RECALL", "", "", "", "Rechemarea din concediul de odihnă", "Отзыв из отпуска", "Recall from leave"),
    ("CM-OVERTIME", "", "", "", "Munca suplimentară și munca în zilele de repaus / sărbătoare",
     "Сверхурочная работа и работа в выходные / праздничные дни", "Overtime and work on rest days"),
    ("CM-SUBST", "", "", "", "Cumulul de funcții și suplinirea temporară", "Совмещение должностей и временное замещение",
     "Combining posts and temporary substitution"),
    ("CM-TRAVEL", "", "", "", "Delegarea în interes de serviciu", "Служебная командировка", "Business travel"),
    ("CM-206", "206", "", "", "Sancțiunile disciplinare", "Дисциплинарные взыскания", "Disciplinary sanctions"),
    ("CM-INCENT", "", "", "", "Stimularea pentru muncă", "Поощрение за труд", "Rewards for work"),
    ("HG-837", "", "", "", "Salarizarea angajaților din IMSP (HG nr. 837/2016)", "Оплата труда в ПМСУ (ПП № 837/2016)",
     "Pay of public medical institutions staff (GD 837/2016)"),
    ("OMS-386", "", "", "", "Atestarea medicilor și farmaciștilor (Ordinul MS nr. 386/2018)",
     "Аттестация врачей и фармацевтов (Приказ МЗ № 386/2018)", "Attestation of physicians (MoH order 386/2018)"),
    ("OMS-100", "", "", "", "Normativele de personal medical (Ordinul MS nr. 100/2008)",
     "Нормативы медицинского персонала (Приказ МЗ № 100/2008)", "Medical staffing norms (MoH order 100/2008)"),
]
NON_CM_ACTS = {"HG-837": "HG nr. 837/2016", "OMS-386": "Ordinul MS nr. 386/2018", "OMS-100": "Ordinul MS nr. 100/2008"}

# Tipurile de ordine (PLAN.md §5.3). from_1c = exista în configurația 1C.
# (cod, RO, RU, EN, grupa, registrul, efectul, colectiv, temei, titlul în ordin, IRM19, efect salarial, din 1C)
P, L, T, G = "order_personnel", "order_leave", "order_travel", "order_general"
ORDER_TYPES = [
    # A. Raporturi de muncă
    ("hire", "Angajare", "Приём на работу", "Hiring", "A", P, "hire", False, "CM-65", "Cu privire la angajare", True, True, True),
    ("hire_transfer", "Angajare prin transfer", "Приём в порядке перевода", "Hiring by transfer", "A", P, "hire", False, "CM-65",
     "Cu privire la angajarea prin transfer", True, True, True),
    ("transfer", "Transfer la altă funcție / subdiviziune", "Перевод на другую должность / в другое подразделение",
     "Transfer to another post / department", "A", P, "change", False, "CM-74", "Cu privire la transfer", True, True, True),
    ("change_rate", "Modificarea normei de muncă", "Изменение ставки", "Change of working rate", "A", P, "change", False,
     "CM-68", "Cu privire la modificarea normei de muncă", True, True, False),
    ("change_terms", "Modificarea condițiilor CIM", "Изменение условий трудового договора", "Change of contract terms", "A", P,
     "change", False, "CM-68", "Cu privire la modificarea contractului individual de muncă", True, True, False),
    ("extend_contract", "Prelungirea CIM pe durată determinată", "Продление срочного договора", "Extension of fixed-term contract",
     "A", P, "change", False, "CM-55", "Cu privire la prelungirea contractului individual de muncă", True, False, False),
    ("substitution", "Suplinire temporară", "Временное замещение", "Temporary substitution", "A", P, "substitution", False,
     "CM-SUBST", "Cu privire la suplinirea temporară", False, True, False),
    ("combination", "Cumul de funcții / extinderea zonei de deservire", "Совмещение / расширение зоны обслуживания",
     "Combining posts", "A", P, "substitution", False, "CM-SUBST", "Cu privire la cumularea funcțiilor", False, True, False),
    ("acting", "Interimat (exercitarea temporară a funcției)", "Временное исполнение обязанностей", "Acting appointment", "A", P,
     "substitution", False, "CM-SUBST", "Cu privire la exercitarea interimatului", False, True, False),
    ("travel", "Delegare", "Командировка", "Business travel", "A", T, "travel", True, "CM-TRAVEL", "Cu privire la delegare",
     False, True, True),
    ("suspend", "Suspendarea CIM", "Приостановление трудового договора", "Suspension of contract", "A", P, "suspend", False,
     "CM-78", "Cu privire la suspendarea contractului individual de muncă", True, True, False),
    ("resume", "Reluarea activității", "Возобновление работы", "Return to work", "A", P, "resume", False, "",
     "Cu privire la reluarea activității", True, True, False),
    ("terminate", "Încetarea CIM (eliberare)", "Прекращение трудового договора (увольнение)", "Termination of contract", "A", P,
     "terminate", False, "CM-85", "Cu privire la încetarea contractului individual de muncă", True, True, True),
    ("cancel_order", "Anularea / modificarea unui ordin", "Отмена / изменение приказа", "Cancelling an order", "A", P, "cancel",
     False, "", "Cu privire la anularea ordinului", False, False, False),
    # B. Concedii
    ("leave_annual", "Concediu de odihnă anual plătit", "Ежегодный оплачиваемый отпуск", "Annual paid leave", "B", L, "leave", True,
     "CM-112", "Cu privire la acordarea concediului de odihnă anual plătit", False, True, True),
    ("leave_extra", "Concediu suplimentar plătit", "Дополнительный оплачиваемый отпуск", "Additional paid leave", "B", L, "leave",
     True, "CM-121", "Cu privire la acordarea concediului suplimentar plătit", False, True, True),
    ("leave_unpaid", "Concediu neplătit", "Отпуск без сохранения заработной платы", "Unpaid leave", "B", L, "leave", False, "CM-120",
     "Cu privire la acordarea concediului neplătit", False, True, True),
    ("leave_maternity", "Concediu de maternitate", "Отпуск по беременности и родам", "Maternity leave", "B", L, "leave", False,
     "CM-124", "Cu privire la acordarea concediului de maternitate", True, True, True),
    ("leave_paternity", "Concediu paternal", "Отцовский отпуск", "Paternity leave", "B", L, "leave", False, "CM-124-1",
     "Cu privire la acordarea concediului paternal", True, True, False),
    ("leave_childcare", "Concediu parțial plătit pentru îngrijirea copilului", "Частично оплачиваемый отпуск по уходу за ребёнком",
     "Partly paid childcare leave", "B", L, "leave", False, "CM-124",
     "Cu privire la acordarea concediului parțial plătit pentru îngrijirea copilului", True, True, True),
    ("leave_childcare_unpaid", "Concediu suplimentar neplătit pentru îngrijirea copilului",
     "Дополнительный неоплачиваемый отпуск по уходу за ребёнком", "Additional unpaid childcare leave", "B", L, "leave", False,
     "CM-124", "Cu privire la acordarea concediului suplimentar neplătit pentru îngrijirea copilului", True, True, False),
    ("leave_study", "Concediu de studii", "Учебный отпуск", "Study leave", "B", L, "leave", False, "CM-STUDY",
     "Cu privire la acordarea concediului de studii", False, True, True),
    ("days_off_paid", "Zile libere plătite (căsătorie, naștere, deces)", "Оплачиваемые свободные дни", "Paid days off", "B", L,
     "leave", False, "", "Cu privire la acordarea zilelor libere plătite", False, True, False),
    ("leave_recall", "Rechemare din concediu", "Отзыв из отпуска", "Recall from leave", "B", L, "leave_recall", False, "CM-RECALL",
     "Cu privire la rechemarea din concediu", False, True, True),
    ("leave_postpone", "Amânarea / transferul concediului", "Перенос отпуска", "Postponing leave", "B", L, "leave_recall", False,
     "", "Cu privire la amânarea concediului", False, False, False),
    ("leave_compensation", "Compensarea concediului nefolosit", "Компенсация неиспользованного отпуска",
     "Compensation for unused leave", "B", L, "leave", False, "", "Cu privire la compensarea concediului nefolosit", False, True, False),
    # C. Timp de muncă
    ("schedule", "Aprobarea / modificarea graficului de lucru", "Утверждение / изменение графика работы",
     "Approving the work schedule", "C", G, "worktime", True, "", "Cu privire la aprobarea graficului de lucru", False, False, True),
    ("rest_day_work", "Lucru în zi de odihnă / sărbătoare", "Работа в выходной / праздничный день", "Work on rest day / holiday",
     "C", P, "worktime", True, "CM-OVERTIME", "Cu privire la antrenarea la muncă în zi de odihnă", False, True, True),
    ("overtime", "Ore suplimentare", "Сверхурочная работа", "Overtime", "C", P, "worktime", True, "CM-OVERTIME",
     "Cu privire la munca suplimentară", False, True, False),
    ("hours_change", "Modificarea orelor de lucru (program parțial, zi redusă)", "Изменение рабочего времени",
     "Change of working hours", "C", P, "worktime", False, "CM-68", "Cu privire la modificarea orelor de lucru", False, True, True),
    ("on_call", "Gărzi (graficul lunar)", "Дежурства (месячный график)", "On-call duty (monthly roster)", "C", G, "worktime", True,
     "", "Cu privire la aprobarea graficului gărzilor", False, True, False),
    # D. Salarizare și stimulare
    ("salary_set", "Stabilirea / modificarea salariului de funcție", "Установление / изменение оклада", "Setting the base salary",
     "D", P, "salary", True, "HG-837", "Cu privire la stabilirea salariului de funcție", False, True, True),
    ("allowance", "Stabilirea sporurilor", "Установление надбавок", "Setting allowances", "D", P, "salary", True, "HG-837",
     "Cu privire la stabilirea sporurilor la salariu", False, True, False),
    ("bonus", "Premiere", "Премирование", "Bonus", "D", P, "incentive", True, "CM-INCENT", "Cu privire la premiere", False, True, True),
    ("material_aid", "Ajutor material", "Материальная помощь", "Financial aid", "D", P, "incentive", True, "",
     "Cu privire la acordarea ajutorului material", False, True, False),
    ("indexation", "Indexarea / majorarea salariilor", "Индексация / повышение зарплат", "Salary indexation", "D", G, "salary", True,
     "HG-837", "Cu privire la majorarea salariilor", False, True, False),
    # E. Disciplină
    ("sanction", "Sancțiune disciplinară", "Дисциплинарное взыскание", "Disciplinary sanction", "E", P, "sanction", False, "CM-206",
     "Cu privire la aplicarea sancțiunii disciplinare", False, False, False),
    ("sanction_lift", "Ridicarea sancțiunii disciplinare", "Снятие дисциплинарного взыскания", "Lifting a sanction", "E", P,
     "sanction", False, "CM-206", "Cu privire la ridicarea sancțiunii disciplinare", False, False, False),
    # F. Profesional
    ("training", "Trimitere la perfecționare / EMC", "Направление на повышение квалификации", "Sending to training / CME", "F", T,
     "qualification", True, "", "Cu privire la trimiterea la cursuri de perfecționare", False, True, False),
    ("attestation", "Trimitere la atestare", "Направление на аттестацию", "Sending to attestation", "F", P, "qualification", True,
     "OMS-386", "Cu privire la trimiterea la atestare", False, False, False),
    ("category_award", "Conferirea / confirmarea categoriei de calificare", "Присвоение / подтверждение категории",
     "Award of qualification category", "F", P, "qualification", True, "OMS-386",
     "Cu privire la conferirea categoriei de calificare", False, True, False),
    ("medical_exam", "Examenul medical periodic", "Периодический медицинский осмотр", "Periodic medical examination", "F", G,
     "none", True, "", "Cu privire la efectuarea examenului medical periodic", False, False, False),
    # G. Organizatorice
    ("staff_list", "Aprobarea / modificarea statelor de personal", "Утверждение / изменение штатного расписания",
     "Approving the staff list", "G", G, "staff_list", False, "OMS-100", "Cu privire la statele de personal", False, False, False),
    ("leave_schedule", "Aprobarea graficului concediilor", "Утверждение графика отпусков", "Approving the leave schedule", "G", G,
     "none", False, "CM-112", "Cu privire la aprobarea graficului concediilor de odihnă", False, False, False),
    ("appoint_responsible", "Numirea responsabililor / constituirea comisiilor", "Назначение ответственных / создание комиссий",
     "Appointing persons in charge / committees", "G", G, "none", True, "", "Cu privire la desemnarea responsabililor", False, False,
     False),
    ("free_text", "Ordin liber („Cu privire la …”)", "Произвольный приказ", "Free-form order", "G", G, "none", True, "",
     "Cu privire la", False, False, False),
]


def run():
    for i, (code, ro, ru, en, cat, hours) in enumerate(OCCUPATIONS):
        lookup = {"code": code} if code else {"code": "", "name_ro": ro}
        Occupation.objects.get_or_create(**lookup, defaults={
            "name_ro": ro, "name_ru": ru, "name_en": en, "category": cat, "weekly_hours": hours, "sort": (i + 1) * 10,
            "notes": "" if code else "Cod CORM de completat din clasificatorul CORM 006-21.",
        })
    for i, (code, ro, ru, en, kind) in enumerate(SPECIALTIES):
        Specialty.objects.get_or_create(name_ro=ro, defaults={"code": code, "name_ru": ru, "name_en": en, "kind": kind,
                                                              "sort": (i + 1) * 10})
    for kind, items in DICTS.items():
        for i, (code, ro, ru, en, extra) in enumerate(items):
            DictItem.objects.get_or_create(kind=kind, code=code, defaults={
                "name_ro": ro, "name_ru": ru, "name_en": en, "extra": extra, "sort": (i + 1) * 10})
    bases = {}
    for i, (code, art, par, let, ro, ru, en) in enumerate(LEGAL_BASES):
        bases[code], _ = LegalBasis.objects.get_or_create(code=code, defaults={
            "act": NON_CM_ACTS.get(code, CM), "article": art, "paragraph": par, "letter": let,
            "name_ro": ro, "name_ru": ru, "name_en": en, "sort": (i + 1) * 10})
    for i, row in enumerate(ORDER_TYPES):
        code, ro, ru, en, group, register, effect, collective, basis, title, irm19, payroll, from_1c = row
        ot, created = OrderType.objects.get_or_create(code=code, defaults={
            "name_ro": ro, "name_ru": ru, "name_en": en, "group": group, "register": register, "effect": effect,
            "collective": collective, "title_ro": title, "report_irm19": irm19,
            "payroll_effect": payroll, "from_1c": from_1c, "needs_employee": effect not in ("staff_list",),
            "sort": (i + 1) * 10,
        })
        if created and bases.get(basis):
            ot.legal_bases.set([bases[basis]])
