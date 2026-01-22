#!/bin/bash
set -e

# Очікуємо готовності Redis
REDIS_URL="${CELERY_BROKER_URL:-redis://redis:6379/0}"
until python -c "import redis; r = redis.Redis.from_url('$REDIS_URL'); r.ping()" 2>/dev/null; do
  >&2 echo "Redis is unavailable - sleeping"
  sleep 1
done

>&2 echo "Redis is up - executing command"

exec celery -A config.celery beat --loglevel=info
