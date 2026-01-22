#!/bin/bash
set -e

# Очікуємо готовності бази даних
until python manage.py check --database default; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - executing command"

# Виконуємо міграції
python manage.py migrate --noinput

# Збираємо статичні файли
python manage.py collectstatic --noinput

# Запускаємо Gunicorn
if [ -f "/config/gunicorn.conf.py" ]; then
    exec gunicorn config.wsgi:application --config /config/gunicorn.conf.py
else
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
fi
