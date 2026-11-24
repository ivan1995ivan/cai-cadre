"""Datele inițiale ale clasificatoarelor. Idempotente: adaugă doar ce lipsește și nu schimbă ce a modificat clientul.

Surse: Clasificatorul ocupațiilor din Republica Moldova CORM 006-2021 (Ordinul MMPS nr. 11 din 12.11.2021, MO 2022 nr. 6-16
art. 23) pentru codurile și grupele majore ale funcțiilor; Codul muncii nr. 154/2003 (redacția 2026, cu Legea 193/2025 și
Legea 156/2025) pentru temeiurile legale; configurația 1C „Cadre” (Personal.cf) pentru enumerări. Funcțiile fără cod nu au
o denumire identică în CORM — codul se alege la instalare din clasificator (importul din Excel al CORM 006-2021).
Atenție: Ordinul MMPS nr. 212/2025 (în vigoare din 04.07.2026) a redenumit și a mutat unele ocupații — codurile se verifică
cu textul consolidat al CORM înainte de raportare.
"""
from .models import STAFF_CATEGORY, DictItem, LegalBasis, Occupation, OrderType, Specialty

# Grupele majore CORM 006-2021 → categoriile de personal (codul = cifra grupei, prima cifră a codului funcției)
STAFF_CATEGORIES = [
    ("1", "Conducători și funcționari superiori", "Руководители и высшие должностные лица", "Managers"),
    ("2", "Specialiști în diverse domenii de activitate", "Специалисты в различных областях деятельности", "Professionals"),
    ("3", "Tehnicieni, maiștri și alți specialiști asimilați", "Техники, мастера и приравненные к ним специалисты",
     "Technicians and associate professionals"),
    ("4", "Funcționari administrativi", "Административные служащие", "Clerical support workers"),
    ("5", "Lucrători din domeniul serviciilor și comerțului", "Работники сферы обслуживания и торговли",
     "Service and sales workers"),
    ("6", "Lucrători calificați în agricultură, silvicultură, acvacultură și pescuit",
     "Квалифицированные работники сельского, лесного, рыбного хозяйства", "Skilled agricultural, forestry and fishery workers"),
    ("7", "Muncitori calificați și lucrători din domeniul artizanal", "Квалифицированные рабочие и ремесленники",
     "Craft and related trades workers"),
    ("8", "Operatori și asamblori de mașini și instalații", "Операторы и сборщики машин и установок",
     "Plant and machine operators, and assemblers"),
    ("9", "Muncitori necalificați", "Неквалифицированные рабочие", "Elementary occupations"),
]

