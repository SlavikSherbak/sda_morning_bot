"""
Django settings for asd_morning_bot project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition
INSTALLED_APPS = [
    "grappelli",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_celery_beat",
    "core",
    "bot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database

db_host = os.getenv("DB_HOST") or os.getenv("DATABASE_HOST", "")
db_name = (
    os.getenv("DB_DATABASE")
    or os.getenv("DB_NAME")
    or os.getenv("DATABASE_NAME", "")
)
db_user = os.getenv("DB_USER") or os.getenv("DATABASE_USER", "")
db_password = os.getenv("DB_PASSWORD") or os.getenv("DATABASE_PASSWORD", "")
db_port = os.getenv("DB_PORT") or os.getenv("DATABASE_PORT", "5432")

def is_valid_db_value(value):
    if not value:
        return False
    if value.strip() == "://" or value.strip().startswith("://"):
        return False
    return True

# Перевіряємо наявність значень (зашифровані DigitalOcean значення EV[1:...] також вважаються валідними)
# і що вони не є явно неправильними (наприклад, "://")
if db_host and db_name and db_user and is_valid_db_value(db_host) and is_valid_db_value(db_name) and is_valid_db_value(db_user):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
        }
    }
else:
    _url = os.getenv("DATABASE_URL", "")
    if _url and _url.strip() != "://" and not _url.startswith("EV[") and not _url.strip().startswith("://") and _url.startswith(("postgres://", "postgresql://", "pgsql://")):
        import dj_database_url
        try:
            DATABASES = {"default": dj_database_url.parse(_url)}
        except Exception as e:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                f"Invalid DATABASE_URL: {e}. Use DB_HOST, DB_USER, DB_PASSWORD, "
                "DB_DATABASE, DB_PORT instead (e.g. on DigitalOcean App Platform)."
            ) from e
    else:
        db_engine = os.getenv("DATABASE_ENGINE", "")
        if db_engine or db_name or db_user or db_host:
            DATABASES = {
                "default": {
                    "ENGINE": "django.db.backends.postgresql",
                    "NAME": db_name or os.getenv("DATABASE_NAME", "asd_morning_bot"),
                    "USER": db_user or os.getenv("DATABASE_USER", "postgres"),
                    "PASSWORD": db_password or os.getenv("DATABASE_PASSWORD", ""),
                    "HOST": db_host or os.getenv("DATABASE_HOST", "localhost"),
                    "PORT": db_port or os.getenv("DATABASE_PORT", "5432"),
                }
            }
        else:
            # Fallback до SQLite
            DATABASES = {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": BASE_DIR / "db.sqlite3",
                }
            }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
] if (BASE_DIR / "static").exists() else []

# Grappelli settings
GRAPPELLI_ADMIN_TITLE = "ASD Morning Bot Admin"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery Configuration
# REDIS_URL (App Platform) або CELERY_BROKER_URL / REDIS_HOST (Docker)
_redis_url = os.getenv("REDIS_URL", "")
if _redis_url:
    CELERY_BROKER_URL = _redis_url
    CELERY_RESULT_BACKEND = _redis_url
elif os.getenv("CELERY_BROKER_URL"):
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND") or CELERY_BROKER_URL
else:
    _h = os.getenv("REDIS_HOST", "redis")
    _p = os.getenv("REDIS_PORT", "6379")
    _d = os.getenv("REDIS_DB", "0")
    _default = f"redis://{_h}:{_p}/{_d}"
    CELERY_BROKER_URL = _default
    CELERY_RESULT_BACKEND = _default
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Celery Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "send-inspirations-to-users": {
        "task": "bot.tasks.send_inspirations_to_users",
        "schedule": crontab(minute="*/5"),  # Кожні 5 хвилин
    },
}

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# EGW Writings API Configuration
EGW_API_AUTH_TOKEN = os.getenv("EGW_API_AUTH_TOKEN", "")

