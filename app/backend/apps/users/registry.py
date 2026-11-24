"""Catalogul modulelor și al drepturilor (permisiunilor) — CAI CADRE.

Fiecare drept are codul `<modul>.<acțiune>`, de exemplu `employees.view`.
Catalogul e sursa unică: comanda `crm_seed` îl sincronizează în baza de date,
iar rolurile primesc drepturi din el. Modulele care apar în etapele următoare
sunt deja declarate, ca rolurile să poată fi configurate de la început.
"""

ACTIONS = {
    "view": ("Vizualizare", "Просмотр"),
    "create": ("Creare", "Создание"),
    "edit": ("Editare", "Редактирование"),
    "delete": ("Ștergere", "Удаление"),
    "approve": ("Aprobare / semnare", "Утверждение / подпись"),
    "export": ("Export", "Экспорт"),
    "sensitive": ("Date sensibile (IDNP, acte, sănătate)", "Конфиденциальные данные (IDNP, документы, здоровье)"),
}

# cod modul: (denumire RO, denumire RU, acțiuni, are filtru pe rânduri „doar subdiviziunea mea / ale mele”)
MODULES = {
    "org": ("Întreprinderea, subdiviziunile, statele de personal", "Предприятие, подразделения, штатное расписание",
            ["view", "create", "edit", "delete", "approve", "export"], False),
    "dictionaries": ("Clasificatoare (funcții CORM, specialități, temeiuri legale...)", "Классификаторы (должности CORM, специальности, основания...)",
                     ["view", "create", "edit", "delete", "export"], False),
    "employees": ("Angajați (dosarul personal)", "Сотрудники (личное дело)",
                  ["view", "create", "edit", "delete", "export", "sensitive"], True),
    "contracts": ("Contracte individuale de muncă", "Трудовые договоры", ["view", "create", "edit", "delete", "export"], True),
    "orders": ("Ordine", "Приказы", ["view", "create", "edit", "delete", "approve", "export"], True),
    "leave": ("Concedii (solduri, grafic, cereri)", "Отпуска (остатки, график, заявления)",
              ["view", "create", "edit", "delete", "approve", "export"], True),
    "sick_leave": ("Certificate de concediu medical", "Листки нетрудоспособности", ["view", "create", "edit", "delete"], True),
    "worktime": ("Timp de muncă (grafice, pontaj)", "Рабочее время (графики, табель)",
                 ["view", "create", "edit", "delete", "approve", "export"], True),
    "training": ("Formarea profesională", "Обучение персонала", ["view", "create", "edit", "delete", "export"], True),
    "health": ("Sănătatea și securitatea în muncă (examene medicale, instructaj SSM)", "Охрана здоровья и труда (медосмотры, инструктажи)",
               ["view", "create", "edit", "delete"], True),
    "military": ("Evidența militară (modul opțional)", "Воинский учёт (дополнительный модуль)", ["view", "create", "edit", "delete", "export"],
                 False),
    "payroll": ("Salarizare (calcul, plată, achitare)", "Зарплата (расчёт, выплата, перечисление)",
                ["view", "create", "edit", "delete", "approve", "export"], True),
    "production": ("Producția: salarizarea în acord (modul opțional — grila, lucrările, brigăzile, rapoartele de producție)",
                   "Производство: сдельная оплата (дополнительный модуль — сетка, работы, бригады, отчёты о выработке)",
                   ["view", "create", "edit", "delete", "approve", "export"], True),
    "transport": ("Transportul: cursele, diurnele, plata pe km (modul opțional — vehiculele, tarifele, normele diurnei)",
                  "Транспорт: рейсы, суточные, оплата за км (дополнительный модуль — транспорт, тарифы, нормы суточных)",
                  ["view", "create", "edit", "delete", "approve", "export"], True),
    "payroll_settings": ("Setările salariului (constante, tipuri de calcul)", "Настройки зарплаты (константы, виды расчёта)",
                         ["view", "edit"], False),
    "tax_reports": ("Raportări fiscale (IPC21, IALS21, IRM19)", "Налоговая отчётность (IPC21, IALS21, IRM19)",
                    ["view", "create", "export"], False),
    "reports": ("Rapoarte", "Отчёты", ["view", "export"], True),
    "portal": ("Cabinetul angajatului (datele proprii, cereri)", "Личный кабинет сотрудника", ["view", "create"], False),
    "imports": ("Import din Excel", "Импорт из Excel", ["view", "create"], False),
    "users": ("Utilizatori", "Пользователи", ["view", "create", "edit", "delete"], False),
    "roles": ("Roluri și drepturi", "Роли и права", ["view", "create", "edit", "delete"], False),
    "settings": ("Constante și setări", "Константы и настройки", ["view", "edit"], False),
    "audit": ("Jurnal de audit", "Журнал аудита", ["view", "export"], False),
}