# (cod CORM 006-2021, RO, RU, EN, grupa CORM — doar pentru funcțiile fără cod, ore/săpt.)
# Codurile sunt verificate în textul oficial al Ordinului MMPS nr. 11/2021; denumirile — forma de masculin a celor oficiale.
OCCUPATIONS = [
    # 1 — conducători
    ("", "Administrator (societate comercială)", "Администратор (коммерческое общество)", "Company administrator", "1", 40),
    ("112012", "Director al întreprinderii", "Директор предприятия", "Company director", "1", 40),
    ("", "Director adjunct", "Заместитель директора", "Deputy director", "1", 40),
    ("121103", "Contabil-șef", "Главный бухгалтер", "Chief accountant", "1", 40),
    # 2 — specialiști
    ("241106", "Contabil", "Бухгалтер", "Accountant", "2", 40),
    ("263107", "Economist", "Экономист", "Economist", "2", 40),
    ("261919", "Jurist", "Юрист", "Lawyer", "2", 40),
    ("242318", "Specialist în resurse umane", "Специалист по человеческим ресурсам", "Human resources specialist", "2", 40),
    ("243302", "Manager în vânzări", "Менеджер по продажам", "Sales manager", "2", 40),
    ("251207", "Programator", "Программист", "Programmer", "2", 40),
    ("252302", "Administrator rețea de calculatoare", "Администратор компьютерной сети", "Network administrator", "2", 40),
    ("214122", "Inginer în industrie și producție", "Инженер в промышленности и производстве", "Industrial and production engineer",
     "2", 40),
    ("214114", "Inginer tehnolog în industrie și producție", "Инженер-технолог в промышленности и производстве",
     "Process engineer", "2", 40),
    ("214932", "Inginer securitate și sănătate în muncă", "Инженер по охране труда", "Occupational safety and health engineer",
     "2", 40),
    # 3 — tehnicieni, maiștri
    ("312221", "Maistru în industria prelucrătoare", "Мастер в обрабатывающей промышленности", "Manufacturing supervisor", "3", 40),
    ("332202", "Agent de vânzări", "Торговый агент", "Sales agent", "3", 40),
    ("332304", "Merceolog", "Товаровед", "Merchandise specialist", "3", 40),
    # 4 — funcționari administrativi
    ("412002", "Secretar", "Секретарь", "Secretary", "4", 40),
    ("413202", "Operator introducere, validare și prelucrare date", "Оператор ввода, проверки и обработки данных",
     "Data entry operator", "4", 40),
    ("413203", "Operator la calculator", "Оператор ЭВМ", "Computer operator", "4", 40),
    ("422202", "Operator call center", "Оператор call-центра", "Call centre operator", "4", 40),
    ("432103", "Magaziner", "Кладовщик", "Storekeeper", "4", 40),
    ("432202", "Dispecer în programare și supraveghere a producției", "Диспетчер по планированию и контролю производства",
     "Production dispatcher", "4", 40),
    ("432313", "Dispecer în transporturi", "Диспетчер на транспорте", "Transport dispatcher", "4", 40),
    ("432314", "Expeditor-logistician în transporturi", "Экспедитор-логист на транспорте", "Freight forwarder (logistics)",
     "4", 40),
    # 5 — servicii și comerț
    ("512001", "Bucătar", "Повар", "Cook", "5", 40),
    ("522103", "Vânzător în magazine", "Продавец в магазине", "Shop sales assistant", "5", 40),
    ("523001", "Casier", "Кассир", "Cashier", "5", 40),
    # 7 — muncitori calificați
    ("721212", "Sudor", "Сварщик", "Welder", "7", 40),
    ("723109", "Mecanic auto", "Автомеханик", "Motor vehicle mechanic", "7", 40),
    ("723314", "Lăcătuș-reparator instalații tehnologice", "Слесарь-ремонтник технологических установок",
     "Industrial equipment repair fitter", "7", 40),
    ("741206", "Electrician echipamente electrice și energetice", "Электрик электрического и энергетического оборудования",
     "Electrical equipment electrician", "7", 40),
    ("753111", "Croitor în confecții", "Портной в швейном производстве", "Garment tailor", "7", 40),
    ("753117", "Cusător în confecții", "Швея в швейном производстве", "Sewing machinist", "7", 40),
    # 8 — operatori, conducători auto
    ("818923", "Operator la mașini și utilaje în alte ramuri", "Оператор машин и оборудования в других отраслях",
     "Machine operator", "8", 40),
    ("832201", "Conducător auto", "Водитель автомобиля", "Car driver", "8", 40),
    ("833202", "Conducător de autocamion", "Водитель грузового автомобиля", "Lorry driver", "8", 40),
    ("833102", "Conducător de autobuz / autocar", "Водитель автобуса", "Bus and coach driver", "8", 40),
    # 9 — muncitori necalificați
    ("911201", "Îngrijitor încăperi", "Уборщик помещений", "Cleaner", "9", 40),
    ("932101", "Ambalator manual", "Упаковщик (вручную)", "Hand packer", "9", 40),
    ("962202", "Muncitor auxiliar", "Подсобный рабочий", "Auxiliary worker", "9", 40),
    ("962908", "Paznic", "Сторож", "Watchman", "9", 40),
]
# Fără cod: CORM 006-2021 nu are o denumire identică. Variantele oficiale apropiate, de ales la instalare.
CODE_HINTS = {
    "Administrator (societate comercială)": "Cod CORM de ales: 112012 (director al întreprinderii), 112031 (președinte al "
                                            "societății comerciale) sau 112033 (director general, adăugat prin Ordinul MMPS 77/2022).",
    "Director adjunct": "CORM nu are cod separat: adjunctul primește codul funcției de bază (de ex. 112012) cu sufixul de "
                        "funcție derivată „01” — de verificat în instrucțiunea CORM.",
}

# (cod, RO, RU, EN, tip). Specialitățile (profesiile după diplomă) se adaugă de client, după actele de studii.
SPECIALTIES: list = []

