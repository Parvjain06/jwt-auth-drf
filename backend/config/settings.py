"""
Django settings for the JWT authentication project.

Secrets are read from environment variables (optionally loaded from a local
.env file). Nothing secret is hard-coded in this file.
"""
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env for local development. Real environment variables take precedence.
load_dotenv(BASE_DIR / ".env", override=False)


def env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("replace-with"):
        raise ImproperlyConfigured(
            f"Environment variable {name} is not set. "
            "Copy .env.example to .env and fill it in."
        )
    return value


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
SECRET_KEY = env_required("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
# Render sets this to the service's public hostname (e.g. jwt-drf-demo.onrender.com).
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])

# Origins allowed to send CSRF-protected requests (only needed if the frontend
# is served from a different domain than the API).
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# Behind Render's HTTPS proxy: trust its header so Django knows the request was HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    # Local
    "accounts",
    "dogs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # serves the built React app and static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# The React app, built into this folder (frontend: `npm run build`).
# WhiteNoise serves its files (e.g. /assets/app.js) and config.urls serves index.html at "/".
FRONTEND_DIST = BASE_DIR / "frontend_dist"
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# The throttle counters live in the default cache. LocMem is fine for a single
# development process; use Redis/Memcached when running several workers.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --------------------------------------------------------------------------
# Session / CSRF cookies (used by the session-authentication comparison)
# --------------------------------------------------------------------------
COOKIE_SECURE = env_bool("COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_HTTPONLY = True          # JavaScript cannot read the session id
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = COOKIE_SECURE
CSRF_COOKIE_SECURE = COOKIE_SECURE
SESSION_COOKIE_AGE = 60 * 60 * 24       # 1 day, to mirror the refresh-token lifetime

# --------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------
LOGIN_THROTTLE_RATE = os.environ.get("LOGIN_THROTTLE_RATE", "5/min")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "login": LOGIN_THROTTLE_RATE,
    },
    # Use REMOTE_ADDR for throttling. With the default (None) DRF trusts the
    # client-supplied X-Forwarded-For header, which lets an attacker dodge the
    # login throttle by sending a different fake IP on every request.
    # Set this to the number of trusted reverse proxies when deployed behind one.
    "NUM_PROXIES": int(os.environ.get("NUM_PROXIES", "0")),
}

# --------------------------------------------------------------------------
# SimpleJWT
# --------------------------------------------------------------------------
JWT_SIGNING_KEY = env_required("JWT_SIGNING_KEY")
if len(JWT_SIGNING_KEY) < 32:
    raise ImproperlyConfigured("JWT_SIGNING_KEY must be at least 32 characters for HS256.")
if JWT_SIGNING_KEY == SECRET_KEY:
    raise ImproperlyConfigured("JWT_SIGNING_KEY must be different from DJANGO_SECRET_KEY.")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,        # /refresh/ returns a new refresh token...
    "BLACKLIST_AFTER_ROTATION": True,     # ...and blacklists the one it replaced
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "LEEWAY": 0,
}

# --------------------------------------------------------------------------
# The Dog API (server-side only; the key never reaches the client)
# --------------------------------------------------------------------------
DOG_API_BASE_URL = os.environ.get("DOG_API_BASE_URL", "https://api.thedogapi.com/v1")
DOG_API_KEY = os.environ.get("DOG_API_KEY", "")
DOG_API_TIMEOUT_SECONDS = float(os.environ.get("DOG_API_TIMEOUT_SECONDS", "5"))

# --------------------------------------------------------------------------
# Tests: record every test outcome to test_results/latest.md
# --------------------------------------------------------------------------
TEST_RUNNER = "config.test_runner.RecordingTestRunner"