# Câmpuri sensibile care pot fi ascunse pe rol.
SENSITIVE_FIELDS = {
    "salary": ("Salariul de funcție și sporurile", "Оклад и надбавки"),
    "idnp": ("IDNP și actele de identitate", "IDNP и документы"),
    "health": ("Datele de sănătate (examene medicale)", "Данные о здоровье (медосмотры)"),
    "contacts": ("Telefon, e-mail, adresa angajatului", "Телефон, e-mail, адрес сотрудника"),
    "family": ("Familia (soț / soție, copii)", "Семья (супруг(а), дети)"),
}

SCOPES = {
    "own": ("Doar ale mele (subdiviziunea mea / eu)", "Только свои (моё подразделение / я)"),
    "team": ("Subdiviziunile mele", "Мои подразделения"),
    "all": ("Toate", "Все"),
}


def all_permission_codes():
    for module, (_ro, _ru, actions, _scoped) in MODULES.items():
        for action in actions:
            yield f"{module}.{action}"


def _perms(spec: dict) -> list:
    """{"employees": "*", "orders": ["view"]} → lista de coduri."""
    codes = []
    for module, actions in spec.items():
        if actions == "*":
            actions = MODULES[module][2]
        codes += [f"{module}.{a}" for a in actions]
    return codes


# Rolurile predefinite (se pot modifica din interfață; se creează doar dacă lipsesc).
DEFAULT_ROLES = {
    "admin": {
        "name": ("Administrator", "Администратор"),
        "is_admin": True,
        "permissions": [],
        "scopes": {},
        "max_discount": 0,
        "hidden_fields": [],
    },
    "hr_head": {
        "name": ("Șef resurse umane", "Начальник отдела кадров"),
        "permissions": _perms({
            "org": "*", "dictionaries": "*", "employees": "*", "contracts": "*", "orders": "*", "leave": "*",
            "sick_leave": "*", "worktime": "*", "training": "*", "health": "*", "military": "*",
            "reports": "*", "imports": "*", "payroll": ["view"], "tax_reports": ["view", "export"], "audit": ["view"],
            "production": ["view"], "transport": ["view"],
        }),
        "scopes": {},
        "max_discount": 0,
        "hidden_fields": [],
    },
    "hr_inspector": {
        "name": ("Inspector resurse umane", "Инспектор отдела кадров"),
        "permissions": _perms({
            "org": ["view"], "dictionaries": ["view", "create", "edit"], "employees": ["view", "create", "edit", "export", "sensitive"],
            "contracts": ["view", "create", "edit"], "orders": ["view", "create", "edit", "export"],
            "leave": ["view", "create", "edit"], "sick_leave": ["view", "create", "edit"], "worktime": ["view", "create", "edit"],
            "training": ["view", "create", "edit"], "health": ["view", "create", "edit"], "military": ["view", "create", "edit", "export"],
            "reports": ["view", "export"],
        }),
        "scopes": {},
        "max_discount": 0,
        "hidden_fields": ["salary"],
    },
    "director": {
        "name": ("Director / administrator", "Директор / администратор"),
        "permissions": _perms({
            "org": ["view", "approve"], "dictionaries": ["view"], "employees": ["view", "export"], "contracts": ["view"],
            "orders": ["view", "approve", "export"], "leave": ["view", "approve"], "worktime": ["view", "approve"],
            "training": ["view"], "payroll": ["view", "approve"], "reports": "*", "audit": ["view"],
            "production": ["view", "approve"], "transport": ["view", "approve"],
        }),
        "scopes": {},
        "max_discount": 0,
        "hidden_fields": [],
    },
    "department_head": {
        "name": ("Șef de subdiviziune", "Руководитель подразделения"),
        "permissions": _perms({
            "employees": ["view"], "orders": ["view"], "leave": ["view", "create", "edit", "approve"],
            "sick_leave": ["view"], "worktime": ["view", "create", "edit"], "training": ["view"], "reports": ["view"],
            "production": ["view", "create", "edit"], "transport": ["view", "create", "edit"],
        }),
        "scopes": {"employees": "own", "orders": "own", "leave": "own", "sick_leave": "own", "worktime": "own",
                   "training": "own", "reports": "own", "production": "own", "transport": "own"},
        "max_discount": 0,
        "hidden_fields": ["salary", "idnp", "health", "family"],
    },
    "accountant": {
        "name": ("Contabilitate (salarizare)", "Бухгалтерия (расчёт зарплаты)"),
        "permissions": _perms({
            "org": ["view"], "employees": ["view", "export"], "contracts": ["view"], "orders": ["view", "export"],
            "leave": ["view"], "sick_leave": ["view", "create", "edit"], "worktime": ["view", "export"],
            "payroll": "*", "payroll_settings": "*", "tax_reports": "*", "reports": ["view", "export"], "audit": ["view"],
            "production": "*", "transport": "*",
        }),
        "scopes": {},
        "max_discount": 0,
        "hidden_fields": ["health"],
    },
    "employee": {
        "name": ("Angajat (cabinetul personal)", "Сотрудник (личный кабинет)"),
        "permissions": _perms({"portal": "*"}),
        "scopes": {},
        "max_discount": 0,
        "hidden_fields": [],
    },
}
