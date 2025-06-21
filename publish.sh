#!/bin/bash
# Скрипт для сборки и публикации Docker-образа в Docker Hub.

# Прерываем выполнение при любой ошибке
set -e

# --- НАСТРОЙКИ ---
# Укажи здесь свой логин на Docker Hub
DOCKER_HUB_USERNAME="твой_логин_здесь" 
# Имя образа
IMAGE_NAME="backup-service"
# Версия образа
VERSION="1.0"

# --- ЛОГИКА СКРИПТА ---

if [ "$DOCKER_HUB_USERNAME" == "твой_логин_здесь" ]; then
    echo "Ошибка: Пожалуйста, укажите ваш логин Docker Hub в переменной DOCKER_HUB_USERNAME в скрипте publish.sh"
    exit 1
fi

# Полный тег образа
FULL_IMAGE_TAG="$DOCKER_HUB_USERNAME/$IMAGE_NAME:$VERSION"
LATEST_TAG="$DOCKER_HUB_USERNAME/$IMAGE_NAME:latest"

echo "Шаг 1: Вход в Docker Hub..."
docker login -u "$DOCKER_HUB_USERNAME"

echo "Шаг 2: Сборка Docker-образа..."
# Мы используем docker-compose для сборки, так как он уже знает, как это делать
docker-compose build

echo "Шаг 3: Тегирование образа для публикации..."
# docker-compose создает образ с именем по умолчанию, обычно 'папка_имя-сервиса'
# В нашем случае это будет 'backup-app-backup' или просто 'backup', если контейнер так назван
# Найдем его. В нашем docker-compose.yml сервис называется 'backup', а проект 'backup-app'
# Но мы задали build: . и container_name: backup-service, так что имя образа может быть разным.
# Проще всего использовать имя из docker-compose.yml
docker tag backup-service:latest "$FULL_IMAGE_TAG"
docker tag backup-service:latest "$LATEST_TAG"

echo "Шаг 4: Публикация образа в Docker Hub..."
docker push "$FULL_IMAGE_TAG"
docker push "$LATEST_TAG"

echo ""
echo "✅ Успешно опубликован образ:"
echo "   $FULL_IMAGE_TAG"
echo "   $LATEST_TAG"