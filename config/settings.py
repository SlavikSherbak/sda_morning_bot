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
# Використовуємо PostgreSQL в Docker, SQLite для локальної розробки без Docker
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL:
    # PostgreSQL з DATABASE_URL
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL)
    }
else:
    # Перевіряємо чи є змінні для PostgreSQL (для Docker)
    db_engine = os.getenv("DATABASE_ENGINE", "")
    db_host = os.getenv("DATABASE_HOST", "")
    if db_engine == "postgresql" or db_host:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("DATABASE_NAME", "asd_morning_bot"),
                "USER": os.getenv("DATABASE_USER", "postgres"),
                "PASSWORD": os.getenv("DATABASE_PASSWORD", "postgres"),
                "HOST": db_host or "postgres",
                "PORT": os.getenv("DATABASE_PORT", "5432"),
            }
        }
    else:
        # SQLite3 для локальної розробки
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
# Використовуємо Redis з Docker compose (сервіс redis) або локальний Redis
# Якщо CELERY_BROKER_URL не встановлено, використовуємо REDIS_HOST (для Docker це "redis")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
# Формуємо URL на основі REDIS_HOST якщо CELERY_BROKER_URL не вказано явно
_default_redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL") or _default_redis_url
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND") or _default_redis_url
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

