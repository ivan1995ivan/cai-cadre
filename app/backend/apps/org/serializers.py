from rest_framework import serializers

from .models import STAFF_CATEGORY, DictItem, LegalBasis, Occupation, OrderType, Specialty, StaffList, StaffListLine, Subdivision

NAMED = ["id", "code", "name_ro", "name_ru", "name_en", "sort", "is_active"]


def user_lang(serializer) -> str:
    request = serializer.context.get("request")
    return getattr(getattr(request, "user", None), "language", "") or "ro"


def validate_staff_category(value):
    if value is not None and value.kind != STAFF_CATEGORY:
        raise serializers.ValidationError("Alegeți o categorie din clasificatorul „Categoriile de personal”.")
    return value


class OccupationSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = Occupation
        fields = NAMED + ["category", "category_name", "isco_code", "weekly_hours", "base_leave_days", "extra_leave_days",
                          "harmful", "notes"]

    def get_category_name(self, obj):
        return obj.category.local_name(user_lang(self)) if obj.category_id else ""

    def validate_category(self, value):
        return validate_staff_category(value)

    def validate_code(self, value):
        value = (value or "").strip()
        if value and Occupation.objects.filter(code=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Există deja o funcție cu acest cod CORM.")
        return value


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = NAMED + ["kind", "isced"]


class DictItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DictItem
        fields = NAMED + ["kind", "extra"]

    def validate(self, attrs):
        kind = attrs.get("kind") or getattr(self.instance, "kind", None)
        code = attrs.get("code", getattr(self.instance, "code", ""))
        if code and DictItem.objects.filter(kind=kind, code=code).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError({"code": "Codul există deja în acest clasificator."})
        return attrs


class LegalBasisSerializer(serializers.ModelSerializer):
    reference = serializers.CharField(read_only=True)

    class Meta:
        model = LegalBasis
        fields = ["id", "code", "act", "article", "paragraph", "letter", "name_ro", "name_ru", "name_en", "text_ro",
                  "text_ru", "sort", "is_active", "reference"]


class OrderTypeSerializer(serializers.ModelSerializer):
    legal_bases_ref = serializers.SerializerMethodField()

    class Meta:
        model = OrderType
        fields = NAMED + ["group", "register", "effect", "collective", "needs_employee", "legal_bases", "legal_bases_ref",
                          "title_ro", "title_ru", "report_irm19", "payroll_effect", "from_1c", "point_template_ro",
                          "point_template_ru", "default_point"]
        read_only_fields = ["from_1c"]

    default_point = serializers.SerializerMethodField()

    def get_legal_bases_ref(self, obj):
        return LegalBasis.combined(obj.legal_bases.all())

    def get_default_point(self, obj):
        from apps.orders.texts import DEFAULT_POINTS

        return DEFAULT_POINTS.get(obj.code, "")

    def validate_code(self, value):
        if not value:
            raise serializers.ValidationError("Codul este obligatoriu.")
        if OrderType.objects.filter(code=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Codul există deja.")
        return value


class SubdivisionSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name_ro", read_only=True, default="")

    class Meta:
        model = Subdivision
        fields = NAMED + ["parent", "parent_name", "kind", "harmful", "extra_leave_days", "reduced_hours", "head_name",
                          "users"]

    def validate_parent(self, parent):
        node = parent
        while node is not None and self.instance is not None:
            if node.pk == self.instance.pk:
                raise serializers.ValidationError("Subdiviziunea nu poate fi pusă sub ea însăși.")
            node = node.parent
        return parent


class StaffListLineSerializer(serializers.ModelSerializer):
    subdivision_name = serializers.SerializerMethodField()
    occupation_code = serializers.CharField(source="occupation.code", read_only=True)
    occupation_name = serializers.SerializerMethodField()
    effective_category = serializers.SerializerMethodField()
    effective_category_name = serializers.SerializerMethodField()
    monthly_fund = serializers.SerializerMethodField()

    class Meta:
        model = StaffListLine
        fields = ["id", "staff_list", "subdivision", "subdivision_name", "occupation", "occupation_code", "occupation_name",
                  "category", "effective_category", "effective_category_name", "units", "base_salary", "allowance_pct", "note",
                  "sort", "monthly_fund"]

    def get_effective_category(self, obj):
        category = obj.effective_category()
        return category.pk if category else None

    def get_effective_category_name(self, obj):
        category = obj.effective_category()
        return category.local_name(user_lang(self)) if category else ""

    def validate_category(self, value):
        return validate_staff_category(value)

    def get_subdivision_name(self, obj):
        return obj.subdivision.local_name(user_lang(self))

    def get_occupation_name(self, obj):
        return obj.occupation.local_name(user_lang(self))

    def get_monthly_fund(self, obj):
        return str(obj.monthly_fund())

    def validate_units(self, value):
        if value <= 0:
            raise serializers.ValidationError("Unitățile trebuie să fie mai mari decât zero.")
        return value


class StaffListSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    lines_count = serializers.IntegerField(read_only=True, default=None)
    previous_label = serializers.SerializerMethodField()

    class Meta:
        model = StaffList
        fields = ["id", "number", "date", "effective_from", "approved_by", "basis", "status", "status_label", "previous",
                  "previous_label", "notes", "created_at", "approved_at", "lines_count"]
        read_only_fields = ["status", "previous", "created_at", "approved_at"]

    def get_previous_label(self, obj):
        return str(obj.previous) if obj.previous_id else ""
