"""Verificarea conexiunii și crearea automată a bazei de date, pentru toate tipurile suportate."""
import importlib.util
import re
from pathlib import Path

from django.db.utils import ConnectionHandler

from config.dbconfig import ENGINES, MSSQL_DRIVER_URL, mssql_driver, to_django

# Bază „de serviciu” la care ne conectăm când baza dorită nu există încă.
MAINTENANCE_DB = {"postgresql": "postgres", "mysql": "", "mssql": "master"}

PROBE_TIMEOUT = 5  # secunde

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


class DbSetupError(Exception):
    pass


def drivers() -> list:
    """Tipurile de baze și dacă driverul lor e instalat pe acest calculator."""
    result = []
    for code, info in ENGINES.items():
        available = any(importlib.util.find_spec(m) is not None for m in info["modules"])
        item = {"code": code, "label": info["label"], "default_port": info["default_port"], "available": available}
        if code == "mssql" and available:
            # pe lângă biblioteca Python, SQL Server cere driverul ODBC de la Microsoft instalat în Windows
            item["odbc"] = mssql_driver() or ""
            item["available"] = bool(item["odbc"])
            item["install_url"] = MSSQL_DRIVER_URL
        result.append(item)
    return result


def _no_odbc() -> str:
    return ("Pe acest calculator nu e instalat driverul ODBC pentru SQL Server. Instalați „ODBC Driver 18 for SQL "
            f"Server” de la Microsoft ({MSSQL_DRIVER_URL}), apoi apăsați din nou „Testează conexiunea”.")


def _connect(db: dict, *, name=None, user=None, password=None):
    cfg = dict(db)
    # Testul din asistent trebuie să răspundă repede chiar dacă serverul nu există.
    timeout_key = {"postgresql": "connect_timeout", "mysql": "connect_timeout",
                   "oracle": "tcp_connect_timeout", "mssql": "connection_timeout"}.get(cfg.get("engine"))
    if timeout_key:
        cfg["options"] = {**(cfg.get("options") or {}), timeout_key: PROBE_TIMEOUT}
    if name is not None:
        cfg["name"] = name
    if user:
        cfg["user"], cfg["password"] = user, password or ""
    settings_dict = to_django(cfg)
    handler = ConnectionHandler({"default": settings_dict})
    conn = handler["default"]
    conn.ensure_connection()
    return conn


def _friendly(exc: Exception) -> str:
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    lowered = text.lower()
    if "im002" in lowered:  # ODBC: driverul cerut nu e instalat
        return _no_odbc()
    if any(s in lowered for s in ("password authentication failed", "access denied", "ora-01017", "login failed")):
        return f"Utilizator sau parolă greșită. ({text})"
    if any(s in lowered for s in ("could not connect", "connection refused", "can't connect", "timeout",
                                  "timed out", "ora-12541", "ora-12514", "no such host", "unknown host",
                                  "name or service not known")):
        return f"Serverul nu răspunde. Verificați adresa, portul și firewall-ul. ({text})"
    return text


def _crm_tables(conn) -> tuple[bool, int]:
    tables = {t.lower() for t in conn.introspection.table_names()}
    has_crm = "django_migrations" in tables and "core_company" in tables
    return has_crm, len(tables)


OTHER_PRODUCT = "Baza aparține altui program CAI (CAI ERP / CAI ERP Vânzări). CAI CADRE n-o poate folosi: ar transforma-o și celălalt program n-ar mai merge cu ea. Alegeți o bază goală sau o bază CAI ERP Vânzări."


