"""Administrare → Întreținere: copiile de rezervă și actualizările programului."""
import json
import os
import tempfile
from pathlib import Path

import requests
from django.conf import settings
from django.http import FileResponse
from django.urls import path
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

import updater
from apps.core import deletion, license
from apps.core.models import SystemSetting
from apps.users.permissions import require
from config.instance import INSTANCE_DIR

from . import backup
from .views import request_restart

UPDATES_KEY = "updates"


def _fail(exc):
    raise ValidationError({"detail": str(exc)})


class BackupsView(APIView):
    parser_classes = [JSONParser]

    def get(self, request):
        require(request.user, "settings.view")
        return Response({"items": backup.list_backups(), "config": backup.config(), "dir": str(backup.backup_dir())})

    def post(self, request):
        require(request.user, "settings.edit")
        try:
            return Response(backup.make_backup("manual"))
        except backup.BackupError as exc:
            _fail(exc)

    def put(self, request):
        require(request.user, "settings.edit")
        return Response(backup.save_config(request.data))


class BackupFileView(APIView):
    def get(self, request, name):
        require(request.user, "settings.edit")
        try:
            file = backup.path_of(name)
        except backup.BackupError as exc:
            _fail(exc)
        return FileResponse(open(file, "rb"), as_attachment=True, filename=file.name)

    def delete(self, request, name):
        require(request.user, "settings.edit")
        try:
            backup.path_of(name).unlink()
        except backup.BackupError as exc:
            _fail(exc)
        return Response(status=204)


def _updates_state():
    cfg = SystemSetting.read(UPDATES_KEY, {}) or {}
    last = INSTANCE_DIR / "updates" / "last.json"
    rollback_dir = INSTANCE_DIR / "updates" / "rollback"
    return {
        "version": settings.APP_VERSION,
        "pending": updater.pending(INSTANCE_DIR),
        "last": json.loads(last.read_text(encoding="utf-8")) if last.exists() else None,
        "rollback_versions": sorted((p.name for p in rollback_dir.iterdir() if p.is_dir()), key=updater.version_tuple)
        if rollback_dir.exists() else [],
        "feed_url": cfg.get("feed_url", ""),
        "docker": bool(os.environ.get("CRM_DOCKER")),
    }


def _no_docker():
    if os.environ.get("CRM_DOCKER"):
        raise ValidationError({"detail": "În Docker programul se actualizează cu imaginea nouă: "
                                         "docker compose pull && docker compose up -d."})


def _stage(file: Path):
    _no_docker()
    try:
        updater.stage(file, INSTANCE_DIR, license.PUBLIC_KEY_B64, settings.APP_VERSION)
    except updater.UpdateError as exc:
        _fail(exc)


class UpdatesView(APIView):
    parser_classes = [JSONParser, MultiPartParser]

    def get(self, request):
        require(request.user, "settings.view")
        return Response(_updates_state())

    def put(self, request):
        """Adresa de unde se verifică versiunile noi (pusă de producător)."""
        require(request.user, "settings.edit")
        url = (request.data.get("feed_url") or "").strip()
        if url and not url.startswith(("https://", "http://")):
            raise ValidationError({"feed_url": "Adresa trebuie să înceapă cu https://"})
        SystemSetting.write(UPDATES_KEY, {"feed_url": url})
        return Response(_updates_state())

    def delete(self, request):
        require(request.user, "settings.edit")
        updater.cancel_pending(INSTANCE_DIR)
        return Response(_updates_state())


class UpdateUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        require(request.user, "settings.edit")
        upload = request.FILES.get("package")
        if upload is None:
            raise ValidationError({"detail": "Alegeți fișierul pachetului (crm-update-....zip)."})
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "package.zip"
            with open(file, "wb") as fh:
                for chunk in upload.chunks():
                    fh.write(chunk)
            _stage(file)
        return Response(_updates_state())


class UpdateCheckView(APIView):
    """Verifică adresa de actualizări: {"version", "url", "notes_ro", "notes_ru"}; cu download=true descarcă și pregătește."""

    parser_classes = [JSONParser]

    def post(self, request):
        require(request.user, "settings.edit")
        url = (SystemSetting.read(UPDATES_KEY, {}) or {}).get("feed_url")
        if not url:
            raise ValidationError({"detail": "Adresa de actualizări nu este setată."})
        try:
            feed = requests.get(url, timeout=20).json()
        except (requests.RequestException, ValueError) as exc:
            _fail(f"Adresa de actualizări nu răspunde: {exc}")
        newer = updater.version_tuple(feed.get("version", "0")) > updater.version_tuple(settings.APP_VERSION)
        result = {"latest": feed.get("version"), "newer": newer, "notes_ro": feed.get("notes_ro", ""),
                  "notes_ru": feed.get("notes_ru", "")}
        if newer and request.data.get("download"):
            with tempfile.TemporaryDirectory() as tmp:
                file = Path(tmp) / "package.zip"
                try:
                    with requests.get(feed["url"], stream=True, timeout=60) as resp:
                        resp.raise_for_status()
                        with open(file, "wb") as fh:
                            for chunk in resp.iter_content(1 << 20):
                                fh.write(chunk)
                except (requests.RequestException, KeyError) as exc:
                    _fail(f"Pachetul nu s-a descărcat: {exc}")
                _stage(file)
        return Response({**result, **_updates_state()})


class UpdateInstallView(APIView):
    """Repornește serverul: supervizorul (run.py) aplică pachetul, face copia bazei și migrațiile."""

    def post(self, request):
        require(request.user, "settings.edit")
        _no_docker()
        if not updater.pending(INSTANCE_DIR):
            raise ValidationError({"detail": "Nu este pregătită nicio actualizare."})
        try:
            backup.make_backup("update")
        except backup.BackupError as exc:
            _fail(exc)
        request_restart()
        return Response({"restarting": True})


urlpatterns = [
    path("backups/", BackupsView.as_view()),
    path("backups/<str:name>/", BackupFileView.as_view()),
    path("updates/", UpdatesView.as_view()),
    path("updates/upload/", UpdateUploadView.as_view()),
    path("updates/check/", UpdateCheckView.as_view()),
    path("updates/install/", UpdateInstallView.as_view()),
    path("marked/", deletion.MarkedView.as_view()),
    path("marked/check/", deletion.MarkedCheckView.as_view()),
    path("marked/delete/", deletion.MarkedDeleteView.as_view()),
    path("marked/unmark/", deletion.MarkedUnmarkView.as_view()),
]
