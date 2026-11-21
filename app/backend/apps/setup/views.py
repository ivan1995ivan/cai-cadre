import json
import os
import re
import subprocess
import sys
import threading
import uuid

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Company
from config.dbconfig import ENGINES
from config.instance import INSTANCE_DIR, encrypt, load_config, save_config

from . import dbtools


def request_restart():
    """Repornește serverul ca să încarce noua bază de date.
    Codul 3 e înțeles atât de `run.py`, cât și de `manage.py runserver` ca „repornește”."""
    if os.environ.get("CRM_NO_RESTART"):
        return
    threading.Timer(1.5, os._exit, [3]).start()


class SetupView(APIView):
    public = True
    authentication_classes = []

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not settings.SETUP_MODE and not isinstance(self, StatusView):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Sistemul este deja instalat.")


class DbSerializer(serializers.Serializer):
    engine = serializers.ChoiceField(choices=list(ENGINES))
    name = serializers.CharField(allow_blank=True, required=False, default="")
    host = serializers.CharField(allow_blank=True, required=False, default="")
    port = serializers.IntegerField(required=False, allow_null=True)
    user = serializers.CharField(allow_blank=True, required=False, default="")
    password = serializers.CharField(allow_blank=True, required=False, default="", trim_whitespace=False)
    options = serializers.DictField(required=False, default=dict)

    def validate(self, attrs):
        if attrs["engine"] != "sqlite":
            missing = [f for f in ("host", "name", "user") if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError({f: "Câmp obligatoriu." for f in missing})
        elif not attrs.get("name"):
            attrs["name"] = "crm.sqlite3"
        return attrs


class StatusView(SetupView):
    def get(self, request):
        return Response({
            "installed": not settings.SETUP_MODE,
            "version": settings.APP_VERSION,
            "language": load_config().get("language", "ro"),
        })


class DriversView(SetupView):
    def get(self, request):
        return Response(dbtools.drivers())


class TestConnectionView(SetupView):
    def post(self, request):
        ser = DbSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            return Response(dbtools.probe(ser.validated_data))
        except dbtools.DbSetupError as exc:
            return Response({"detail": str(exc)}, status=400)


class CreateDatabaseView(SetupView):
    def post(self, request):
        ser = DbSerializer(data=request.data.get("db") or {})
        ser.is_valid(raise_exception=True)
        try:
            message = dbtools.create_database(
                ser.validated_data,
                admin_user=request.data.get("admin_user", ""),
                admin_password=request.data.get("admin_password", ""),
            )
        except dbtools.DbSetupError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({"message": message, "probe": dbtools.probe(ser.validated_data)})


class AdminSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[\w.@+-]+$", max_length=150)
    password = serializers.CharField(trim_whitespace=False)
    first_name = serializers.CharField(allow_blank=True, required=False, default="")
    last_name = serializers.CharField(allow_blank=True, required=False, default="")
    email = serializers.EmailField(allow_blank=True, required=False, default="")

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class CompanySetupSerializer(serializers.Serializer):
    """Datele întreprinderii din asistentul de instalare (restul se completează apoi în Constante)."""

    name_ro = serializers.CharField(max_length=200)
    name_ru = serializers.CharField(max_length=200, allow_blank=True, required=False, default="")
    legal_form = serializers.CharField(max_length=20, allow_blank=True, required=False, default="")
    idno = serializers.RegexField(r"^\d{13}$", allow_blank=True, required=False, default="",
                                  error_messages={"invalid": "IDNO are 13 cifre."})
    caem = serializers.CharField(max_length=6, allow_blank=True, required=False, default="")
    legal_address = serializers.CharField(max_length=300, allow_blank=True, required=False, default="")
    phone = serializers.CharField(max_length=64, allow_blank=True, required=False, default="")
    email = serializers.EmailField(allow_blank=True, required=False, default="")
    director = serializers.CharField(max_length=150, allow_blank=True, required=False, default="")
    director_position_ro = serializers.CharField(max_length=100, allow_blank=True, required=False, default="")
    default_theme = serializers.ChoiceField(choices=[x for x, _ in Company.THEMES], required=False, default="green")
    bank = serializers.DictField(required=False)

    def validate_caem(self, value):
        value = re.sub(r"[\s.]", "", value)
        if value and not re.fullmatch(r"\d{4}", value):
            raise serializers.ValidationError("Codul CAEM are patru cifre (de ex. 6201).")
        return value

    def validate_bank(self, value):
        iban = str(value.get("iban") or "").replace(" ", "").upper()
        if iban and not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", iban):
            raise serializers.ValidationError("IBAN incorect.")
        return {"iban": iban, "bank_name": str(value.get("bank_name") or "")[:150],
                "bic": str(value.get("bic") or "")[:11]} if iban else {}


class InstallView(SetupView):
    def post(self, request):
        ser = DbSerializer(data=request.data.get("db") or {})
        ser.is_valid(raise_exception=True)
        db = dict(ser.validated_data)
        mode = request.data.get("mode", "new")
        language = request.data.get("language", "ro")
        payload = {"mode": mode, "language": language}

        if mode == "new":
            admin = AdminSerializer(data=request.data.get("admin") or {})
            if not admin.is_valid():
                return Response({"admin": admin.errors}, status=400)
            company = CompanySetupSerializer(data=request.data.get("company") or {})
            if not company.is_valid():
                return Response({"company": company.errors}, status=400)
            payload.update(admin=admin.validated_data, company=company.validated_data, demo=bool(request.data.get("demo")))

        probe = dbtools.probe(db)
        if not probe["server_ok"] or (db["engine"] != "sqlite" and not probe["database_exists"]):
            return Response({"detail": probe["error"] or "Baza de date nu există. Creați-o mai întâi."}, status=400)
        if probe.get("other_product"):
            return Response({"detail": dbtools.OTHER_PRODUCT}, status=400)
        if mode == "new" and probe["has_crm"] and not probe["unfinished"]:
            return Response({"detail": "Baza conține deja sistemul CRM. Alegeți „Conectare la baza existentă”."},
                            status=400)
        if mode == "new" and probe["table_count"] and not probe["has_crm"]:
            if not request.data.get("allow_non_empty"):
                return Response({"detail": f"Baza conține deja {probe['table_count']} tabele străine. "
                                           "Folosiți o bază goală.", "non_empty": True}, status=400)

        db["password"] = encrypt(db.get("password", ""))
        config = load_config()
        config.update(db=db, language=language, installed=False, product="cadre")
        save_config(config)

        payload_file = INSTANCE_DIR / f"install-{uuid.uuid4().hex}.json"
        payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(settings.BASE_DIR / "manage.py"), "crm_install", "--payload", str(payload_file)],
                cwd=settings.BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=1800,
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "DJANGO_SETTINGS_MODULE": "config.settings"},
            )
        finally:
            payload_file.unlink(missing_ok=True)
        log = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            return Response({"detail": "Instalarea nu a reușit.", "log": log[-8000:]}, status=500)

        config.update(installed=True, installed_at=timezone.now().isoformat())
        save_config(config)
        if payload.get("demo"):
            # Datele demo trec prin API-ul sistemului, deci după ce instalarea e marcată (proces nou, fără regimul de instalare).
            demo_proc = subprocess.run(
                [sys.executable, str(settings.BASE_DIR / "manage.py"), "crm_demo"], cwd=settings.BASE_DIR,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "DJANGO_SETTINGS_MODULE": "config.settings"},
            )
            log += "\n" + (demo_proc.stdout or "") + (demo_proc.stderr or "")[-4000:]
        request_restart()
        return Response({"ok": True, "log": log[-8000:]})
