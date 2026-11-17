"""Câmpurile obligatorii alese de administrator (Administrare → Câmpuri obligatorii), prin bife.

Dosarul angajatului, actele și studiile: la salvare, câmpurile bifate nu pot rămâne goale (de exemplu IDNP-ul, data
nașterii, IBAN-ul pentru salariu). Setarea: SystemSetting „required_fields” = {"employee": ["idnp", "birth_date"], ...}.
"""
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from rest_framework import serializers

KEY = "required_fields"

# document → (model, denumirea RO, denumirea RU, câmpurile care se pot cere, la ce moment)
DOCS = {
    "employee": ("staff.Employee", "Angajat (dosarul personal)", "Сотрудник (личное дело)",
                 ["idnp", "birth_date", "birth_place", "sex", "citizenship", "nationality", "marital_status", "phone", "email",
                  "address", "address_actual", "cnam_code", "cpas", "iban", "bank_name", "emergency_contact"], "save"),
    "document": ("staff.EmployeeDocument", "Act (din dosar)", "Документ (из личного дела)",
                 ["series", "number", "issued_by", "issue_date", "expiry_date"], "save"),
    "education": ("staff.Education", "Studii", "Образование",
                  ["specialty", "qualification", "form", "year_to", "diploma_series", "diploma_number", "diploma_date"], "save"),
}

# Denumirile câmpurilor în rusă (în română se iau din modele).
LABELS_RU = {
    "idnp": "IDNP", "birth_date": "Дата рождения", "birth_place": "Место рождения", "sex": "Пол", "citizenship": "Гражданство",
    "nationality": "Национальность", "marital_status": "Семейное положение", "phone": "Телефон", "email": "E-mail",
    "address": "Адрес прописки", "address_actual": "Адрес проживания", "cnam_code": "Код медицинского страхования (CNAM)",
    "cpas": "Персональный код социального страхования (CPAS)", "iban": "IBAN (зарплатная карта)", "bank_name": "Банк",
    "emergency_contact": "Контакт на случай ЧП", "series": "Серия", "number": "Номер", "issued_by": "Кем выдан",
    "issue_date": "Дата выдачи", "expiry_date": "Действителен до", "specialty": "Специальность", "qualification": "Квалификация",
    "form": "Форма обучения", "year_to": "Год окончания", "diploma_series": "Диплом: серия", "diploma_number": "Диплом: номер",
    "diploma_date": "Диплом: дата",
}
CONDITIONS: dict = {}


def _label(model, name: str, doc: str = "", lang: str = "ro") -> str:
    if lang == "ru" and name in LABELS_RU:
        return LABELS_RU[name]
    try:
        field = model._meta.get_field(name)
    except FieldDoesNotExist:
        return name
    label = str(getattr(field, "verbose_name", "") or name)
    return label[:1].upper() + label[1:]


def catalog() -> list:
    out = []
    for key, (label, ro, ru, fields, when) in DOCS.items():
        model = apps.get_model(label)
        out.append({"key": key, "name_ro": ro, "name_ru": ru, "when": when,
                    "fields": [{"name": f, "label": _label(model, f, key), "label_ru": _label(model, f, key, "ru")}
                               for f in fields if _exists(model, f)]})
    return out


def _exists(model, name):
    try:
        model._meta.get_field(name)
        return True
    except FieldDoesNotExist:
        return False


def selected() -> dict:
    from .models import SystemSetting

    data = SystemSetting.read(KEY, {}) or {}
    return {k: [f for f in v if f in DOCS[k][3]] for k, v in data.items() if k in DOCS and isinstance(v, list)}


def save(data: dict) -> dict:
    from .models import SystemSetting

    clean = {k: sorted({f for f in (v or []) if f in DOCS[k][3] and _exists(apps.get_model(DOCS[k][0]), f)})
             for k, v in (data or {}).items() if k in DOCS}
    SystemSetting.write(KEY, {k: v for k, v in clean.items() if v})
    return selected()


def _empty(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or (hasattr(value, "name") and value.name == "")


def missing(doc: str, get) -> list:
    """Câmpurile obligatorii goale; `get(nume)` dă valoarea câmpului (din datele trimise sau din obiect)."""
    model = apps.get_model(DOCS[doc][0])
    out = []
    for name in selected().get(doc, []):
        condition = CONDITIONS.get((doc, name))
        if condition and not condition(get):
            continue
        if _empty(get(name)):
            out.append(name)
    return [(n, _label(model, n, doc)) for n in out]


def check_instance(doc: str, obj, error_class=ValueError):
    """Documentele: la înregistrare, câmpurile obligatorii trebuie completate."""
    gone = missing(doc, lambda n: getattr(obj, n, None))
    if gone:
        raise error_class("Completați câmpurile obligatorii: " + ", ".join(label for _n, label in gone) + ".")


class RequiredFieldsMixin:
    """Serializerele clasificatoarelor: la salvare, câmpurile bifate ca obligatorii nu pot rămâne goale."""

    required_doc = ""

    def run_validation(self, data=serializers.empty):
        attrs = super().run_validation(data)
        if self.required_doc:
            instance = getattr(self, "instance", None)

            def get(name):
                if name in attrs:
                    return attrs[name]
                return getattr(instance, name, None) if instance is not None else None

            gone = missing(self.required_doc, get)
            if gone:
                raise serializers.ValidationError({n: f"„{label}” este obligatoriu (Administrare → Câmpuri obligatorii)."
                                                   for n, label in gone})
        return attrs
