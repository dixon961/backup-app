#!/bin/bash
set -e

CRONTAB_FILE="/etc/cron.d/backup-cron"

echo "Шаг 1: Подготовка переменных окружения для cron..."
# Очищаем и заполняем /etc/environment для cron
> /etc/environment
printenv >> /etc/environment
echo "Переменные окружения подготовлены."
echo "---"

echo "Шаг 2: Генерация crontab..."
python3 /app/generate_crontab.py > "$CRONTAB_FILE"

# Проверяем, что файл crontab был создан и не пустой
if [ -s "$CRONTAB_FILE" ]; then
    echo "Crontab успешно сгенерирован:"
    cat "$CRONTAB_FILE"
    chmod 0644 "$CRONTAB_FILE"
else
    echo "Crontab не был сгенерирован. Задачи по расписанию выполняться не будут."
fi
echo "---"

# Шаг 3: Запуск Supervisord, который будет управлять cron и ботом
echo "Запуск Supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf