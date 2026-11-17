"""Testele pe SQL Server (LocalDB): pytest --ds=config.test_settings_mssql. Baza de test se creează și se șterge singură."""
from .test_settings import *  # noqa: F403

DATABASES = {"default": {
    "ENGINE": "mssql", "NAME": "crm", "HOST": r"(localdb)\MSSQLLocalDB",
    "OPTIONS": {"driver": "ODBC Driver 17 for SQL Server", "extra_params": "TrustServerCertificate=yes;Trusted_Connection=yes"},
    "TEST": {"NAME": "crm_pytest"},
}}
