"""Ora documentelor după tip și închiderea perioadei (data interzicerii modificării).

- **Ora documentului**: într-o zi documentele au mereu aceeași ordine, indiferent când au fost introduse: intrările
  (08:00), mișcările interne — transfer, producție, casare, inventar (09:00), eliberările — facturi, avize, retur la
  furnizor (13:00). Lotul primește data documentului cu ora tipului lui, iar FIFO ia doar loturile intrate până la
  momentul documentului care scoate marfa. Orele se schimbă din Constante.
- **Data interzicerii modificării**: documentele cu data până la ea (inclusiv) nu se mai înregistrează, anulează sau
  modifică. O dată generală, excepții pe module (blocuri) și pe utilizatori (utilizatorul are prioritate, apoi modulul).
"""
import datetime

from django.utils import timezone

from .models import SystemSetting

TIMES_KEY = "doc_times"
CLOSING_KEY = "closing"
DEFAULT_TIMES = {"receipt": "08:00", "internal": "09:00", "issue": "13:00"}
DOC_KIND = {
    "receipt": "receipt", "opening": "receipt", "client_return": "receipt",
    "transfer": "internal", "production": "internal", "writeoff": "internal", "inventory": "internal",
    "invoice": "issue", "delivery_note": "issue", "supplier_return": "issue", "marketing": "issue",
}
KIND_ORDER = {"receipt": 0, "internal": 1, "issue": 2}
MODULE_OF = {"invoice": "invoices", "delivery_note": "invoices", "client_return": "invoices", "payment": "payments",
             "production": "production"}
MODULES = ["inventory", "invoices", "payments", "production"]


class PeriodClosed(ValueError):
    pass


def doc_times() -> dict:
    return {**DEFAULT_TIMES, **(SystemSetting.read(TIMES_KEY, {}) or {})}


def moment(day, doc_type: str, times=None) -> datetime.datetime:
    """Data documentului cu ora tipului lui (cu fus orar)."""
    times = times or doc_times()
    hh, mm = (int(x) for x in times[DOC_KIND.get(doc_type, "issue")].split(":"))
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time(hh, mm)))


def sort_key(day, doc_type: str, doc_id=0):
    """Ordinea documentelor: data, tipul (intrări, mișcări interne, eliberări), apoi numărul intern."""
    return day, KIND_ORDER[DOC_KIND.get(doc_type, "issue")], doc_id


def closing() -> dict:
    cfg = SystemSetting.read(CLOSING_KEY, {}) or {}
    return {"date": cfg.get("date") or None, "modules": cfg.get("modules") or {}, "users": cfg.get("users") or {}}


def _parse(value):
    return datetime.date.fromisoformat(value) if value else None


def closed_until(user, module: str):
    """Data până la care (inclusiv) modificarea e interzisă pentru utilizator și modul; None = nimic închis.
    Excepția utilizatorului are prioritate (gol = fără interdicție), apoi cea a modulului, apoi data generală."""
    cfg = closing()
    uid = str(getattr(user, "pk", "") or "")
    if uid and uid in cfg["users"]:
        return _parse(cfg["users"][uid])
    if module in cfg["modules"]:
        return _parse(cfg["modules"][module])
    return _parse(cfg["date"])


def check_open(day, user, doc_type: str):
    """Ridică PeriodClosed dacă data documentului e în perioada închisă pentru utilizator și modulul documentului."""
    if day is None:
        return
    if isinstance(day, datetime.datetime):
        day = day.date()
    limit = closed_until(user, MODULE_OF.get(doc_type, "inventory"))
    if limit and day <= limit:
        raise PeriodClosed(f"Perioada până la {limit:%d.%m.%Y} este închisă: documentul din {day:%d.%m.%Y} "
                           "nu se mai poate înregistra, anula sau modifica.")


def write_settings(data: dict):
    """Salvarea din Constante: {"doc_times": {...}, "closing": {"date", "modules", "users"}}."""
    if "doc_times" in data:
        times = {}
        for kind in DEFAULT_TIMES:
            value = str((data["doc_times"] or {}).get(kind) or DEFAULT_TIMES[kind])
            hh, mm = value.split(":")
            times[kind] = f"{int(hh):02d}:{int(mm):02d}"
        SystemSetting.write(TIMES_KEY, times)
    if "closing" in data:
        cfg = data["closing"] or {}
        clean = {"date": cfg.get("date") or None,
                 "modules": {m: (v or "") for m, v in (cfg.get("modules") or {}).items() if m in MODULES},
                 "users": {str(u): (v or "") for u, v in (cfg.get("users") or {}).items()}}
        for value in [clean["date"], *clean["modules"].values(), *clean["users"].values()]:
            _parse(value)  # datele greșite se resping aici
        SystemSetting.write(CLOSING_KEY, clean)
    return {"doc_times": doc_times(), "closing": closing()}
