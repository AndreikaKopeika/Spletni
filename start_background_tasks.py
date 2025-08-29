#!/usr/bin/env python3
"""
Скрипт для запуска фоновых задач в Docker контейнере
"""
import os
import sys
import time
import threading
from datetime import datetime

# Добавляем путь к приложению
sys.path.insert(0, '/app')

def run_automatic_backup():
    """Запуск автоматического резервного копирования"""
    print(f"[{datetime.now()}] Запуск автоматического резервного копирования...")
    
    try:
        # Импортируем необходимые модули
        from app import app, run_automatic_backup as backup_func
        
        with app.app_context():
            backup_func()
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка в автоматическом резервном копировании: {e}")

def run_bot_activity():
    """Запуск активности ботов"""
    print(f"[{datetime.now()}] Запуск активности ботов...")
    
    try:
        # Импортируем необходимые модули
        from app import app, User, trigger_bot_actions
        
        with app.app_context():
            bots = User.query.filter_by(is_bot=True).all()
            if bots:
                num_to_trigger = min(3, len(bots))
                bots_to_trigger = bots[:num_to_trigger]  # Берем первых 3 ботов
                trigger_bot_actions(bots_to_trigger)
                print(f"[{datetime.now()}] Активировано {num_to_trigger} ботов")
            else:
                print(f"[{datetime.now()}] Нет ботов для активации")
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка в активности ботов: {e}")

def main():
    """Главная функция"""
    print(f"[{datetime.now()}] Запуск фоновых задач...")
    
    # Ждем немного, чтобы основное приложение запустилось
    time.sleep(10)
    
    # Запускаем автоматическое резервное копирование в отдельном потоке
    backup_thread = threading.Thread(target=run_automatic_backup, daemon=True)
    backup_thread.start()
    
    # Запускаем активность ботов каждые 30 минут
    while True:
        try:
            run_bot_activity()
            # Ждем 30 минут
            time.sleep(1800)  # 30 минут = 1800 секунд
        except Exception as e:
            print(f"[{datetime.now()}] Ошибка в главном цикле ботов: {e}")
            time.sleep(300)  # Ждем 5 минут перед повторной попыткой

if __name__ == "__main__":
    main()
