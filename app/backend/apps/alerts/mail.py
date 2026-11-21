"""Trimiterea pe e-mail (serverul SMTP al întreprinderii, din Setări): rezumatul zilnic al alertelor și proba conexiunii."""
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils.html import escape

from apps.core.models import SystemSetting

SMTP_KEY = "smtp_settings"
DEFAULTS = {"host": "", "port": 587, "username": "", "password": "", "use_tls": True, "use_ssl": False, "from_email": "",
            "enabled": False}


def get_smtp(with_password=False) -> dict:
    cfg = {**DEFAULTS, **(SystemSetting.read(SMTP_KEY, {}) or {})}
    if not with_password:
        cfg["password"] = "" if not cfg.get("password") else "********"
    return cfg


def save_smtp(data: dict) -> dict:
    from config.instance import encrypt

    cfg = get_smtp(with_password=True)
    for key in ("host", "username", "from_email"):
        if key in data:
            cfg[key] = str(data.get(key) or "").strip()[:200]
    if "port" in data:
        cfg["port"] = int(data.get("port") or 587)
    for key in ("use_tls", "use_ssl", "enabled"):
        if key in data:
            cfg[key] = bool(data.get(key))
    if data.get("password") and data["password"] != "********":
        cfg["password"] = encrypt(str(data["password"]))
    SystemSetting.write(SMTP_KEY, cfg)
    return get_smtp()


def connection():
    from config.instance import decrypt

    cfg = get_smtp(with_password=True)
    if not cfg.get("enabled") or not cfg.get("host"):
        return None, cfg
    conn = get_connection("django.core.mail.backends.smtp.EmailBackend", host=cfg["host"], port=int(cfg["port"]),
                          username=cfg["username"] or None, password=decrypt(cfg["password"]) if cfg.get("password") else None,
                          use_tls=bool(cfg["use_tls"]) and not cfg["use_ssl"], use_ssl=bool(cfg["use_ssl"]), timeout=20)
    return conn, cfg


def send(to: list, subject: str, text: str, html: str = "") -> bool:
    conn, cfg = connection()
    if conn is None or not to:
        return False
    msg = EmailMultiAlternatives(subject, text, cfg["from_email"] or cfg["username"], to, connection=conn)
    if html:
        msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)
    return True


def send_digest(user, alerts: list, today) -> bool:
    """Rezumatul zilnic: alertele noi ale utilizatorului într-un singur mesaj. Eșecul trimiterii nu oprește notificările."""
    if not user.email:
        return False
    lines = [f"- {a.title}: {a.text}" for a in alerts]
    rows = "".join(f"<tr><td style='padding:4px 8px'><b>{escape(a.title)}</b></td><td style='padding:4px 8px'>{escape(a.text)}</td></tr>"
                   for a in alerts)
    subject = f"CAI CADRE: {len(alerts)} termene și alerte noi ({today:%d.%m.%Y})"
    text = "Termene și alerte noi:\n\n" + "\n".join(lines)
    html = f"<p>Termene și alerte noi:</p><table style='border-collapse:collapse;font-family:Arial;font-size:13px'>{rows}</table>"
    try:
        return send([user.email], subject, text, html)
    except Exception:  # noqa: BLE001 — serverul de e-mail indisponibil nu oprește sarcina de noapte
        return False