def _other_product(conn) -> bool:
    """Baza CRM e a lui CAI ERP pentru acoperișuri: are sistemul, dar nu și migrările Vânzări (sortimentul clienților)."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = %s", ["assortment"])
        return cursor.fetchone()[0] == 0


def _unfinished(conn) -> bool:
    """Sistemul CRM e în bază, dar fără niciun utilizator: instalarea anterioară s-a oprit la jumătate (de ex. a căzut o
    migrare). Asistentul o continuă ca pe o instalare nouă — firma și administratorul — fără să șteargă ceva."""
    tables = {t.lower() for t in conn.introspection.table_names()}
    if "users_user" not in tables:
        return True
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users_user")
        return cursor.fetchone()[0] == 0


def probe(db: dict) -> dict:
    """Testează conexiunea. Întoarce:
    server_ok – serverul răspunde și datele de acces sunt corecte
    database_exists – baza (schema) există
    has_crm – baza conține deja sistemul CRM (se va actualiza, nu se șterge nimic)
    table_count – câte tabele are baza (o bază străină, nevidă, e semnalată)
    """
    engine = db.get("engine")
    if engine not in ENGINES:
        raise DbSetupError("Alegeți tipul bazei de date.")
    result = {"server_ok": False, "database_exists": False, "has_crm": False, "unfinished": False, "table_count": 0,
              "version": "", "error": "", "other_product": False}

    if engine == "mssql" and not (db.get("options") or {}).get("driver") and mssql_driver() is None:
        result["error"] = _no_odbc()
        return result

    if engine == "sqlite":
        path = Path(to_django(db)["NAME"])
        result["server_ok"] = True
        result["database_exists"] = path.exists()
        if path.exists():
            conn = _connect(db)
            try:
                result["has_crm"], result["table_count"] = _crm_tables(conn)
                result["unfinished"] = result["has_crm"] and _unfinished(conn)
                result["other_product"] = result["has_crm"] and not result["unfinished"] and _other_product(conn)
                if result["other_product"]:
                    result["error"] = OTHER_PRODUCT
                result["version"] = "SQLite " + conn.Database.sqlite_version
            finally:
                conn.close()
        return result

    try:
        conn = _connect(db)
    except Exception as exc:  # noqa: BLE001 – fiecare driver are excepțiile lui
        first_error = _friendly(exc)
        # Serverul nu răspunde deloc sau parola e greșită: a doua încercare nu ajută, doar întârzie.
        if first_error.startswith(("Serverul nu răspunde", "Utilizator sau parolă greșită")):
            result["error"] = first_error
            return result
        if engine in MAINTENANCE_DB:
            try:
                conn = _connect(db, name=MAINTENANCE_DB[engine])
            except Exception as exc2:  # noqa: BLE001
                result["error"] = _friendly(exc2)
                return result
            result["server_ok"] = True
            result["version"] = _version(conn)
            conn.close()
            return result
        result["error"] = first_error
        return result

    try:
        result["server_ok"] = True
        result["database_exists"] = True
        result["version"] = _version(conn)
        result["has_crm"], result["table_count"] = _crm_tables(conn)
        result["unfinished"] = result["has_crm"] and _unfinished(conn)
        result["other_product"] = result["has_crm"] and not result["unfinished"] and _other_product(conn)
        if result["other_product"]:
            result["error"] = OTHER_PRODUCT
    finally:
        conn.close()
    return result


def _version(conn) -> str:
    vendor = conn.vendor
    try:
        with conn.cursor() as cursor:
            if vendor == "postgresql":
                cursor.execute("SHOW server_version")
                return "PostgreSQL " + cursor.fetchone()[0]
            if vendor == "mysql":
                cursor.execute("SELECT VERSION()")
                return "MySQL/MariaDB " + cursor.fetchone()[0]
            if vendor == "microsoft":
                cursor.execute("SELECT CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(50))")
                return "SQL Server " + cursor.fetchone()[0]
            if vendor == "oracle":
                return "Oracle " + conn.oracle_full_version
    except Exception:  # noqa: BLE001
        pass
    return vendor


def create_database(db: dict, admin_user: str = "", admin_password: str = "") -> str:
    """Creează baza de date (sau schema, la Oracle). Întoarce un mesaj pentru utilizator.

    admin_user/admin_password – un cont cu drept de creare, dacă utilizatorul aplicației nu îl are.
    """
    engine = db.get("engine")
    name = (db.get("name") or "").strip()

    if engine == "sqlite":
        path = Path(to_django(db)["NAME"])
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = _connect(db)
        conn.close()
        return f"Fișierul bazei de date a fost creat: {path}"

    target = db.get("user") if engine == "oracle" else name
    if not target or not IDENTIFIER.match(target):
        raise DbSetupError(
            "Numele bazei (la Oracle: utilizatorul/schema) poate conține doar litere latine, cifre și „_” "
            "și trebuie să înceapă cu o literă."
        )

    try:
        if engine == "oracle":
            conn = _connect(db, user=admin_user, password=admin_password)
        else:
            conn = _connect(db, name=MAINTENANCE_DB[engine], user=admin_user, password=admin_password)
    except Exception as exc:  # noqa: BLE001
        raise DbSetupError(_friendly(exc)) from exc

    app_password = db.get("password", "")
    try:
        with conn.cursor() as cursor:
            if engine == "postgresql":
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", [name])
                if cursor.fetchone():
                    return f"Baza „{name}” există deja."
                owner = f' OWNER "{db["user"]}"' if admin_user and db.get("user") and IDENTIFIER.match(db["user"]) else ""
                cursor.execute(f"CREATE DATABASE \"{name}\" ENCODING 'UTF8'{owner}")
            elif engine == "mysql":
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                if admin_user and db.get("user") and db["user"] != admin_user:
                    cursor.execute(f"GRANT ALL PRIVILEGES ON `{name}`.* TO %s@'%%'", [db["user"]])
            elif engine == "mssql":
                cursor.execute(f"IF DB_ID(N'{name}') IS NULL CREATE DATABASE [{name}]")
            elif engine == "oracle":
                if '"' in app_password:
                    raise DbSetupError("Parola pentru Oracle nu poate conține ghilimele.")
                cursor.execute("SELECT COUNT(*) FROM dba_users WHERE username = UPPER(%s)", [target])
                if cursor.fetchone()[0]:
                    return f"Schema „{target}” există deja."
                cursor.execute(
                    f'CREATE USER {target} IDENTIFIED BY "{app_password}" '
                    f"DEFAULT TABLESPACE USERS QUOTA UNLIMITED ON USERS"
                )
                cursor.execute(
                    f"GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE VIEW, "
                    f"CREATE PROCEDURE, CREATE TRIGGER TO {target}"
                )
    except DbSetupError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DbSetupError(f"Baza nu a putut fi creată: {_friendly(exc)}") from exc
    finally:
        conn.close()
    return f"Baza de date „{target}” a fost creată."
