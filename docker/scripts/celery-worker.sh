#!/bin/bash
set -e

# Очікуємо готовності бази даних та Redis
until python manage.py check --database default; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - executing command"

exec celery -A config.celery worker --loglevel=info
