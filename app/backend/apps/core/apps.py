from django.apps import AppConfig


def _mssql_json_without_isjson():
    """SQL Server: câmpurile JSON primesc verificarea ISJSON(...) = 1, dar SQL Server 2016–2019 nu socotește JSON o valoare
    simplă (text, număr, dată), iar setările (SystemSetting) se țin și așa. Tabelele noi se fac fără verificare; din
    bazele create înainte o scoate migrarea core.0011_mssql_json."""
    try:
        from mssql.base import DatabaseWrapper
    except ImportError:
        return
    DatabaseWrapper.data_type_check_constraints = {k: v for k, v in DatabaseWrapper.data_type_check_constraints.items()
                                                   if k != "JSONField"}


def _drf_str_of_missing_object():
    """Câmpurile `source="manager.__str__"` (60 în serializatoare): când legătura e goală (fără manager, fără adresă),
    DRF lua `None.__str__` și pe pagină apărea „<method-wrapper '__str__' of NoneType object>”. Acum legătura goală
    înseamnă câmp absent: se folosește valoarea implicită a câmpului (de obicei "")."""
    from rest_framework import fields

    original = fields.get_attribute
    if getattr(original, "_crm_patched", False):
        return

    def get_attribute(instance, attrs):
        if attrs and attrs[-1] == "__str__":
            target = instance
            for attr in attrs[:-1]:
                target = original(target, [attr])
                if target is None:
                    raise AttributeError("legătura e goală")
        return original(instance, attrs)

    get_attribute._crm_patched = True
    fields.get_attribute = get_attribute


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"
    verbose_name = "Nucleu"

    def ready(self):
        _mssql_json_without_isjson()
        _drf_str_of_missing_object()
        from .audit import register
        from .models import BankAccount, Company, Currency, NumberSeries, PaymentMethod, VatRate

        register(Company)
        register(BankAccount)
        register(Currency)
        register(VatRate)
        register(PaymentMethod)
        register(NumberSeries, exclude={"next_value", "current_year"})
