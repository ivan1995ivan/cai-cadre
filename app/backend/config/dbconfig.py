"""Traducerea setărilor de conexiune din config.json în formatul DATABASES al Django.

Formatul din config.json (secțiunea "db"):
    {
      "engine":   "sqlite" | "postgresql" | "mysql" | "oracle" | "mssql",
      "name":     numele bazei (SQLite: calea fișierului; Oracle: service name / DSN),
      "host", "port", "user", "password" (criptată),
      "options":  {...}  – opțiuni suplimentare ale driverului
    }
"""
from pathlib import Path

from .instance import INSTANCE_DIR, decrypt

CONNECT_TIMEOUT = 10  # secunde: un server care nu răspunde nu blochează programul

# Driverele ODBC pentru SQL Server, de la cel mai nou; se ia primul instalat pe calculator
MSSQL_DRIVERS = ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "ODBC Driver 13.1 for SQL Server",
                 "ODBC Driver 13 for SQL Server", "SQL Server Native Client 11.0", "SQL Server"]
MSSQL_DRIVER_URL = "https://go.microsoft.com/fwlink/?linkid=2249006"  # ODBC Driver 18 for SQL Server (x64)


def mssql_driver() -> str | None:
    """Driverul ODBC pentru SQL Server instalat pe acest calculator (cel mai nou), sau None."""
    try:
        import pyodbc
    except ImportError:
        return None
    installed = set(pyodbc.drivers())
    return next((d for d in MSSQL_DRIVERS if d in installed), None)

ENGINES = {
    "sqlite": {
        "django": "django.db.backends.sqlite3",
        "label": "SQLite (local, un singur calculator)",
        "default_port": None,
        "modules": ["sqlite3"],
    },
    "postgresql": {
        "django": "django.db.backends.postgresql",
        "label": "PostgreSQL",
        "default_port": 5432,
        "modules": ["psycopg", "psycopg2"],
    },
    "mysql": {
        "django": "django.db.backends.mysql",
        "label": "MySQL / MariaDB",
        "default_port": 3306,
        "modules": ["MySQLdb", "pymysql"],
    },
    "mssql": {
        "django": "mssql",
        "label": "Microsoft SQL Server",
        "default_port": 1433,
        "modules": ["mssql"],
    },
    "oracle": {
        "django": "django.db.backends.oracle",
        "label": "Oracle",
        "default_port": 1521,
        "modules": ["oracledb"],
    },
}


def sqlite_path(name: str) -> str:
    path = Path(name or "crm.sqlite3")
    if not path.is_absolute():
        path = INSTANCE_DIR / path
    return str(path)


def to_django(db: dict) -> dict:
    """Construiește dicționarul de conexiune Django dintr-o secțiune "db"."""
    engine = db.get("engine", "sqlite")
    if engine not in ENGINES:
        raise ValueError(f"Tip de bază de date necunoscut: {engine}")
    options = dict(db.get("options") or {})
    result = {
        "ENGINE": ENGINES[engine]["django"],
        "NAME": db.get("name", ""),
        "USER": db.get("user", ""),
        "PASSWORD": decrypt(db.get("password", "")),
        "HOST": db.get("host", ""),
        "PORT": str(db.get("port") or ""),
        "OPTIONS": options,
    }
    if engine == "sqlite":
        result["NAME"] = sqlite_path(result["NAME"])
        result.update(USER="", PASSWORD="", HOST="", PORT="")
        # Așteaptă în loc să dea eroare imediat când alt utilizator scrie în bază.
        options.setdefault("timeout", 20)
        options.setdefault("transaction_mode", "IMMEDIATE")
        options.setdefault("init_command", "PRAGMA journal_mode=WAL;PRAGMA synchronous=NORMAL;")
    elif engine == "postgresql":
        options.setdefault("connect_timeout", CONNECT_TIMEOUT)
    elif engine == "mysql":
        options.setdefault("charset", "utf8mb4")
        options.setdefault("init_command", "SET sql_mode='STRICT_TRANS_TABLES'")
        options.setdefault("connect_timeout", CONNECT_TIMEOUT)
    elif engine == "oracle":
        options.setdefault("tcp_connect_timeout", CONNECT_TIMEOUT)
    elif engine == "mssql":
        options.setdefault("driver", mssql_driver() or MSSQL_DRIVERS[0])
        options.setdefault("extra_params", "TrustServerCertificate=yes")
        options.setdefault("connection_timeout", CONNECT_TIMEOUT)
    return result
