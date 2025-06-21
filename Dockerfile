FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    zip \
    cron \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем самую свежую версию rclone с помощью официального скрипта
RUN curl https://rclone.org/install.sh | bash

# Создаем директории
WORKDIR /app
RUN mkdir -p /config/rclone

# Копируем скрипты и зависимости
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

# Делаем entrypoint исполняемым
RUN chmod +x /app/entrypoint.sh

# Запускаем entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]