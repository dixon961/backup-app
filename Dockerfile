FROM python:3.10-slim

# Устанавливаем системные зависимости: rclone, zip и cron
RUN apt-get update && apt-get install -y --no-install-recommends \
    rclone \
    zip \
    cron \
    && rm -rf /var/lib/apt/lists/*

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