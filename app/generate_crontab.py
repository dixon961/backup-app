# app/generate_crontab.py
import yaml
import sys

CONFIG_PATH = '/config/config.yml'
CRONTAB_PATH = '/etc/cron.d/backup-cron'

def generate():
    """Читает config.yml и печатает строки для crontab в stdout."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        # Если конфига нет, ничего не делаем. Cron просто не будет запущен.
        return

    globals_conf = config.get("globals", {})
    default_schedule = globals_conf.get("default_schedule", "0 2 * * *")

    cron_jobs = []
    for task in config.get("tasks", []):
        schedule = task.get("schedule", default_schedule)
        name = task["name"]
        # Формируем команду. >> /proc/1/fd/1 2>> /proc/1/fd/2 направляет вывод в лог контейнера
        command = f"/usr/local/bin/python /app/backup.py {name} >> /proc/1/fd/1 2>> /proc/1/fd/2"
        cron_jobs.append(f"{schedule} root {command}")
    
    # Печатаем все строки в stdout. entrypoint.sh перенаправит это в файл.
    if cron_jobs:
        print('\n'.join(cron_jobs) + '\n')

if __name__ == "__main__":
    generate()