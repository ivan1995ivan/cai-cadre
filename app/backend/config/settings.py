"""Setările Django ale sistemului CAI CADRE.

Baza de date NU se scrie aici: vine din instance/config.json, completat de asistentul de instalare.
Până la instalare sistemul pornește în „modul instalare” cu o bază fictivă (dummy).
"""
import importlib.util
import os
from datetime import timedelta

from . import dbconfig
from .instance import BASE_DIR, INSTANCE_DIR, PROJECT_DIR, load_config, load_secrets

_CONFIG = load_config()
_SECRETS = load_secrets()

SECRET_KEY = os.environ.get("CRM_SECRET_KEY") or os.environ.get("SECRET_KEY") or _SECRETS["secret_key"]
DEBUG = os.environ.get("CRM_DEBUG", "0") == "1"
ALLOWED_HOSTS = ["*"]  # sistemul rulează în rețeaua firmei; accesul se controlează prin autentificare

# Modul instalare: configurația lipsește sau instalarea nu s-a terminat.
SETUP_MODE = not _CONFIG.get("installed")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.users",
    "apps.core",
    "apps.printing",
    "apps.org",
    "apps.staff",
    "apps.leave",
    "apps.orders",
    "apps.worktime",
    "apps.payroll",
    "apps.production",
    "apps.transport",
    "apps.alerts",
    "apps.reports",
    "apps.training",
    "apps.health",
    "apps.military",
    "apps.portal",
    "apps.setup",
    "apps.help",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.request_cache.RequestCacheMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "apps.setup.middleware.SetupModeMiddleware",
    "apps.core.license_middleware.LicenseMiddleware",
    "apps.core.audit.AuditContextMiddleware",
    "apps.core.console.ConsoleMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

# --- Baza de date --------------------------------------------------------------
if _CONFIG.get("db"):
    DATABASES = {"default": dbconfig.to_django(_CONFIG["db"])}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Intrarea în program: verificarea parolei cu PBKDF2 (1,2 milioane de iterații) ținea ~1 s pe un calculator bun și
# câteva secunde pe un server slab. Argon2 e la fel de sigur și de 10 ori mai rapid; parolele vechi (PBKDF2) merg în
# continuare și se rescriu în Argon2 la prima intrare reușită. Fără pachetul argon2-cffi rămâne PBKDF2.
PASSWORD_HASHERS = [
    *(["django.contrib.auth.hashers.Argon2PasswordHasher"] if importlib.util.find_spec("argon2") else []),
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

# --- Limbă și timp ---------------------------------------------------------------
LANGUAGE_CODE = "ro"
LANGUAGES = [("ro", "Română"), ("ru", "Русский"), ("en", "English")]
TIME_ZONE = "Europe/Chisinau"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# --- Fișiere ---------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = INSTANCE_DIR / "static"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
MEDIA_URL = "/media/"
MEDIA_ROOT = INSTANCE_DIR / "media"
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"
DOCS_DIR = PROJECT_DIR / "docs"
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None
WHITENOISE_MIMETYPES = {".webmanifest": "application/manifest+json"}
# Fișierele interfeței au numele cu amprentă (index-CulFr99i.js): browserul le ține un an, fără să mai întrebe serverul.
# Variantele comprimate (.gz / .br, făcute la `npm run build`) se servesc singure.
WHITENOISE_IMMUTABLE_FILE_TEST = r"^/assets/.+-[\w-]{8,}\.\w+$"
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# --- API -------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.users.auth.AuditedJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["apps.users.permissions.RolePermission"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "DEFAULT_FILTER_BACKENDS": [],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

APP_VERSION = "1.6.0"

# Profilul produsului: „cadre” (evidența personalului și salarizarea în instituții medicale).
PRODUCT_PROFILE = os.environ.get("CRM_PROFILE", "cadre")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {"crm": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
