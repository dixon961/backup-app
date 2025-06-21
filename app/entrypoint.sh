#!/bin/bash
set -e

CRONTAB_FILE="/etc/cron.d/backup-cron"

echo "Шаг 1: Подготовка переменных окружения для cron..."
# Очищаем файл /etc/environment
> /etc/environment
# Записываем в него все переменные окружения, которые были переданы в контейнер
printenv >> /etc/environment
echo "Переменные окружения подготовлены."
echo "---"

echo "Шаг 2: Генерация crontab..."
python3 /app/generate_crontab.py > "$CRONTAB_FILE"

# Проверяем, что файл crontab был создан и не пустой
if [ -s "$CRONTAB_FILE" ]; then
    echo "Crontab успешно сгенерирован:"
    cat "$CRONTAB_FILE"
    echo "---"
    chmod 0644 "$CRONTAB_FILE"
    
    echo "Шаг 3: Запуск cron в foreground режиме..."
    exec cron -f
else
    echo "Crontab не был сгенерирован (конфиг пуст или отсутствует). Сервис в режиме ожидания."
    exec tail -f /dev/null
fi