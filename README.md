# Automated Docker Backup Service

Простой, но мощный сервис для автоматического резервного копирования директорий с Linux-сервера в облачное хранилище по протоколу WebDAV. Сервис упакован в Docker, управляется через единый файл конфигурации и отправляет уведомления в Telegram.

## ✨ Возможности

-   **Гибкая настройка:** Управление задачами резервного копирования через один `config.yml`.
-   **Расписание:** Настройка расписания `cron` для каждой задачи или использование значения по умолчанию.
-   **Облачная синхронизация:** Использование `rclone` для загрузки архивов в любое WebDAV-совместимое хранилище (Яндекс.Диск, Google Drive и др.).
-   **Автоматическая очистка:** Удаление старых резервных копий в облаке по истечении заданного срока.
-   **Уведомления:** Отправка статуса (успех/ошибка) в Telegram.
-   **Изоляция:** Все зависимости и процессы работают внутри Docker-контейнера.

## ⚙️ Установка и настройка

**Предварительные требования:** `Docker`, `docker-compose`, `git`.

**1. Клонировать репозиторий:**
```bash
git clone https://github.com/dixon961/backup-app.git
cd backup-app
```

**2. Настроить `rclone`:**
Нам нужен файл конфигурации `rclone.conf`.
- Запустите на вашем хост-компьютере `rclone config` для интерактивной настройки подключения к вашему WebDAV-хранилищу.
- Дайте подключению имя (например, `MyCloud`).
- После настройки найдите файл `rclone.conf` (обычно в `~/.config/rclone/`) и скопируйте его в папку `config/rclone/` данного проекта.

**3. Создать и настроить `config.yml`:**
Создайте файл `config/config.yml` по этому шаблону и отредактируйте его.
```yaml
# config/config.yml
globals:
  rclone_remote_name: "MyCloud" # Имя подключения из rclone.conf
  remote_base_path: "server-backups"
  default_schedule: "0 2 * * *"
  default_retention_days: 30

telegram:
  chat_id: "123456789" # Ваш Chat ID в Telegram

tasks:
  - name: "etc-configs"
    source: "/mnt/data/etc"
    archive_prefix: "etc-backup"
    schedule: "0 3 * * 1"
    retention_days: 60
  - name: "web-data"
    source: "/mnt/data/www"
    archive_prefix: "my-site"
```

**4. Настроить `docker-compose.yml`:**
- Укажите ваш токен Telegram в `environment.TELEGRAM_TOKEN`.
- Настройте `volumes`, чтобы пробросить папки для бэкапа с хоста в контейнер. Путь слева — на хосте, справа — в контейнере (должен совпадать с `source` в `config.yml`).

**5. Запустить сервис:**
```bash
docker-compose up --build -d
```

## 🚀 Использование

-   **Просмотр логов:** `docker-compose logs -f`
-   **Остановка сервиса:** `docker-compose down`

## ⚠️ Безопасность

Папка `config/` содержит ваши секретные данные (`rclone.conf`) и добавлена в `.gitignore`. **Никогда не публикуйте содержимое этой папки.**