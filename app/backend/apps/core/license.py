"""Licența sistemului.

O licență este textul `<payload base64>.<semnătură base64>`, semnat Ed25519 cu cheia privată a
producătorului (tools/license_tool.py). Sistemul verifică semnătura cu cheia publică de mai jos,
deci o licență nu poate fi modificată sau falsificată de client.

Fără licență sistemul rulează în regim de probă (TRIAL_DAYS zile, toate modulele).
"""
import base64
import datetime
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .models import Company, SystemSetting

# Cheia publică a producătorului (perechea privată NU se află în cod).
PUBLIC_KEY_B64 = "KhcxXNz-VcJ4NGyFsxNrG79S8OFjTq4Oz95FfqmDSto"

TRIAL_DAYS = 30
TRIAL_MAX_USERS = 10

# Modulele licenței CAI CADRE: cadrele (de bază, mereu) și salarizarea (livrarea „cu salariu”, se licențiază separat).
LICENSED_MODULES = ["cadre", "payroll"]
PAID_MODULES = ["payroll"]
# Drepturile din registrul de roluri care țin de un modul plătit.
PERMISSION_MODULES = {"payroll": "payroll", "payroll_settings": "payroll", "tax_reports": "payroll"}
# Adresele API ale modulelor plătite (calculul, plata, raportările IPC21 / IALS21 / IRM19).
API_MODULES = {"/api/payroll/": "payroll"}
# În regimul „doar citire” (licența expirată) rămân permise: intrarea, profilul, licența, notificările și evenimentele externe.
READ_ONLY_ALLOWED = ("/api/setup/", "/api/auth/", "/api/license/", "/api/system/", "/api/notifications/", "/api/help/", "/api/telephony/",
                     "/api/hub/")
WARN_DAYS = 14

from .license_plans import PLANS, check_plan, plan_for  # noqa: E402,F401 — treptele (fără Django, și pentru tools/)


def active_users() -> int:
    from apps.users.models import User

    return User.objects.filter(is_active=True).count()


class LicenseError(Exception):
    pass


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def verify(license_text: str) -> dict:
    try:
        payload_b64, signature_b64 = license_text.strip().split(".")
        payload = _b64decode(payload_b64)
        signature = _b64decode(signature_b64)
    except ValueError as exc:
        raise LicenseError("Formatul licenței este greșit.") from exc
    try:
        Ed25519PublicKey.from_public_bytes(_b64decode(PUBLIC_KEY_B64)).verify(signature, payload)
    except (InvalidSignature, ValueError) as exc:
        raise LicenseError("Semnătura licenței nu este validă.") from exc
    return json.loads(payload)


def status() -> dict:
    """Starea curentă a licenței, pentru interfață și verificări."""
    today = datetime.date.today()
    text = SystemSetting.read("license", {}).get("text")
    if text:
        try:
            data = verify(text)
        except LicenseError as exc:
            return {"mode": "invalid", "error": str(exc), "modules": [], "max_users": 1, "valid": False}
        valid_until = datetime.date.fromisoformat(data["valid_until"]) if data.get("valid_until") else None
        expired = bool(valid_until and valid_until < today)
        company = Company.get()
        idno_ok = not data.get("idno") or data["idno"] == company.idno
        max_users = data.get("max_users", 1)
        plan = data.get("plan") if data.get("plan") in PLANS else plan_for(max_users)
        return {
            "plan": plan, "plan_name": PLANS[plan]["name"],
            "mode": "licensed",
            "valid": not expired and idno_ok,
            "error": "" if idno_ok else "Licența este emisă pentru alt IDNO.",
            "company": data.get("company", ""),
            "idno": data.get("idno", ""),
            "max_users": data.get("max_users", 1),
            "modules": data.get("modules", LICENSED_MODULES),
            "valid_until": data.get("valid_until"),
            "expired": expired,
        }
    installed = Company.get().installed_at.date()
    ends = installed + datetime.timedelta(days=TRIAL_DAYS)
    return {
        "plan": "trial", "plan_name": "Trial",
        "mode": "trial",
        "valid": ends >= today,
        "error": "",
        "max_users": TRIAL_MAX_USERS,
        "modules": LICENSED_MODULES,
        "valid_until": ends.isoformat(),
        "expired": ends < today,
        "days_left": max((ends - today).days, 0),
    }


def summary(status_: dict | None = None) -> dict:
    """Ce trebuie să știe orice utilizator: regimul, zilele rămase, dacă sistemul e doar pentru citire."""
    s = status_ or status()
    days_left = None
    if s.get("valid_until"):
        days_left = (datetime.date.fromisoformat(s["valid_until"]) - datetime.date.today()).days
    return {"mode": s["mode"], "valid": s["valid"], "read_only": not s["valid"], "error": s.get("error", ""),
            "valid_until": s.get("valid_until"), "days_left": days_left,
            "warn": bool(s["valid"] and days_left is not None and days_left <= WARN_DAYS),
            "modules": s.get("modules", [])}


def enabled_modules(status_: dict | None = None) -> set:
    s = status_ or status()
    return set(s.get("modules") or []) | (set(LICENSED_MODULES) - set(PAID_MODULES))


def module_enabled(module: str) -> bool:
    return module not in PAID_MODULES or module in enabled_modules()


def api_module(path: str) -> str | None:
    return next((m for prefix, m in API_MODULES.items() if path.startswith(prefix)), None)


def with_usage(status_: dict | None = None) -> dict:
    """Starea licenței cu utilizatorii activi și treptele (pentru pagina „Licență”)."""
    s = dict(status_ or status())
    s["active_users"] = active_users()
    s["over_limit"] = s["active_users"] > s.get("max_users", 0)
    s["plans"] = [{"key": k, "name": p["name"], "min": p["min"], "max": p["max"]} for k, p in PLANS.items()]
    return s


def install(license_text: str) -> dict:
    verify(license_text)
    SystemSetting.write("license", {"text": license_text.strip()})
    return status()
