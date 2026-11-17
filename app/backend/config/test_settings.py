"""Setări pentru testele automate: instanță temporară, bază SQLite, fără repornire."""
import os
import tempfile

os.environ.setdefault("CRM_INSTANCE_DIR", tempfile.mkdtemp(prefix="crm-test-"))
os.environ["CRM_NO_RESTART"] = "1"

from .settings import *  # noqa: E402,F403
from .instance import INSTANCE_DIR  # noqa: E402

SETUP_MODE = False
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(INSTANCE_DIR / "test.sqlite3")}}
MEDIA_ROOT = INSTANCE_DIR / "media"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
IMPORT_INLINE = True  # sincronizarea 1C rulează imediat în teste (nu în fundal)
CRM_EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"  # e-mailurile rămân în memorie (django.core.mail.outbox)
EXCHANGE_NO_KICK = True

PRODUCT_PROFILE = "cadre"
