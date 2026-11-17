"""Copiile de rezervă: baza de date + fișierele încărcate (poze, logo-uri), într-o arhivă ZIP în instance/backups/.

Baza se salvează după tipul ei:
- SQLite — copia exactă a bazei (API-ul de backup SQLite, include și jurnalul WAL);
- PostgreSQL — `pg_dump` (format custom), dacă programul există pe server;
- oricare altă bază (sau PostgreSQL fără pg_dump) — exportul universal al datelor (JSON), care se poate încărca
  într-o bază nouă de orice tip (`manage.py loaddata`).
"""
import datetime
import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from config.instance import INSTANCE_DIR

KEY = "backup"
DEFAULTS = {"daily": True, "keep": 14, "hour": 2}


class BackupError(RuntimeError):
    pass


def backup_dir() -> Path:
    path = INSTANCE_DIR / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config() -> dict:
    from apps.core.models import SystemSetting

    return {**DEFAULTS, **(SystemSetting.read(KEY, {}) or {})}


def save_config(data: dict) -> dict:
    from apps.core.models import SystemSetting

    cfg = config()
    if "daily" in data:
        cfg["daily"] = bool(data["daily"])
    if "keep" in data:
        cfg["keep"] = max(1, min(int(data["keep"]), 365))
    if "hour" in data:
        cfg["hour"] = max(0, min(int(data["hour"]), 23))
    SystemSetting.write(KEY, {k: cfg[k] for k in ("daily", "keep", "hour", "last_daily") if k in cfg})
    return cfg


def _dump_database(work: Path) -> tuple[Path, str]:
    db = settings.DATABASES["default"]
    if connection.vendor == "sqlite":
        target = work / "database.sqlite3"
        connection.ensure_connection()
        dst = sqlite3.connect(target)
        try:
            connection.connection.backup(dst)
        finally:
            dst.close()
        return target, "sqlite"
    if connection.vendor == "postgresql" and shutil.which("pg_dump"):
        target = work / "database.pgdump"
        env = {**os.environ, "PGPASSWORD": db.get("PASSWORD") or ""}
        cmd = ["pg_dump", "-Fc", "-f", str(target), "-h", db.get("HOST") or "localhost", "-p", str(db.get("PORT") or 5432),
               "-U", db.get("USER") or "postgres", db["NAME"]]
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=3600)
        if proc.returncode == 0:
            return target, "pg_dump"
    from django.apps import apps

    target = work / "data.json.gz"
    historical = _applied_state_apps()
    if historical is not None:
        # Copia dinaintea actualizării: baza are încă tabelele vechi, iar modelele noi au deja coloanele noi
        # („Invalid column name”); se salvează cu modelele care corespund migrațiilor aplicate.
        with gzip.open(target, "wt", encoding="utf-8") as fh:
            _dump_models(historical, fh)
        return target, "json"
    # se exclud doar modulele instalate: dumpdata cade la o etichetă necunoscută (sessions / admin nu sunt în program)
    exclude = [x for x in ("contenttypes", "auth.permission", "sessions", "admin.logentry")
               if apps.is_installed(f"django.contrib.{x.split('.')[0]}")]
    with gzip.open(target, "wt", encoding="utf-8") as fh:
        call_command("dumpdata", natural_foreign=True, natural_primary=False, exclude=exclude, stdout=fh, verbosity=0)
    return target, "json"


SKIPPED = {"contenttypes.contenttype", "auth.permission", "sessions.session", "admin.logentry"}


def _applied_state_apps():
    """Modelele așa cum sunt acum în bază (doar migrațiile aplicate), dacă mai sunt migrații de aplicat; altfel None."""
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    if not executor.migration_plan(executor.loader.graph.leaf_nodes()):
        return None
    return executor._create_project_state(with_applied_migrations=True).apps


def _dump_models(historical, fh):
    """Același JSON ca `dumpdata` (se încarcă cu `loaddata` în versiunea de dinainte), din modelele istorice."""
    from itertools import chain

    from django.core import serializers

    models = [m for m in historical.get_models()
              if m._meta.managed and not m._meta.proxy and m._meta.label_lower not in SKIPPED]
    objects = chain.from_iterable(m._base_manager.order_by("pk").iterator(chunk_size=2000) for m in models)
    serializers.get_serializer("json")().serialize(objects, stream=fh, use_natural_foreign_keys=False)


def make_backup(reason: str = "manual") -> dict:
    """Creează arhiva și o întoarce ca {name, size, created, reason, method}."""
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    name = f"crm-{reason}-{stamp}.zip"
    target = backup_dir() / name
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        try:
            dump, method = _dump_database(work)
        except Exception as exc:  # noqa: BLE001
            raise BackupError(f"Baza de date nu s-a putut salva: {exc}") from exc
        manifest = {"version": settings.APP_VERSION, "created": timezone.now().isoformat(), "reason": reason,
                    "method": method, "vendor": connection.vendor}
        partial = target.with_suffix(".part")
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            zf.write(dump, dump.name)
            media = Path(settings.MEDIA_ROOT)
            if media.exists():
                for file in media.rglob("*"):
                    if file.is_file():
                        zf.write(file, f"media/{file.relative_to(media).as_posix()}")
        partial.replace(target)
    if reason != "manual":
        prune(config()["keep"])
    return describe(target)


def describe(path: Path) -> dict:
    reason = path.stem.split("-")[1] if path.stem.count("-") >= 2 else ""
    method = ""
    try:
        with zipfile.ZipFile(path) as zf:
            method = json.loads(zf.read("manifest.json")).get("method", "")
    except (KeyError, zipfile.BadZipFile, ValueError):
        pass
    stat = path.stat()
    return {"name": path.name, "size": stat.st_size, "reason": reason, "method": method,
            "created": datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.timezone.utc).isoformat()}


def list_backups() -> list:
    files = sorted(backup_dir().glob("crm-*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [describe(p) for p in files]


def prune(keep: int):
    """Copiile automate (zilnice, înainte de actualizare) se păstrează doar ultimele `keep`; cele manuale rămân."""
    auto = [p for p in sorted(backup_dir().glob("crm-*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not p.name.startswith("crm-manual-")]
    for old in auto[keep:]:
        old.unlink(missing_ok=True)


def path_of(name: str) -> Path:
    path = (backup_dir() / name).resolve()
    if path.parent != backup_dir().resolve() or not path.name.startswith("crm-") or path.suffix != ".zip" or not path.exists():
        raise BackupError("Copia nu există.")
    return path


def run_daily_if_due(now=None) -> dict | None:
    """Apelată periodic de server: o copie pe zi, după ora aleasă."""
    from apps.core.models import SystemSetting

    cfg = config()
    now = now or timezone.localtime()
    if not cfg["daily"] or now.hour < cfg["hour"] or cfg.get("last_daily") == now.date().isoformat():
        return None
    result = make_backup("daily")
    stored = dict(SystemSetting.read(KEY, {}) or {})
    stored["last_daily"] = now.date().isoformat()
    stored.pop("last_error", None)
    stored.pop("last_error_at", None)
    SystemSetting.write(KEY, stored)
    return result


def record_failure(exc):
    """Copia automată nereușită: se ține minte pentru consola serverului (alertă) până la următoarea reușită."""
    from apps.core.models import SystemSetting

    try:
        stored = dict(SystemSetting.read(KEY, {}) or {})
        stored["last_error"], stored["last_error_at"] = str(exc)[:300], timezone.now().isoformat()
        SystemSetting.write(KEY, stored)
    except Exception:  # noqa: BLE001 — nici baza nu răspunde: rămâne mesajul din jurnal
        pass
