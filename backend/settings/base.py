import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [
    h
    for h in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost,sinov.pythonanywhere.com,bilimstore.uz,www.bilimstore.uz",
    ).split(",")
    if h
]

# Caching:
# - DEBUG: DummyCache (no persistence) so admin o'zgarishlari darhol ko'rinadi.
# - REDIS_URL set: Redis (shared cache for multiple workers).
# - Else: LocMem (single-process fallback).
_redis_url = os.environ.get("REDIS_URL") or os.environ.get("DJANGO_REDIS_URL")
if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            "TIMEOUT": None,
        }
    }
elif _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _redis_url,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "TIMEOUT": None,  # rely on per-use timeouts
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-bilim-cache",
            "TIMEOUT": None,  # rely on per-use timeouts
        }
    }

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "apps.catalog.apps.CatalogConfig",
    "apps.orders.apps.OrdersConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.orders.context_processors.cart",
                "apps.catalog.context_processors.categories",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.backend.wsgi.application"

# Prefer DATABASE_URL (postgres), fallback to explicit env vars, then sqlite.
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    ENGINE = "django.db.backends.postgresql"
    DATABASES = {
        "default": {
            "ENGINE": ENGINE,
            "NAME": parsed.path.lstrip("/") or os.environ.get("DJANGO_DB_NAME", ""),
            "USER": parsed.username or os.environ.get("DJANGO_DB_USER", ""),
            "PASSWORD": parsed.password or os.environ.get("DJANGO_DB_PASSWORD", ""),
            "HOST": parsed.hostname or os.environ.get("DJANGO_DB_HOST", "localhost"),
            "PORT": parsed.port or os.environ.get("DJANGO_DB_PORT", "5432"),
        }
    }
else:
    engine = os.environ.get("DJANGO_DB_ENGINE", "postgresql")
    if engine in {"sqlite", "sqlite3"}:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.environ.get("DJANGO_DB_NAME", BASE_DIR / "db.sqlite3"),
            }
        }
    else:
        if "." not in engine:
            engine = f"django.db.backends.{engine}"
        DATABASES = {
            "default": {
                "ENGINE": engine,
                "NAME": os.environ.get("DJANGO_DB_NAME", "bilimstore"),
                "USER": os.environ.get("DJANGO_DB_USER", "bilimstore"),
                "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", "bilimstore"),
                "HOST": os.environ.get("DJANGO_DB_HOST", "localhost"),
                "PORT": os.environ.get("DJANGO_DB_PORT", "5432"),
            }
        }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Use manifest storage in production (needs collectstatic); simpler storage in DEBUG to avoid missing manifest errors.
if DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CART_SESSION_ID = "cart"

FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.TemporaryFileUploadHandler"]
FILE_UPLOAD_MAX_MEMORY_SIZE = 0

SHOP_LAT = float(os.environ.get("SHOP_LAT", "41.2995"))
SHOP_LNG = float(os.environ.get("SHOP_LNG", "69.2401"))
DELIVERY_BASE_FEE_UZS = int(os.environ.get("DELIVERY_BASE_FEE_UZS", "10000"))
DELIVERY_PER_KM_FEE_UZS = int(os.environ.get("DELIVERY_PER_KM_FEE_UZS", "2000"))
DELIVERY_MIN_FEE_UZS = int(os.environ.get("DELIVERY_MIN_FEE_UZS", "10000"))
DELIVERY_MAX_FEE_UZS = int(os.environ.get("DELIVERY_MAX_FEE_UZS", "60000"))
DELIVERY_FREE_OVER_UZS = os.environ.get("DELIVERY_FREE_OVER_UZS")
DELIVERY_FREE_OVER_UZS = int(DELIVERY_FREE_OVER_UZS) if DELIVERY_FREE_OVER_UZS else None
