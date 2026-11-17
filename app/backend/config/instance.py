"""Fișierele instanței: configurația bazei de date și cheile secrete.

Totul se ține în directorul `instance/` (în afara codului, nu intră în git):
    instance/config.json   – tipul bazei, conexiunea, starea instalării
    instance/secret.json   – SECRET_KEY Django + cheia de criptare a parolelor
    instance/media/        – fișiere încărcate (logo-uri, ștampile...)

Directorul se poate schimba cu variabila de mediu CRM_INSTANCE_DIR.
"""
import json
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
PROJECT_DIR = BASE_DIR.parent                              # rădăcina proiectului
INSTANCE_DIR = Path(os.environ.get("CRM_INSTANCE_DIR", PROJECT_DIR / "instance")).resolve()
CONFIG_FILE = INSTANCE_DIR / "config.json"
SECRET_FILE = INSTANCE_DIR / "secret.json"

ENCRYPTED_PREFIX = "enc:"


def _ensure_dir():
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def load_secrets() -> dict:
    """Citește (sau generează la prima pornire) cheile secrete ale instanței."""
    _ensure_dir()
    if SECRET_FILE.exists():
        data = json.loads(SECRET_FILE.read_text(encoding="utf-8"))
    else:
        data = {}
    changed = False
    if not data.get("secret_key"):
        data["secret_key"] = secrets.token_urlsafe(50)
        changed = True
    if not data.get("fernet_key"):
        data["fernet_key"] = Fernet.generate_key().decode()
        changed = True
    if changed:
        SECRET_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _fernet() -> Fernet:
    return Fernet(load_secrets()["fernet_key"].encode())


def encrypt(value: str) -> str:
    if not value:
        return ""
    return ENCRYPTED_PREFIX + _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value or not value.startswith(ENCRYPTED_PREFIX):
        return value or ""
    try:
        return _fernet().decrypt(value[len(ENCRYPTED_PREFIX):].encode()).decode()
    except InvalidToken:
        return ""


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    _ensure_dir()
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CONFIG_FILE)


def is_installed() -> bool:
    return bool(load_config().get("installed"))
