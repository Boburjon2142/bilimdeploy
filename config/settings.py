import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- Core ---
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
# Allow localhost/127.0.0.1 by default so local dev doesn't 400.
default_hosts = "127.0.0.1,localhost,bilimstore.uz,www.bilimstore.uz"
ALLOWED_HOSTS = [h for h in os.getenv("DJANGO_ALLOWED_HOSTS", default_hosts).split(",") if h]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "https://bilimstore.uz,https://www.bilimstore.uz",
    ).split(",")
    if origin.strip()
]

# --- Applications ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "apps.accounts.apps.AccountsConfig",
    "apps.catalog.apps.CatalogConfig",
    "apps.orders.apps.OrdersConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    ENGINE = "django.db.backends.postgresql"
    DATABASES = {
        "default": {
            "ENGINE": ENGINE,
            "NAME": parsed.path.lstrip("/") or "",
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "localhost",
            "PORT": parsed.port or "5432",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
DATABASES["default"]["CONN_MAX_AGE"] = int(os.getenv("DJANGO_CONN_MAX_AGE", "60"))

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18N ---
LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

# --- Static / Media ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Use non-manifest storage to avoid bootstrap errors before collectstatic.
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Cache ---
_redis_url = os.getenv("REDIS_URL") or os.getenv("DJANGO_REDIS_URL")
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
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "TIMEOUT": None,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "bilimstore-locmem",
            "TIMEOUT": None,
        }
    }

# --- Security ---
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "True").lower() == "true"
SESSION_COOKIE_SECURE = os.getenv("DJANGO_SESSION_COOKIE_SECURE", "True").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("DJANGO_CSRF_COOKIE_SECURE", "True").lower() == "true"
# Disable HSTS to avoid browser HTTPS pinning in local/dev; enable in prod if needed.
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# --- Logging: write errors to django.log in BASE_DIR ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "django.log",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

# --- Misc ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CART_SESSION_ID = "cart"
FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.TemporaryFileUploadHandler"]
FILE_UPLOAD_MAX_MEMORY_SIZE = 0
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "profile"
LOGOUT_REDIRECT_URL = "home"

SHOP_LAT = float(os.getenv("SHOP_LAT", "41.2995"))
SHOP_LNG = float(os.getenv("SHOP_LNG", "69.2401"))
DELIVERY_BASE_FEE_UZS = int(os.getenv("DELIVERY_BASE_FEE_UZS", "10000"))
DELIVERY_PER_KM_FEE_UZS = int(os.getenv("DELIVERY_PER_KM_FEE_UZS", "2000"))
DELIVERY_MIN_FEE_UZS = int(os.getenv("DELIVERY_MIN_FEE_UZS", "10000"))
DELIVERY_MAX_FEE_UZS = int(os.getenv("DELIVERY_MAX_FEE_UZS", "60000"))
DELIVERY_FREE_OVER_UZS = os.getenv("DELIVERY_FREE_OVER_UZS")
DELIVERY_FREE_OVER_UZS = int(DELIVERY_FREE_OVER_UZS) if DELIVERY_FREE_OVER_UZS else None
