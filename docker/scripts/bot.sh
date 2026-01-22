#!/bin/bash
set -e

# Очікуємо готовності бази даних та Redis
until python manage.py check --database default; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - executing command"

# Виконуємо міграції (якщо потрібно)
python manage.py migrate --noinput

# Запускаємо бота
exec python manage.py run_bot
