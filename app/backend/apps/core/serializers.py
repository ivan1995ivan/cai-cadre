import re

from rest_framework import serializers

from .models import (AuditLog, BankAccount, Company, Currency, ExchangeRate, Notification, NumberSeries,
                     PaymentMethod, VatRate)

LOGO_FIELDS = ["logo", "logo_small", "logo_dark", "signature", "stamp"]
ALLOWED_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".svg", ".webp")
MAX_IMAGE_SIZE = 3 * 1024 * 1024


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ["id", "iban", "bank_name", "bic", "currency", "is_default"]
        extra_kwargs = {"bank_name": {"required": False, "allow_blank": True}}

    def validate_iban(self, value):
        value = value.replace(" ", "").upper()
        if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", value):
            raise serializers.ValidationError("IBAN incorect.")
        return value

    def validate(self, attrs):
        from .banks import fill

        if "iban" in attrs:
            attrs = fill(attrs)
        if not attrs.get("bank_name", getattr(self.instance, "bank_name", "")):
            raise serializers.ValidationError({"bank_name": "Indicați banca (sau alegeți-o din clasificator)."})
        return attrs


class CompanySerializer(serializers.ModelSerializer):
    bank_accounts = BankAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        exclude = ["installed_at"]
        extra_kwargs = {"caem": {"max_length": 8}}  # „62.01” se primește și se păstrează ca 6201

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["languages"] = instance.enabled_languages()
        return data

    def validate_languages(self, value):
        chosen = [x for x in ("ro", "ru", "en") if x in (value or [])]
        if not chosen:
            raise serializers.ValidationError("Bifați cel puțin o limbă.")
        return chosen

    def update(self, instance, validated_data):
        company = super().update(instance, validated_data)
        if "languages" in validated_data:
            from apps.users.models import User

            # cine lucra într-o limbă oprită trece pe prima limbă rămasă
            User.objects.exclude(language__in=company.enabled_languages()).update(language=company.enabled_languages()[0])
        return company

    def validate_idno(self, value):
        if value and not re.fullmatch(r"\d{13}", value):
            raise serializers.ValidationError("IDNO are 13 cifre.")
        return value

    def validate_caem(self, value):
        """Codul CAEM: patru cifre (punctul din „62.01” se scoate)."""
        value = re.sub(r"[\s.]", "", value or "")
        if value and not re.fullmatch(r"\d{4}", value):
            raise serializers.ValidationError("Codul CAEM are patru cifre (de ex. 6201).")
        return value

    def validate_primary_color(self, value):
        if value and not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            raise serializers.ValidationError("Culoarea se scrie ca #RRGGBB.")
        return value

    def validate(self, attrs):
        for field in LOGO_FIELDS:
            upload = attrs.get(field)
            if upload and hasattr(upload, "size"):
                if not upload.name.lower().endswith(ALLOWED_IMAGE_EXT):
                    raise serializers.ValidationError({field: "Sunt acceptate PNG, JPG, SVG, WEBP."})
                if upload.size > MAX_IMAGE_SIZE:
                    raise serializers.ValidationError({field: "Fișierul depășește 3 MB."})
        return attrs


class BrandingSerializer(serializers.ModelSerializer):
    """Ce se vede fără autentificare (pagina de login): nume, logo, temă."""

    class Meta:
        model = Company
        fields = ["name_ro", "name_ru", "name_en", "logo", "logo_small", "logo_dark", "default_theme", "primary_color",
                  "payroll_enabled", "military_enabled", "production_enabled", "transport_enabled", "function_panel", "languages"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["languages"] = instance.enabled_languages()
        # denumirea completă, cu forma juridică („Exemplu SRL”), în fiecare limbă — bara de titlu a programului
        data["display_names"] = {lang: instance.display_name(lang) for lang in ("ro", "ru", "en")}
        return data


class CurrencySerializer(serializers.ModelSerializer):
    last_rate = serializers.SerializerMethodField()

    class Meta:
        model = Currency
        fields = ["id", "code", "name_ro", "name_ru", "symbol", "is_base", "is_active", "auto_rate", "last_rate"]
        read_only_fields = ["is_base"]

    def get_last_rate(self, obj):
        rate = obj.rates.order_by("-date").first()
        return {"date": rate.date, "rate": str(rate.rate), "nominal": rate.nominal} if rate else None


class ExchangeRateSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source="currency.code", read_only=True)

    class Meta:
        model = ExchangeRate
        fields = ["id", "currency", "currency_code", "date", "rate", "nominal", "source"]


class VatRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VatRate
        fields = ["id", "name", "rate", "is_default", "is_active"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "code", "name_ro", "name_ru", "kind", "fiscal_receipt", "external_code", "sort", "is_active"]


class NumberSeriesSerializer(serializers.ModelSerializer):
    preview = serializers.CharField(read_only=True)

    class Meta:
        model = NumberSeries
        fields = ["id", "doc_type", "name_ro", "name_ru", "prefix", "include_year", "padding", "reset_yearly",
                  "next_value", "preview"]
        read_only_fields = ["doc_type"]

    def validate_prefix(self, value):
        if value and not re.fullmatch(r"[A-Za-z0-9/]{1,10}", value):
            raise serializers.ValidationError("Doar litere latine, cifre și /.")
        return value

    def validate_padding(self, value):
        if not 1 <= value <= 10:
            raise serializers.ValidationError("Între 1 și 10 cifre.")
        return value


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "timestamp", "user", "username", "action", "model", "object_id", "object_repr",
                  "changes", "ip"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "level", "kind", "title", "message", "link", "is_read", "created_at"]
        read_only_fields = fields
