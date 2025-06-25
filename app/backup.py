import os
import sys
import yaml
import logging
import subprocess
from datetime import datetime
import requests
import telebot
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Настройка ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_PATH = '/config/config.yml'
RCLONE_CONFIG_PATH = '/config/rclone/rclone.conf'

# --- Загрузка конфигурации ---
try:
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    logging.critical(f"Критическая ошибка: Файл конфигурации не найден по пути {CONFIG_PATH}")
    sys.exit(1)
except Exception as e:
    logging.critical(f"Критическая ошибка при чтении конфигурации: {e}")
    sys.exit(1)

# --- Инициализация Telegram ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN') or config.get('telegram', {}).get('token')
AUTHORIZED_USER_ID = int(config.get('telegram', {}).get('chat_id'))

if not TELEGRAM_TOKEN or not AUTHORIZED_USER_ID:
    logging.critical("Критическая ошибка: TELEGRAM_TOKEN или chat_id не найдены в конфигурации или переменных окружения.")
    sys.exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ====================================================================
# Секция существующей логики бекапа (немного адаптирована)
# ====================================================================

def send_telegram_message(message):
    """Отправляет сообщение в Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {'chat_id': AUTHORIZED_USER_ID, 'text': message, 'parse_mode': 'Markdown'}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление в Telegram: {e}")

def run_command(command):
    """Запускает команду и возвращает ее вывод, логируя ошибки."""
    logging.info(f"Выполнение команды: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error_message = f"Ошибка выполнения команды:\n{result.stderr or 'Нет вывода об ошибке.'}"
        logging.error(error_message)
        raise RuntimeError(error_message)
    logging.info(f"Вывод команды:\n{result.stdout or 'Нет вывода.'}")
    return result.stdout

def do_backup_task(task_name):
    """Основная логика бекапа для одной задачи. Адаптирована для бота."""
    task = next((t for t in config['tasks'] if t['name'] == task_name), None)
    if not task:
        error_msg = f"Задача с именем '{task_name}' не найдена в конфигурации."
        logging.error(error_msg)
        send_telegram_message(f"❌ *Ошибка запуска бекапа*\n\n{error_msg}")
        return

    globals_conf = config.get('globals', {})
    source_path = task['source']
    archive_prefix = task['archive_prefix']
    retention_days = task.get('retention_days', globals_conf.get('default_retention_days', 0))
    remote_name = globals_conf['rclone_remote_name']
    remote_path = os.path.join(globals_conf['remote_base_path'], task_name)

    if not os.path.isdir(source_path):
        error_msg = f"Исходная папка не найдена: {source_path}"
        send_telegram_message(f"❌ *Ошибка бекапа*\n\nЗадача: `{task_name}`\n\nПричина:\n`{error_msg}`")
        return

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    archive_name = f"{archive_prefix}_{timestamp}.zip"
    local_archive_path = f"/tmp/{archive_name}"

    try:
        logging.info(f"Создание архива для '{task_name}'...")
        run_command(['zip', '-r', local_archive_path, source_path])

        logging.info(f"Загрузка '{archive_name}'...")
        rclone_cmd = [
            'rclone', '-v', '--config', RCLONE_CONFIG_PATH, '--timeout', '1h',
            '--multi-thread-cutoff', '256M', '--multi-thread-chunk-size', '128M',
            '--multi-thread-streams', '4', 'copy', local_archive_path, f'{remote_name}:{remote_path}'
        ]
        run_command(rclone_cmd)

        if retention_days > 0:
            logging.info(f"Удаление бекапов старше {retention_days} дней...")
            rclone_cleanup_cmd = [
                'rclone', '--config', RCLONE_CONFIG_PATH, 'delete',
                f'{remote_name}:{remote_path}', '--min-age', f'{retention_days}d'
            ]
            run_command(rclone_cleanup_cmd)
        
        send_telegram_message(f"✅ *Успешный бекап*\n\nЗадача: `{task_name}`\nАрхив: `{archive_name}`")

    except Exception as e:
        error_msg = f"❌ *Ошибка бекапа*\n\nЗадача: `{task_name}`\n\nПричина:\n`{e}`"
        logging.error(error_msg)
        send_telegram_message(error_msg)
    finally:
        if os.path.exists(local_archive_path):
            os.remove(local_archive_path)
            logging.info(f"Временный архив удален: {local_archive_path}")

def run_backup_in_thread(task_name):
    """Обертка для запуска задачи бекапа в отдельном потоке."""
    logging.info(f"Запуск бекапа '{task_name}' в фоновом режиме.")
    thread = threading.Thread(target=do_backup_task, args=(task_name,))
    thread.start()

# ====================================================================
# Новая секция с логикой Telegram-бота
# ====================================================================

def is_authorized(message_or_call):
    """Проверяет, авторизован ли пользователь."""
    return message_or_call.from_user.id == AUTHORIZED_USER_ID

def get_main_menu_keyboard():
    """Возвращает клавиатуру с главной кнопкой."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🗄️ Ручной бекап", callback_data="manual_backup_start"))
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Обработчик команды /start."""
    if not is_authorized(message):
        bot.reply_to(message, "Permission denied.")
        return
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=get_main_menu_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """Главный обработчик всех нажатий на inline-кнопки."""
    if not is_authorized(call):
        bot.answer_callback_query(call.id, "Permission denied.")
        return

    # Разбираем callback_data
    action, *params = call.data.split(':')

    # --- Маршрутизация действий ---

    if action == 'manual_backup_start':
        # Показываем список задач для бекапа
        bot.answer_callback_query(call.id)
        tasks = config.get('tasks', [])
        if not tasks:
            bot.edit_message_text("В конфигурации не найдено ни одной задачи для бекапа.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return
        
        markup = InlineKeyboardMarkup()
        for task in tasks:
            markup.add(InlineKeyboardButton(task['name'], callback_data=f"select_task:{task['name']}"))
        markup.add(InlineKeyboardButton("« Назад", callback_data="back_to_main"))
        bot.edit_message_text("Выберите задачу для бекапа:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    elif action == 'select_task':
        # Показываем подтверждение для выбранной задачи
        task_name = params[0]
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Да, уверен", callback_data=f"confirm_backup:{task_name}"),
            InlineKeyboardButton("❌ Нет, отмена", callback_data="manual_backup_start")
        )
        bot.edit_message_text(f"Вы уверены, что хотите запустить бекап для задачи `{task_name}`?", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif action == 'confirm_backup':
        # Запускаем бекап в фоне
        task_name = params[0]
        bot.answer_callback_query(call.id, f"Начинаю бекап задачи '{task_name}'...")
        bot.edit_message_text(f"🚀 Бекап задачи `{task_name}` запущен в фоновом режиме. Вы получите уведомление по завершении.", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        run_backup_in_thread(task_name)
        # Возвращаем пользователя в главное меню
        bot.send_message(call.message.chat.id, "Вы можете выбрать другое действие:", reply_markup=get_main_menu_keyboard())

    elif action == 'back_to_main':
        # Возврат в главное меню
        bot.answer_callback_query(call.id)
        bot.edit_message_text("Выберите действие:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_menu_keyboard())


# ====================================================================
# Основной цикл запуска
# ====================================================================

if __name__ == "__main__":
    # Старый функционал запуска из командной строки
    if len(sys.argv) > 1:
        task_to_run = sys.argv[1]
        logging.info(f"Запуск одной задачи из командной строки: {task_to_run}")
        do_backup_task(task_to_run)
    else:
        # Новый функционал - запуск бота в режиме ожидания
        logging.info("Запуск Telegram-бота в режиме ожидания...")
        send_telegram_message("🤖 Бот для бекапов запущен и готов к работе.")
        bot.infinity_polling()