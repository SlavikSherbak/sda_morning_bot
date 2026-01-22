FROM python:3.12.3-bullseye

WORKDIR /app

# Встановлюємо тільки необхідні системні пакети
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libffi-dev \
        gcc \
        libxml2 \
        libxslt-dev \
        postgresql-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Встановлюємо Python залежності
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Копіюємо код проєкту
COPY . /app

# Встановлюємо права на виконання скриптів
RUN chmod +x /app/docker/scripts/*.sh

ENV PYTHONUNBUFFERED=1

CMD ["./docker/scripts/server.sh"]
