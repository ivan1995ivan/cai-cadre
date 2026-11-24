"""Datele inițiale ale sistemului. Funcțiile sunt idempotente: se pot rula la fiecare actualizare
și nu suprascriu ce a modificat utilizatorul (adaugă doar ce lipsește)."""
from decimal import Decimal

from django.db import transaction

from apps.users.models import Permission, Role
from apps.users.registry import ACTIONS, DEFAULT_ROLES, MODULES

from .models import Company, Currency, NumberSeries, PaymentMethod, SystemSetting, VatRate

CURRENCIES = [
    ("MDL", "Leu moldovenesc", "Молдавский лей", "lei", True),
    ("EUR", "Euro", "Евро", "€", False),
    ("USD", "Dolar SUA", "Доллар США", "$", False),
    ("RON", "Leu românesc", "Румынский лей", "RON", False),
    ("UAH", "Grivnă ucraineană", "Украинская гривна", "₴", False),
]

VAT_RATES = [
    ("TVA 20%", Decimal("20"), True),
    ("TVA 8%", Decimal("8"), False),
    ("TVA 0%", Decimal("0"), False),
    ("Scutit de TVA", Decimal("0"), False),
]

# Modalitățile de plată a salariului
PAYMENT_METHODS = [
    ("card", "Card bancar (transfer pe cont)", "Банковская карта (перевод на счёт)", "bank", False, ""),
    ("cash", "Numerar (casa întreprinderii)", "Наличные (касса)", "cash", False, ""),
]

# tip document: (RO, RU, prefix)
NUMBER_SERIES = {
    "order_personnel": ("Ordin privind personalul", "Приказ по личному составу", ""),
    "order_leave": ("Ordin privind concediile", "Приказ об отпусках", ""),
    "order_travel": ("Ordin privind deplasările", "Приказ о командировках", ""),
    "order_general": ("Ordin de bază (activitate generală)", "Приказ по основной деятельности", ""),
    "contract": ("Contract individual de muncă", "Индивидуальный трудовой договор", ""),
    "staff_list": ("State de personal", "Штатное расписание", "SP"),
    "timesheet": ("Tabel de pontaj", "Табель учёта рабочего времени", "TP"),
    "leave_schedule": ("Graficul concediilor", "График отпусков", "GC"),
    "certificate": ("Adeverință", "Справка", "AD"),
    "payroll": ("Calculul salariului", "Расчёт зарплаты", "CS"),
    "payroll_payment": ("Îndreptarea spre plată", "Ведомость на выплату", "PS"),
    "pay_item_change": ("Modificarea acumulărilor planificate", "Изменение плановых начислений", "MA"),
    "meal_vouchers": ("Borderoul tichetelor de masă", "Ведомость талонов на питание", "TM"),
    "production_report": ("Raportul de producție", "Отчёт о выработке", "RP"),
    "payout": ("Achitare", "Выдача / перечисление", "AC"),
    "excel_import": ("Import din Excel", "Импорт из Excel", "IM"),
}


def sync_permissions():
    codes = set()
    for module, (name_ro, name_ru, actions, _scoped) in MODULES.items():
        for action in actions:
            code = f"{module}.{action}"
            codes.add(code)
            Permission.objects.update_or_create(
                code=code,
                defaults={
                    "module": module,
                    "action": action,
                    "name_ro": f"{name_ro}: {ACTIONS[action][0]}",
                    "name_ru": f"{name_ru}: {ACTIONS[action][1]}",
                },
            )
    Permission.objects.exclude(code__in=codes).delete()


def create_default_roles():
    """Creează rolurile predefinite care lipsesc.

    La actualizare, drepturile APĂRUTE ÎNTRE TIMP în catalog se acordă rolurilor predefinite conform
    DEFAULT_ROLES. Drepturile vechi nu se ating, deci ce a scos administratorul rămâne scos.
    """
    perms = {p.code: p for p in Permission.objects.all()}
    known = set(SystemSetting.read("seeded_permissions", {}).get("codes", []))
    new_codes = set(perms) - known if known else set()
    for code, spec in DEFAULT_ROLES.items():
        role, created = Role.objects.get_or_create(
            code=code,
            defaults={
                "name_ro": spec["name"][0],
                "name_ru": spec["name"][1],
                "is_admin": spec.get("is_admin", False),
                "is_system": True,
                "data_scopes": spec["scopes"],
                "max_discount": Decimal(spec["max_discount"]),
                "hidden_fields": spec["hidden_fields"],
            },
        )
        if created:
            role.permissions.set([perms[c] for c in spec["permissions"] if c in perms])
        elif new_codes:
            role.permissions.add(*[perms[c] for c in spec["permissions"] if c in new_codes])
            # modulul nou primește și filtrul pe rânduri din rolul predefinit (altfel ar vedea tot)
            fresh = {c.split(".")[0] for c in new_codes}
            scopes = {m: s for m, s in spec["scopes"].items() if m in fresh and m not in role.data_scopes}
            if scopes:
                role.data_scopes = {**role.data_scopes, **scopes}
                role.save(update_fields=["data_scopes"])
    SystemSetting.write("seeded_permissions", {"codes": sorted(perms)})


def create_reference_data():
    for code, name_ro, name_ru, symbol, is_base in CURRENCIES:
        Currency.objects.get_or_create(
            code=code, defaults={"name_ro": name_ro, "name_ru": name_ru, "symbol": symbol, "is_base": is_base,
                                 "auto_rate": not is_base}
        )
    if not VatRate.objects.exists():
        for name, rate, default in VAT_RATES:
            VatRate.objects.create(name=name, rate=rate, is_default=default)
    for i, (code, name_ro, name_ru, kind, fiscal, ext) in enumerate(PAYMENT_METHODS):
        PaymentMethod.objects.get_or_create(code=code, defaults={
            "name_ro": name_ro, "name_ru": name_ru, "kind": kind, "fiscal_receipt": fiscal, "external_code": ext,
            "sort": (i + 1) * 10})
    for doc_type, (name_ro, name_ru, prefix) in NUMBER_SERIES.items():
        NumberSeries.objects.get_or_create(
            doc_type=doc_type, defaults={"name_ro": name_ro, "name_ru": name_ru, "prefix": prefix}
        )


@transaction.atomic
def run():
    from apps.org import seed as org_seed
    from apps.printing import seed as printing_seed
    from apps.payroll import seed as payroll_seed
    from apps.worktime import seed as worktime_seed

    sync_permissions()
    create_default_roles()
    create_reference_data()
    Company.get()
    printing_seed.run()
    org_seed.run()
    worktime_seed.run()
    payroll_seed.run()
