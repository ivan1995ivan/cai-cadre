"""Sarcinile de noapte ale serverului (o dată pe zi, după ora din setări). Modulele de cadre își înregistrează aici
sarcinile (notificările de termene, închiderea perioadelor) prin `TASKS`."""
from django.utils import timezone

from .models import SystemSetting

KEY = "nightly"
DEFAULT_HOUR = 3


def run_if_due(now=None) -> dict | None:
    """Rulează sarcinile o singură dată pe zi, după ora stabilită. Întoarce rezultatul sau None dacă nu era timpul."""
    now = now or timezone.localtime()
    cfg = SystemSetting.read(KEY, {}) or {}
    hour = int(cfg.get("hour", DEFAULT_HOUR))
    if now.hour < hour or cfg.get("last_run") == now.date().isoformat():
        return None
    result = run_all(now.date())
    SystemSetting.write(KEY, {**cfg, "last_run": now.date().isoformat(), "last_result": result})
    return result


# (nume, funcție(today) -> rezultat) — modulele adaugă sarcini la pornire (apps.py → ready)
TASKS: list = []


def run_all(today) -> dict:
    result = {}
    for name, task in TASKS:
        try:
            result[name] = task(today)
        except Exception as exc:  # noqa: BLE001 – o sarcină nereușită nu le oprește pe celelalte
            result[f"{name}_error"] = str(exc)
    return result