# tip: [(cod, RO, RU, EN, extra)]
DICTS = {
    STAFF_CATEGORY: [(code, ro, ru, en, {"corm_group": code}) for code, ro, ru, en in STAFF_CATEGORIES],
    "education": [  # din enumerarea 1C „Studii”
        ("primary", "Primare", "Начальное", "Primary", {}),
        ("secondary", "Medii", "Среднее", "Secondary", {}),
        ("vocational", "Medii de specialitate", "Среднее специальное", "Vocational (post-secondary)", {}),
        ("higher", "Superioare", "Высшее", "Higher", {}),
        ("postgraduate", "Postuniversitare", "Послевузовское", "Postgraduate", {}),
        ("doctorate", "Doctorat", "Докторантура", "Doctorate", {}),
    ],
    "education_form": [  # din enumerarea 1C „FormaDeInvatamint”
        ("full", "La zi", "Дневная", "Full-time", {}),
        ("reduced", "Frecvență redusă", "Сокращённое посещение", "Reduced attendance", {}),
        ("distance", "Fără frecvență", "Заочная", "Distance", {}),
        ("evening", "Serală", "Вечерняя", "Evening", {}),
    ],
    "document": [  # actele la angajare — Codul muncii, art. 57 alin. (1); celelalte — după actele normative speciale
        ("id_card", "Buletin de identitate", "Удостоверение личности", "Identity card", {"has_expiry": True}),
        ("passport", "Pașaport", "Паспорт", "Passport", {"has_expiry": True}),
        ("residence", "Permis de ședere", "Вид на жительство", "Residence permit", {"has_expiry": True}),
        ("diploma", "Diplomă de studii", "Диплом об образовании", "Diploma", {}),
        ("qualification_cert", "Certificat de calificare", "Свидетельство о квалификации", "Qualification certificate", {}),
        ("medical_cert", "Certificat medical (aptitudinea de muncă)", "Медицинская справка (годность к работе)",
         "Medical fitness certificate", {"has_expiry": True}),
        ("driving_licence", "Permis de conducere", "Водительское удостоверение", "Driving licence", {"has_expiry": True}),
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
    "termination": [  # Codul muncii, art. 81–86; legal_basis — codul temeiului legal (articolul, alineatul, litera)
        ("resignation", "Demisie", "По собственному желанию", "Resignation", {"legal_basis": "CM-85"}),
        ("agreement", "Acordul scris al părților", "По письменному соглашению сторон", "Mutual written agreement",
         {"legal_basis": "CM-AGR"}),
        ("term_end", "Expirarea termenului contractului", "Истечение срока договора", "End of fixed term",
         {"legal_basis": "CM-82-F"}),
        ("probation", "Rezultatul nesatisfăcător al perioadei de probă", "Неудовлетворительный результат испытания",
         "Unsatisfactory probation", {"legal_basis": "CM-86-A"}),
        ("liquidation", "Lichidarea unității", "Ликвидация предприятия", "Liquidation of the company", {"legal_basis": "CM-86-B"}),
        ("staff_cut", "Reducerea numărului sau a statelor de personal", "Сокращение численности или штата",
         "Staff reduction", {"legal_basis": "CM-86-C"}),
        ("unfit", "Necorespunderea funcției din motive de sănătate", "Несоответствие должности по состоянию здоровья",
         "Unfitness for the post on health grounds", {"legal_basis": "CM-86-D"}),
        ("disciplinary", "Încălcarea repetată a obligațiilor de muncă", "Неоднократное нарушение трудовых обязанностей",
         "Repeated breach of duties", {"legal_basis": "CM-86-G"}),
        ("absence", "Absența fără motive întemeiate (4 ore la rând)", "Прогул (4 часа подряд)", "Unjustified absence",
         {"legal_basis": "CM-86-H"}),
        ("drunk", "Prezența la muncă în stare de ebrietate", "Появление на работе в нетрезвом состоянии",
         "Intoxication at work", {"legal_basis": "CM-86-I"}),
        ("serious_breach", "Încălcarea gravă a obligațiilor de muncă", "Грубое нарушение трудовых обязанностей",
         "Serious breach of duties", {"legal_basis": "CM-86-P"}),
        ("retirement", "Pensionare", "Выход на пенсию", "Retirement", {}),
        ("death", "Decesul salariatului", "Смерть работника", "Death of employee", {"legal_basis": "CM-82-A"}),
        ("transfer_out", "Transfer la altă unitate", "Перевод в другую организацию", "Transfer to another employer",
         {"legal_basis": "CM-86-U"}),
    ],
    "sanction": [  # Codul muncii, art. 206
        ("warning", "Avertisment", "Замечание", "Warning", {}),
        ("reprimand", "Mustrare", "Выговор", "Reprimand", {}),
        ("severe", "Mustrare aspră", "Строгий выговор", "Severe reprimand", {}),
        ("dismissal", "Concediere", "Увольнение", "Dismissal", {}),
    ],
    "incentive": [  # Codul muncii, art. 203
        ("bonus", "Premiu unic", "Единовременная премия", "One-off bonus", {}),
        ("thanks", "Mulțumire", "Благодарность", "Letter of thanks", {}),
        ("diploma", "Diplomă de onoare", "Почётная грамота", "Certificate of honour", {}),
        ("aid", "Ajutor material", "Материальная помощь", "Financial aid", {}),
    ],
    "employment": [  # din enumerarea 1C „TipAngajare”, completată cu suplinirea
        ("main", "De bază", "Основное место работы", "Main job", {}),
        ("main_student", "De bază (student)", "Основное (студент)", "Main job (student)", {}),
        ("external", "Cumul extern", "Внешнее совместительство", "External second job", {}),
        ("internal", "Cumul intern", "Внутреннее совместительство", "Internal second job", {}),
        ("substitute", "Suplinire temporară", "Временное замещение", "Temporary substitution", {}),
    ],
    "military_group": [  # din enumerarea 1C „GrupaEvidentei”
        ("army", "Forțele Armate", "Вооружённые силы", "Armed Forces", {}),
        ("border", "Poliția de Frontieră (grăniceri)", "Пограничная полиция", "Border Police", {}),
        ("carabinieri", "Carabinieri", "Карабинеры", "Carabinieri", {}),
    ],
    "checklist": [  # angajarea — Codul muncii, art. 57 (actele), 58 (CIM în scris), Legea 186/2008 (SSM); eliberarea — ce se predă
        ("contract", "CIM semnat în două exemplare (CM art. 58)", "Трудовой договор подписан в двух экземплярах",
         "Employment contract signed (two copies)", {}),
        ("id_doc", "Actul de identitate (CM art. 57 alin. (1) lit. a))", "Документ, удостоверяющий личность",
         "Identity document", {}),
        ("diploma", "Diploma / certificatul de calificare — pentru munca ce cere cunoștințe speciale (art. 57 lit. d))",
         "Диплом / свидетельство о квалификации", "Diploma / qualification certificate", {}),
        ("medical_cert", "Certificatul medical — în cazurile prevăzute de lege (art. 57 lit. e))", "Медицинская справка",
         "Medical certificate (where required by law)", {}),
        ("declaration", "Declarația pe propria răspundere (art. 57 lit. f))", "Декларация под личную ответственность",
         "Sworn statement", {}),
        ("job_desc", "Fișa postului semnată", "Должностная инструкция подписана", "Job description signed", {}),
        ("ssm", "Instructajul SSM și PSI la angajare (Legea 186/2008)", "Вводный инструктаж по охране труда и ПБ",
         "Health and safety induction", {}),
        ("gdpr", "Informarea privind prelucrarea datelor cu caracter personal (Legea 195/2024)",
         "Информирование об обработке персональных данных", "Personal data processing notice", {}),
        ("badge", "Ecusonul / legitimația", "Бейдж / удостоверение", "Badge / ID card", {"returnable": True}),
        ("ppe", "Echipamentul individual de protecție / uniforma", "Средства индивидуальной защиты / униформа",
         "Personal protective equipment / uniform", {"returnable": True}),
        ("locker", "Cheia dulapului", "Ключ от шкафчика", "Locker key", {"returnable": True}),
        ("system_access", "Accesul la sistemele informatice", "Доступ к информационным системам",
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

# Codul muncii nr. 154/2003 (redacția 2026) — articolele de bază. Textul din ordin se poate scrie / corecta din interfață.
# (cod, articol, alineat, literă, RO, RU, EN)
CM = "Codul muncii nr. 154/2003"
LEGAL_BASES = [
    ("CM-55", "55", "", "", "Contractul individual de muncă pe durată determinată", "Срочный трудовой договор", "Fixed-term contract"),
    ("CM-57", "57", "", "", "Actele prezentate la încheierea contractului individual de muncă",
     "Документы, предъявляемые при заключении трудового договора", "Documents required at hiring"),
    ("CM-60", "60", "", "", "Perioada de probă", "Испытательный срок", "Probation period"),
    ("CM-65", "65", "", "", "Ordinul de angajare", "Приказ о приёме на работу", "Hiring order"),
    ("CM-68", "68", "", "", "Modificarea contractului individual de muncă", "Изменение трудового договора", "Amendment of the contract"),
    ("CM-TRAVEL", "70", "", "", "Trimiterea în deplasare în interes de serviciu", "Служебная командировка", "Business travel"),
    ("CM-74", "74", "", "", "Transferul la o altă muncă", "Перевод на другую работу", "Transfer to another job"),
    ("CM-76", "76", "", "", "Suspendarea CIM în circumstanțe ce nu depind de voința părților",
     "Приостановление договора по не зависящим от сторон обстоятельствам", "Suspension beyond the parties' control"),
    ("CM-77", "77", "", "", "Suspendarea CIM prin acordul părților", "Приостановление договора по соглашению сторон",
     "Suspension by agreement"),
    ("CM-78", "78", "", "", "Suspendarea CIM la inițiativa uneia dintre părți", "Приостановление договора по инициативе одной из сторон",
     "Suspension at one party's initiative"),
    ("CM-80", "80", "", "", "Șomajul tehnic", "Технический простой (безработица)", "Technical unemployment"),
    ("CM-80-1", "80¹", "", "", "Staționarea", "Простой", "Downtime"),
    ("CM-99", "99", "", "", "Evidența globală a timpului de muncă", "Суммированный учёт рабочего времени",
     "Aggregate working time accounting"),
    ("CM-161", "161", "", "", "Salarizarea în cazul neîndeplinirii normelor de muncă",
     "Оплата труда при невыполнении норм", "Pay when output norms are not met"),
    ("CM-82", "82", "", "", "Încetarea CIM în circumstanțe ce nu depind de voința părților",
     "Прекращение договора по не зависящим от сторон обстоятельствам", "Termination beyond the parties' control"),
    ("CM-82-A", "82", "", "a", "Decesul salariatului", "Смерть работника", "Death of the employee"),
    ("CM-82-F", "82", "", "f", "Expirarea termenului contractului individual de muncă pe durată determinată",
     "Истечение срока срочного трудового договора", "Expiry of a fixed-term contract"),
    ("CM-AGR", "82¹", "", "", "Încetarea CIM prin acordul scris al părților", "Прекращение договора по письменному соглашению сторон",
     "Termination by written mutual agreement"),
    ("CM-85", "85", "", "", "Demisia", "Увольнение по собственному желанию", "Resignation"),
    ("CM-86", "86", "", "", "Concedierea (la inițiativa angajatorului)", "Увольнение по инициативе работодателя",
     "Dismissal by the employer"),
    ("CM-86-A", "86", "1", "a", "Concedierea: rezultatul nesatisfăcător al perioadei de probă",
     "Увольнение: неудовлетворительный результат испытания", "Dismissal: unsatisfactory probation"),
    ("CM-86-B", "86", "1", "b", "Concedierea: lichidarea unității", "Увольнение: ликвидация предприятия",
     "Dismissal: liquidation of the company"),
    ("CM-86-C", "86", "1", "c", "Concedierea: reducerea numărului sau a statelor de personal",
     "Увольнение: сокращение численности или штата", "Dismissal: staff reduction"),
    ("CM-86-D", "86", "1", "d", "Concedierea: necorespunderea funcției din motive de sănătate",
     "Увольнение: несоответствие должности по состоянию здоровья", "Dismissal: unfitness on health grounds"),
    ("CM-86-G", "86", "1", "g", "Concedierea: încălcarea repetată a obligațiilor de muncă",
     "Увольнение: неоднократное нарушение трудовых обязанностей", "Dismissal: repeated breach of duties"),
    ("CM-86-H", "86", "1", "h", "Concedierea: absența fără motive întemeiate", "Увольнение: прогул", "Dismissal: unjustified absence"),
    ("CM-86-I", "86", "1", "i", "Concedierea: prezența la muncă în stare de ebrietate",
     "Увольнение: появление на работе в нетрезвом состоянии", "Dismissal: intoxication at work"),
    ("CM-86-P", "86", "1", "p", "Concedierea: încălcarea gravă a obligațiilor de muncă",
     "Увольнение: грубое нарушение трудовых обязанностей", "Dismissal: serious breach of duties"),
    ("CM-86-U", "86", "1", "u", "Concedierea: transferul la altă unitate", "Увольнение: перевод на другое предприятие",
     "Termination: transfer to another employer"),
    ("CM-101", "101", "", "", "Munca în schimburi (ture)", "Сменная работа", "Shift work"),
    ("CM-OVERTIME", "104", "", "", "Munca suplimentară", "Сверхурочная работа", "Overtime"),
    ("CM-110", "110", "", "", "Munca în zilele de repaus", "Работа в выходные дни", "Work on rest days"),
    ("CM-111", "111", "", "", "Zilele de sărbătoare nelucrătoare", "Нерабочие праздничные дни", "Public holidays"),
    ("CM-112", "112", "", "", "Concediul de odihnă anual", "Ежегодный оплачиваемый отпуск", "Annual paid leave"),
    ("CM-118", "118", "", "", "Acordarea anuală a concediului de odihnă; amânarea în cazuri excepționale",
     "Ежегодное предоставление отпуска; перенос в исключительных случаях", "Annual leave; postponement in exceptional cases"),
    ("CM-120", "120", "", "", "Concediul neplătit", "Отпуск без сохранения заработной платы", "Unpaid leave"),
    ("CM-121", "121", "", "", "Concediul de odihnă anual suplimentar", "Ежегодный дополнительный отпуск", "Additional annual leave"),
    ("CM-RECALL", "122", "", "", "Rechemarea din concediul de odihnă", "Отзыв из отпуска", "Recall from leave"),
    ("CM-123", "123", "", "", "Concediul medical", "Отпуск по болезни", "Sick leave"),
    ("CM-124", "124", "", "", "Concediul de maternitate și concediul parțial plătit pentru îngrijirea copilului",
     "Отпуск по беременности и родам и частично оплачиваемый отпуск по уходу за ребёнком", "Maternity and childcare leave"),
    ("CM-124-1", "124¹", "", "", "Concediul paternal (până la 15 zile calendaristice)", "Отцовский отпуск (до 15 календарных дней)",
     "Paternity leave (up to 15 calendar days)"),
    ("CM-126", "126", "", "", "Concediul suplimentar neplătit pentru îngrijirea copilului",
     "Дополнительный неоплачиваемый отпуск по уходу за ребёнком", "Additional unpaid childcare leave"),
    ("CM-PAY", "128–139", "", "", "Salarizarea (salariul de bază, sporurile, sistemele de salarizare)",
     "Оплата труда (оклад, надбавки, системы оплаты)", "Pay (base salary, allowances, pay systems)"),
    ("CM-148", "148", "", "", "Reținerile din salariu", "Удержания из заработной платы", "Deductions from wages"),
    ("CM-SUBST", "156", "", "", "Cumularea funcțiilor și suplinirea salariaților temporar absenți",
     "Совмещение должностей и замещение временно отсутствующих работников", "Combining posts and temporary substitution"),
    ("CM-STUDY", "178", "", "", "Concediul de studii (îmbinarea muncii cu studiile)", "Учебный отпуск (совмещение работы с учёбой)",
     "Study leave"),
    ("CM-INCENT", "203", "", "", "Stimulările pentru succese în muncă", "Поощрения за успехи в работе", "Rewards for work"),
    ("CM-206", "206", "", "", "Sancțiunile disciplinare", "Дисциплинарные взыскания", "Disciplinary sanctions"),
    ("CM-211", "211", "2", "", "Ridicarea sancțiunii disciplinare înainte de termen", "Досрочное снятие дисциплинарного взыскания",
     "Early lifting of a disciplinary sanction"),
    ("CM-TRAINING", "213", "", "", "Formarea profesională a salariaților", "Профессиональная подготовка работников",
     "Vocational training of employees"),
    ("SSM-186", "", "", "", "Supravegherea sănătății lucrătorilor (examenul medical)", "Надзор за здоровьем работников (медосмотр)",
     "Workers' health surveillance (medical examination)"),
    ("REG-PAY", "", "", "", "Regulamentul de salarizare / contractul colectiv de muncă", "Положение об оплате труда / коллективный договор",
     "Pay regulation / collective agreement"),
]
NON_CM_ACTS = {"SSM-186": "Legea securității și sănătății în muncă nr. 186/2008",
               "REG-PAY": "Regulamentul de salarizare al întreprinderii"}

# Tipurile de ordine (PLAN.md §5.3). from_1c = exista în configurația 1C.
# (cod, RO, RU, EN, grupa, registrul, efectul, colectiv, temeiurile, titlul în ordin, IRM19, efect salarial, din 1C)
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
     "CM-126", "Cu privire la acordarea concediului suplimentar neplătit pentru îngrijirea copilului", True, True, False),
    ("leave_study", "Concediu de studii", "Учебный отпуск", "Study leave", "B", L, "leave", False, "CM-STUDY",
     "Cu privire la acordarea concediului de studii", False, True, True),
    ("days_off_paid", "Zile libere plătite (căsătorie, naștere, deces)", "Оплачиваемые свободные дни", "Paid days off", "B", L,
     "leave", False, "", "Cu privire la acordarea zilelor libere plătite", False, True, False),
    ("leave_recall", "Rechemare din concediu", "Отзыв из отпуска", "Recall from leave", "B", L, "leave_recall", False, "CM-RECALL",
     "Cu privire la rechemarea din concediu", False, True, True),
    ("leave_postpone", "Amânarea / transferul concediului", "Перенос отпуска", "Postponing leave", "B", L, "leave_recall", False,
     "CM-118", "Cu privire la amânarea concediului", False, False, False),
    ("leave_compensation", "Compensarea concediului nefolosit", "Компенсация неиспользованного отпуска",
     "Compensation for unused leave", "B", L, "leave", False, "", "Cu privire la compensarea concediului nefolosit", False, True, False),
    # C. Timp de muncă
    ("schedule", "Aprobarea / modificarea graficului de lucru (de ture)", "Утверждение / изменение графика работы (смен)",
     "Approving the work (shift) schedule", "C", G, "worktime", True, "CM-101", "Cu privire la aprobarea graficului de lucru",
     False, False, True),
    ("rest_day_work", "Lucru în zi de odihnă / sărbătoare", "Работа в выходной / праздничный день", "Work on rest day / holiday",
     "C", P, "worktime", True, ("CM-110", "CM-111"), "Cu privire la antrenarea la muncă în zi de odihnă", False, True, True),
    ("overtime", "Ore suplimentare", "Сверхурочная работа", "Overtime", "C", P, "worktime", True, "CM-OVERTIME",
     "Cu privire la munca suplimentară", False, True, False),
    # S5b: timpul fără producție — absența pe perioadă (pontajul: St / Șt), plătită după cauză și procent
    ("idle", "Staționare", "Простой", "Downtime", "C", P, "idle", True, "CM-80-1", "Cu privire la declararea staționării",
     False, True, False),
    ("tech_unemployment", "Șomaj tehnic", "Технический простой", "Technical unemployment", "C", P, "idle", True, "CM-80",
     "Cu privire la instituirea șomajului tehnic", False, True, False),
    ("hours_change", "Modificarea orelor de lucru (program parțial, zi redusă)", "Изменение рабочего времени",
     "Change of working hours", "C", P, "worktime", False, "CM-68", "Cu privire la modificarea orelor de lucru", False, True, True),
    # D. Salarizare și stimulare
    ("salary_set", "Stabilirea / modificarea salariului de funcție", "Установление / изменение оклада", "Setting the base salary",
     "D", P, "salary", True, ("CM-PAY", "REG-PAY"), "Cu privire la stabilirea salariului de funcție", False, True, True),
    ("allowance", "Stabilirea sporurilor", "Установление надбавок", "Setting allowances", "D", P, "salary", True,
     ("CM-PAY", "REG-PAY"), "Cu privire la stabilirea sporurilor la salariu", False, True, False),
    ("bonus", "Premiere", "Премирование", "Bonus", "D", P, "incentive", True, "CM-INCENT", "Cu privire la premiere", False, True, True),
    ("material_aid", "Ajutor material", "Материальная помощь", "Financial aid", "D", P, "incentive", True, "",
     "Cu privire la acordarea ajutorului material", False, True, False),
    ("indexation", "Indexarea / majorarea salariilor", "Индексация / повышение зарплат", "Salary indexation", "D", G, "salary", True,
     ("CM-PAY", "REG-PAY"), "Cu privire la majorarea salariilor", False, True, False),
    ("deduction", "Reținere din salariu", "Удержание из заработной платы", "Deduction from wages", "D", P, "none", False, "CM-148",
     "Cu privire la reținerea din salariu", False, True, False),
    # E. Disciplină
    ("sanction", "Sancțiune disciplinară", "Дисциплинарное взыскание", "Disciplinary sanction", "E", P, "sanction", False, "CM-206",
     "Cu privire la aplicarea sancțiunii disciplinare", False, False, False),
    ("sanction_lift", "Ridicarea sancțiunii disciplinare", "Снятие дисциплинарного взыскания", "Lifting a sanction", "E", P,
     "sanction", False, "CM-211", "Cu privire la ridicarea sancțiunii disciplinare", False, False, False),
    # F. Formare profesională și SSM
    ("training", "Trimitere la formare profesională", "Направление на профессиональное обучение", "Sending to vocational training",
     "F", T, "qualification", True, "CM-TRAINING", "Cu privire la trimiterea la formare profesională", False, True, False),
    ("medical_exam", "Examenul medical (supravegherea sănătății, SSM)", "Медицинский осмотр (охрана труда)",
     "Medical examination (health and safety)", "F", G, "none", True, "SSM-186",
     "Cu privire la efectuarea examenului medical", False, False, False),
    # G. Organizatorice
    ("staff_list", "Aprobarea / modificarea statelor de personal", "Утверждение / изменение штатного расписания",
     "Approving the staff list", "G", G, "staff_list", False, "", "Cu privire la statele de personal", False, False, False),
    ("leave_schedule", "Aprobarea graficului concediilor", "Утверждение графика отпусков", "Approving the leave schedule", "G", G,
     "none", False, "CM-112", "Cu privire la aprobarea graficului concediilor de odihnă", False, False, False),
    ("appoint_responsible", "Numirea responsabililor / constituirea comisiilor", "Назначение ответственных / создание комиссий",
     "Appointing persons in charge / committees", "G", G, "none", True, "", "Cu privire la desemnarea responsabililor", False, False,
     False),
    ("free_text", "Ordin liber („Cu privire la …”)", "Произвольный приказ", "Free-form order", "G", G, "none", True, "",
     "Cu privire la", False, False, False),
]


def run():
    for kind, items in DICTS.items():
        for i, (code, ro, ru, en, extra) in enumerate(items):
            DictItem.objects.get_or_create(kind=kind, code=code, defaults={
                "name_ro": ro, "name_ru": ru, "name_en": en, "extra": extra, "sort": (i + 1) * 10})
    groups = {c.code: c for c in DictItem.objects.filter(kind=STAFF_CATEGORY)}
    for i, (code, ro, ru, en, group, hours) in enumerate(OCCUPATIONS):
        lookup = {"code": code} if code else {"code": "", "name_ro": ro}
        Occupation.objects.get_or_create(**lookup, defaults={
            "name_ro": ro, "name_ru": ru, "name_en": en, "category": groups.get(group), "weekly_hours": hours,
            "sort": (i + 1) * 10, "notes": CODE_HINTS.get(ro, ""),
        })
    for i, (code, ro, ru, en, kind) in enumerate(SPECIALTIES):
        Specialty.objects.get_or_create(name_ro=ro, defaults={"code": code, "name_ru": ru, "name_en": en, "kind": kind,
                                                              "sort": (i + 1) * 10})
    bases = {}
    for i, (code, art, par, let, ro, ru, en) in enumerate(LEGAL_BASES):
        bases[code], created = LegalBasis.objects.get_or_create(code=code, defaults={
            "act": NON_CM_ACTS.get(code, CM), "article": art, "paragraph": par, "letter": let,
            "name_ro": ro, "name_ru": ru, "name_en": en, "sort": (i + 1) * 10})
        basis = bases[code]
        # temeiurile livrate fără articol (versiunile vechi) primesc articolul, dacă clientul nu l-a scris el
        if not created and art and not (basis.article or basis.paragraph or basis.letter) and basis.act == CM:
            basis.article, basis.paragraph, basis.letter = art, par, let
            basis.save(update_fields=["article", "paragraph", "letter"])
    for i, row in enumerate(ORDER_TYPES):
        code, ro, ru, en, group, register, effect, collective, basis, title, irm19, payroll, from_1c = row
        ot, created = OrderType.objects.get_or_create(code=code, defaults={
            "name_ro": ro, "name_ru": ru, "name_en": en, "group": group, "register": register, "effect": effect,
            "collective": collective, "title_ro": title, "report_irm19": irm19,
            "payroll_effect": payroll, "from_1c": from_1c, "needs_employee": effect not in ("staff_list",),
            "sort": (i + 1) * 10,
        })
        codes = (basis,) if isinstance(basis, str) else basis
        if created and any(bases.get(c) for c in codes):
            ot.legal_bases.set([bases[c] for c in codes if bases.get(c)])
