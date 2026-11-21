from rest_framework import serializers

from apps.core.required import RequiredFieldsMixin
from apps.org.serializers import user_lang

from . import services
from .models import (AccessLog, Education, Employee, EmployeeDocument, Employment, EmploymentHistory, FamilyMember,
                     MilitaryRecord, PriorExperience)

# câmpurile sensibile (users.registry.SENSITIVE_FIELDS) → ce se ascunde din fișă
SENSITIVE = {
    "idnp": {"idnp", "cnam_code", "cpas", "birth_place"},
    "contacts": {"phone", "phone2", "email", "address", "address_actual", "emergency_contact"},
    "salary": {"base_salary", "allowance_pct", "combination_pct", "iban", "bank_name"},
    "health": {"disability"},
}


def hidden_for(request) -> set:
    """Ce câmpuri nu vede utilizatorul: fără dreptul „date sensibile” — IDNP și actele; plus ce ascund rolurile."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return set()
    hidden = set()
    flags = set(user.hidden_fields())
    if not user.has_crm_perm("employees.sensitive"):
        flags |= {"idnp", "health"}
    for flag in flags:
        hidden |= SENSITIVE.get(flag, set())
    return hidden


class MaskMixin:
    def to_internal_value(self, data):
        # câmpurile pe care utilizatorul nu le vede nu le poate nici schimba (formularul le trimite goale)
        hidden = hidden_for(self.context.get("request"))
        if hidden and hasattr(data, "keys"):
            data = {k: data[k] for k in data.keys() if k not in hidden}
        return super().to_internal_value(data)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        for field in hidden_for(self.context.get("request")) & set(data):
            data[field] = None
        return data


def _name(obj, lang):
    return obj.local_name(lang) if obj else ""


class EmployeeDocumentSerializer(RequiredFieldsMixin, serializers.ModelSerializer):
    required_doc = "document"

    doc_type_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocument
        fields = ["id", "employee", "doc_type", "doc_type_name", "title", "series", "number", "issued_by", "issue_date",
                  "expiry_date", "file", "is_identity", "note", "created_at"]
        read_only_fields = ["created_at"]

    def get_doc_type_name(self, obj):
        return _name(obj.doc_type, user_lang(self)) or obj.title

    def validate(self, attrs):
        if not attrs.get("doc_type", getattr(self.instance, "doc_type", None)) and not attrs.get("title", getattr(self.instance, "title", "")):
            raise serializers.ValidationError({"doc_type": "Alegeți tipul actului sau scrieți denumirea."})
        start, end = attrs.get("issue_date"), attrs.get("expiry_date")
        if start and end and end < start:
            raise serializers.ValidationError({"expiry_date": "Termenul este înaintea datei eliberării."})
        return attrs


class FamilyMemberSerializer(MaskMixin, serializers.ModelSerializer):
    relation_name = serializers.SerializerMethodField()

    class Meta:
        model = FamilyMember
        fields = ["id", "employee", "relation", "relation_name", "full_name", "idnp", "birth_date", "dependent", "disabled", "note"]

    def get_relation_name(self, obj):
        return _name(obj.relation, user_lang(self))


class EducationSerializer(RequiredFieldsMixin, serializers.ModelSerializer):
    required_doc = "education"

    level_name = serializers.SerializerMethodField()
    specialty_name = serializers.SerializerMethodField()
    form_name = serializers.SerializerMethodField()

    class Meta:
        model = Education
        fields = ["id", "employee", "level", "level_name", "institution", "specialty", "specialty_name", "specialty_text",
                  "qualification", "form", "form_name", "year_from", "year_to", "diploma_series", "diploma_number", "diploma_date"]

    def get_level_name(self, obj):
        return _name(obj.level, user_lang(self))

    def get_specialty_name(self, obj):
        return _name(obj.specialty, user_lang(self)) or obj.specialty_text

    def get_form_name(self, obj):
        return _name(obj.form, user_lang(self))


class PriorExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorExperience
        fields = ["id", "employee", "organization", "position", "date_from", "date_to", "in_specialty", "document"]

    def validate(self, attrs):
        start = attrs.get("date_from", getattr(self.instance, "date_from", None))
        end = attrs.get("date_to", getattr(self.instance, "date_to", None))
        if start and end and end < start:
            raise serializers.ValidationError({"date_to": "Data de sfârșit este înaintea celei de început."})
        return attrs


class MilitaryRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MilitaryRecord
        fields = ["id", "employee", "status", "category", "group", "composition", "rank", "specialty_code", "center", "fit",
                  "special_record", "book", "note"]


class EmploymentHistorySerializer(MaskMixin, serializers.ModelSerializer):
    event_label = serializers.CharField(source="get_event_display", read_only=True)
    subdivision_name = serializers.SerializerMethodField()
    occupation_name = serializers.SerializerMethodField()

    class Meta:
        model = EmploymentHistory
        fields = ["id", "event", "event_label", "date", "subdivision", "subdivision_name", "occupation", "occupation_name",
                  "rate", "base_salary", "allowance_pct", "combination_pct", "order", "note", "created_at"]

    def get_subdivision_name(self, obj):
        return _name(obj.subdivision, user_lang(self))

    def get_occupation_name(self, obj):
        return _name(obj.occupation, user_lang(self))


class EmploymentSerializer(MaskMixin, serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    subdivision_name = serializers.SerializerMethodField()
    occupation_name = serializers.SerializerMethodField()
    occupation_code = serializers.CharField(source="occupation.code", read_only=True)
    category = serializers.IntegerField(source="occupation.category_id", read_only=True, allow_null=True)
    category_name = serializers.SerializerMethodField()
    termination_reason_name = serializers.SerializerMethodField()
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_tab = serializers.CharField(source="employee.tab_number", read_only=True)
    history = EmploymentHistorySerializer(many=True, read_only=True)
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = Employment
        fields = ["id", "employee", "employee_name", "employee_tab", "kind", "kind_label", "subdivision", "subdivision_name", "occupation", "occupation_name",
                  "occupation_code", "category", "category_name", "rate", "base_salary", "allowance_pct", "combination_pct", "date_from", "date_to",
                  "probation_until", "contract_number", "contract_date", "substitutes", "status", "status_label",
                  "suspended_from", "suspension_reason", "end_date", "termination_reason", "termination_reason_name",
                  "hire_order", "end_order", "note", "history", "warnings"]
        read_only_fields = ["status", "suspended_from", "suspension_reason", "end_date", "termination_reason", "end_order"]

    def get_subdivision_name(self, obj):
        return _name(obj.subdivision, user_lang(self))

    def get_warnings(self, obj):
        """Salariul de funcție sub salariul minim pe țară (apps.payroll.alerts)."""
        from apps.payroll.alerts import min_wage_warning

        if obj.status == "ended":
            return []
        text = min_wage_warning(obj.base_salary, obj.kind)
        return [text] if text else []

    def get_occupation_name(self, obj):
        return _name(obj.occupation, user_lang(self))

    def get_termination_reason_name(self, obj):
        return _name(obj.termination_reason, user_lang(self))

    def get_category_name(self, obj):
        return _name(obj.occupation.category, user_lang(self)) if obj.occupation.category_id else ""


class EmployeeListSerializer(MaskMixin, serializers.ModelSerializer):
    """Rândul din lista angajaților: datele persoanei și raportul de bază (secția, funcția, norma)."""

    full_name = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    subdivision = serializers.SerializerMethodField()
    occupation = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    kind = serializers.SerializerMethodField()
    rate = serializers.SerializerMethodField()
    date_from = serializers.SerializerMethodField()
    jobs = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ["id", "tab_number", "full_name", "last_name", "first_name", "patronymic", "idnp", "birth_date", "sex",
                  "phone", "email", "status", "status_label", "is_archived", "subdivision", "occupation", "category",
                  "category_name", "kind", "rate", "date_from", "jobs"]

    def _main(self, obj):
        if not hasattr(obj, "_main_cache"):
            obj._main_cache = obj.main_employment()
        return obj._main_cache

    def get_subdivision(self, obj):
        m = self._main(obj)
        return _name(m.subdivision, user_lang(self)) if m else ""

    def get_occupation(self, obj):
        m = self._main(obj)
        return _name(m.occupation, user_lang(self)) if m else ""

    def get_category(self, obj):
        m = self._main(obj)
        return m.occupation.category_id if m else None

    def get_category_name(self, obj):
        m = self._main(obj)
        return _name(m.occupation.category, user_lang(self)) if m and m.occupation.category_id else ""

    def get_kind(self, obj):
        m = self._main(obj)
        return m.kind if m else ""

    def get_rate(self, obj):
        m = self._main(obj)
        return str(m.rate) if m else ""

    def get_date_from(self, obj):
        m = self._main(obj)
        return m.date_from if m else None

    def get_jobs(self, obj):
        """Câte raporturi active are (de bază + cumul)."""
        return sum(1 for e in obj.employments.all() if e.status != "ended")


class EmployeeSerializer(RequiredFieldsMixin, MaskMixin, serializers.ModelSerializer):
    required_doc = "employee"

    full_name = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    nationality_name = serializers.SerializerMethodField()
    marital_status_name = serializers.SerializerMethodField()
    seniority = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ["id", "tab_number", "full_name", "last_name", "first_name", "patronymic", "previous_names", "idnp",
                  "birth_date", "birth_place", "sex", "citizenship", "nationality", "nationality_name", "marital_status",
                  "marital_status_name", "photo", "phone", "phone2", "email", "address", "address_actual", "cnam_code",
                  "cpas", "iban", "bank_name", "emergency_contact", "disability", "clothing_size", "shoe_size", "height",
                  "status", "status_label", "is_archived",
                  "checklist", "notes", "user", "created_at", "seniority"]
        read_only_fields = ["status", "created_at"]
        extra_kwargs = {"tab_number": {"required": False, "allow_blank": True}}

    def get_nationality_name(self, obj):
        return _name(obj.nationality, user_lang(self))

    def validate_height(self, value):
        if value is not None and not 50 <= value <= 250:
            raise serializers.ValidationError("Înălțimea se scrie în centimetri (de ex. 170).")
        return value

    def get_marital_status_name(self, obj):
        return _name(obj.marital_status, user_lang(self))

    def get_seniority(self, obj):
        if not self.context.get("with_seniority"):
            return None
        s = services.seniority(obj)
        lang = user_lang(self)
        return {k: {**v, "text": services.seniority_text(v, lang)} for k, v in s.items() if k != "on_date"}

    def validate_tab_number(self, value):
        value = (value or "").strip()
        if value and Employee.objects.filter(tab_number=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Numărul de tabel este deja folosit.")
        return value

    def validate_idnp(self, value):
        if value and Employee.objects.filter(idnp=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Există deja un angajat cu acest IDNP.")
        return value

    def to_internal_value(self, data):
        # fișa trimisă înapoi întreagă (JSON) are photo = adresa sau null: fotografia se schimbă doar prin încărcare
        if hasattr(data, "keys") and not hasattr(data.get("photo"), "read") and data.get("photo") != "":
            data = {k: data[k] for k in data.keys() if k != "photo"}
        return super().to_internal_value(data)

    def validate_photo(self, value):
        if value and hasattr(value, "name") and not value.name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            raise serializers.ValidationError("Fotografia: JPG, PNG sau WEBP.")
        return value


class AccessLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AccessLog
        fields = ["id", "user", "user_name", "action", "action_label", "detail", "at"]

    def get_user_name(self, obj):
        return str(obj.user) if obj.user_id else ""


class ContractRowSerializer(EmploymentSerializer):
    """Rândul din registrul contractelor (fără istoric — lista e mare)."""

    class Meta(EmploymentSerializer.Meta):
        fields = [f for f in EmploymentSerializer.Meta.fields if f != "history"]
