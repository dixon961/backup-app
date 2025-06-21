import os
import sys
import yaml
import logging
import subprocess
from datetime import datetime
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_PATH = '/config/config.yml'
RCLONE_CONFIG_PATH = '/config/rclone/rclone.conf'

def send_telegram_message(message):
    """Отправляет сообщение в Telegram."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        token = os.environ.get('TELEGRAM_TOKEN') or config.get('telegram', {}).get('token')
        chat_id = config.get('telegram', {}).get('chat_id')

        if not token or not chat_id:
            logging.warning("Telegram token или chat_id не настроены. Уведомление не отправлено.")
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление в Telegram: {e}")

def run_command(command):
    """Запускает команду и возвращает ее вывод."""
    logging.info(f"Выполнение команды: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error_message = f"Ошибка выполнения команды:\n{result.stderr}"
        logging.error(error_message)
        raise RuntimeError(error_message)
    logging.info(f"Вывод команды:\n{result.stdout}")
    return result.stdout

def main(task_name):
    """Основная логика бекапа для одной задачи."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"Файл конфигурации не найден: {CONFIG_PATH}")
        sys.exit(1)

    task = next((t for t in config['tasks'] if t['name'] == task_name), None)
    if not task:
        logging.error(f"Задача с именем '{task_name}' не найдена в конфигурации.")
        sys.exit(1)

    # Получаем настройки, используя значения по умолчанию, если не заданы
    globals_conf = config.get('globals', {})
    source_path = task['source']
    archive_prefix = task['archive_prefix']
    retention_days = task.get('retention_days', globals_conf.get('default_retention_days', 0))
    remote_name = globals_conf['rclone_remote_name']
    remote_path = os.path.join(globals_conf['remote_base_path'], task_name)

    # Проверяем, существует ли исходная папка
    if not os.path.isdir(source_path):
        raise FileNotFoundError(f"Исходная папка не найдена: {source_path}")

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    archive_name = f"{archive_prefix}_{timestamp}.zip"
    local_archive_path = f"/tmp/{archive_name}"

    try:
        # 1. Создание архива
        logging.info(f"Создание архива для '{task_name}' из '{source_path}'...")
        run_command(['zip', '-r', local_archive_path, source_path])
        logging.info(f"Архив успешно создан: {local_archive_path}")

        # 2. Загрузка в облако
        logging.info(f"Загрузка '{archive_name}' в '{remote_name}:{remote_path}'...")
        rclone_cmd = [
            'rclone',
            '-v',  # Подробный лог для отладки
            '--config', RCLONE_CONFIG_PATH,
            '--timeout', '1h',  # Общий таймаут на операцию
            '--multi-thread-cutoff', '256M', # Использовать многопоточную загрузку для файлов > 256MB
            '--multi-thread-chunk-size', '128M',    # Размер одного куска - 128MB
            '--multi-thread-streams', '4',          # Использовать 4 потока
            'copy',
            local_archive_path,
            f'{remote_name}:{remote_path}'
        ]
        run_command(rclone_cmd)
        logging.info("Загрузка завершена.")

        # 3. Удаление старых бекапов
        if retention_days > 0:
            logging.info(f"Удаление бекапов старше {retention_days} дней...")
            rclone_cleanup_cmd = [
                'rclone', '--config', RCLONE_CONFIG_PATH, 'delete',
                f'{remote_name}:{remote_path}', '--min-age', f'{retention_days}d'
            ]
            run_command(rclone_cleanup_cmd)
            logging.info("Очистка завершена.")
        
        send_telegram_message(f"✅ *Успешный бекап*\n\nЗадача: `{task_name}`\nАрхив: `{archive_name}`")

    except Exception as e:
        error_msg = f"❌ *Ошибка бекапа*\n\nЗадача: `{task_name}`\n\nПричина:\n`{e}`"
        logging.error(error_msg)
        send_telegram_message(error_msg)
    finally:
        # 4. Очистка локального временного файла
        if os.path.exists(local_archive_path):
            os.remove(local_archive_path)
            logging.info(f"Временный архив удален: {local_archive_path}")

if __name__ == "__main__":
    print("Старт обработки")
    if len(sys.argv) != 2:
        print("Использование: python backup.py <task_name>")
        sys.exit(1)
    main(sys.argv[1])