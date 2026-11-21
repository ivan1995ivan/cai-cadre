from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.core import license as license_service
from apps.core import moved

from .models import Permission, Role, User
from .registry import MODULES, SCOPES, SENSITIVE_FIELDS


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "module", "action", "name_ro", "name_ru"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(
        slug_field="code", many=True, queryset=Permission.objects.all(), required=False
    )
    user_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Role
        fields = ["id", "code", "name_ro", "name_ru", "description", "is_admin", "is_system", "permissions",
                  "data_scopes", "max_discount", "min_margin", "hidden_fields", "menu_hidden", "user_count"]
        read_only_fields = ["is_system"]

    def validate_menu_hidden(self, value):
        return _menu_list(value)

    def validate_data_scopes(self, value):
        for module, scope in (value or {}).items():
            if module not in MODULES or scope not in SCOPES:
                raise serializers.ValidationError(f"Valoare greșită: {module}={scope}")
        return value

    def validate_hidden_fields(self, value):
        unknown = set(value or []) - set(SENSITIVE_FIELDS)
        if unknown:
            raise serializers.ValidationError(f"Câmpuri necunoscute: {', '.join(unknown)}")
        return value

    def validate_max_discount(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Discountul maxim trebuie să fie între 0 și 100%.")
        return value

    def validate(self, attrs):
        if self.instance and self.instance.is_system and "code" in attrs and attrs["code"] != self.instance.code:
            raise serializers.ValidationError({"code": "Codul unui rol predefinit nu se poate schimba."})
        return attrs


def _subdivisions():
    from apps.org.models import Subdivision

    return Subdivision.objects.all()


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(many=True, queryset=Role.objects.all(), required=False)
    # secțiile utilizatorului (șeful subdiviziunii, adjunctul lui): după ele se vede „doar ale mele / subdiviziunile mele”
    subdivisions = serializers.PrimaryKeyRelatedField(many=True, queryset=_subdivisions(), required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "middle_name", "full_name", "email", "phone",
                  "position", "language", "theme", "is_active", "roles", "subdivisions", "must_change_password",
                  "last_login", "date_joined", "password"]
        read_only_fields = ["last_login", "date_joined"]

    def get_full_name(self, obj):
        return str(obj)

    def validate_language(self, value):
        return _language(value)

    def validate_password(self, value):
        if value:
            try:
                validate_password(value)
            except ValidationError as exc:
                raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, attrs):
        if not self.instance and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Parola este obligatorie pentru un utilizator nou."})
        creating_active = not self.instance and attrs.get("is_active", True)
        activating = self.instance and not self.instance.is_active and attrs.get("is_active")
        if creating_active or activating:
            lic = license_service.status()
            if User.objects.filter(is_active=True).count() >= lic["max_users"]:
                raise serializers.ValidationError(
                    f"Licența ({lic.get('plan_name', '')}) permite cel mult {lic['max_users']} utilizatori activi. "
                    "Dezactivați un utilizator sau treceți la o treaptă mai mare (Administrare → Licență)."
                )
        return attrs

    def create(self, validated_data):
        roles = validated_data.pop("roles", [])
        subdivisions = validated_data.pop("subdivisions", [])  # liste (many-to-many): se pun după salvare
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        user.roles.set(roles)
        user.subdivisions.set(subdivisions)
        return user

    def update(self, instance, validated_data):
        roles = validated_data.pop("roles", None)
        subdivisions = validated_data.pop("subdivisions", None)
        password = validated_data.pop("password", "")
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        if roles is not None:
            instance.roles.set(roles)
        if subdivisions is not None:
            instance.subdivisions.set(subdivisions)
        return instance


def _menu_list(value):
    if not isinstance(value, list) or not all(isinstance(x, str) and len(x) <= 60 for x in value):
        raise serializers.ValidationError("Lista meniului e greșită.")
    return moved.hidden_keys(value)


def _favorites(value):
    """Favoritele: cel mult 30, fiecare cu adresa paginii (în aplicație) și eticheta funcției sau titlul paginii."""
    if not isinstance(value, list) or len(value) > 30:
        raise serializers.ValidationError("Cel mult 30 de favorite.")
    out = []
    for item in value:
        path = str((item or {}).get("path", "")) if isinstance(item, dict) else ""
        if not path.startswith("/") or path.startswith("//") or len(path) > 200:
            raise serializers.ValidationError("Adresa favoritei e greșită.")
        out.append({"path": path, "key": str(item.get("key", ""))[:40], "title": str(item.get("title", ""))[:100]})
    return moved.favorites(out)


def _language(value):
    from apps.core.models import Company

    if value and value not in Company.get().enabled_languages():
        raise serializers.ValidationError("Limba aceasta nu este pornită în sistem (Constante → Module).")
    return value


class MeSerializer(serializers.ModelSerializer):
    """Profilul utilizatorului curent (ce își poate schimba singur)."""

    roles = RoleSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    hidden_fields = serializers.SerializerMethodField()
    menu_hidden = serializers.SerializerMethodField()
    max_discount = serializers.SerializerMethodField()
    min_margin = serializers.SerializerMethodField()
    can_see_margin = serializers.SerializerMethodField()
    scopes = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    license = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "middle_name", "full_name", "email", "phone",
                  "position", "language", "theme", "density", "buttons", "roles", "permissions",
                  "is_admin", "hidden_fields", "menu_hidden", "max_discount", "min_margin", "can_see_margin", "scopes", "must_change_password",
                  "last_seen_version", "tours_done", "favorites", "license", "profile"]
        read_only_fields = ["username", "roles", "must_change_password"]

    def get_permissions(self, obj):
        return sorted(obj.permission_codes())

    def get_is_admin(self, obj):
        return obj.is_crm_admin

    def validate_favorites(self, value):
        return _favorites(value)

    def validate_language(self, value):
        return _language(value)

    def get_menu_hidden(self, obj):
        return obj.menu_hidden()

    def get_hidden_fields(self, obj):
        return sorted(obj.hidden_fields())

    def get_max_discount(self, obj):
        return str(obj.max_discount())

    def get_min_margin(self, obj):
        return str(obj.min_margin())

    def get_can_see_margin(self, obj):
        return obj.can_see_margin()

    def get_scopes(self, obj):
        return {m: obj.data_scope(m) for m, spec in MODULES.items() if spec[3]}

    def get_full_name(self, obj):
        return str(obj)

    def get_license(self, obj):
        return license_service.summary()

    def get_profile(self, obj):
        """Profilul produsului: „trade” (comerț alimentar / nealimentar) ascunde calculatorul de acoperiș, rolele de
        tablă și parametrii foilor; „roofing” le arată."""
        from django.conf import settings

        return getattr(settings, "PRODUCT_PROFILE", "trade")

    def validate_theme(self, value):
        if value not in dict(User.THEMES) and value != "":
            raise serializers.ValidationError("Temă necunoscută.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "Parola actuală este greșită."})
        try:
            validate_password(attrs["new_password"], user)
        except ValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        return attrs
