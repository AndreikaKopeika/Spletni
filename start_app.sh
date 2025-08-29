#!/bin/bash

# Скрипт для запуска приложения с фоновыми задачами в Docker

echo "Запуск Spletni..."

# Обновляем базу данных перед запуском
echo "Обновление базы данных..."
python update_database.py
if [ $? -ne 0 ]; then
    echo "Ошибка при обновлении базы данных!"
    exit 1
fi
echo "База данных успешно обновлена"

# Проверяем, нужно ли запускать фоновые задачи
if [ "$ENABLE_BACKGROUND_TASKS" = "true" ]; then
    echo "Запуск фоновых задач..."
    
    # Запускаем фоновые задачи в отдельном процессе
    python start_background_tasks.py &
    BACKGROUND_PID=$!
    
    echo "Фоновые задачи запущены с PID: $BACKGROUND_PID"
else
    echo "Фоновые задачи отключены"
    BACKGROUND_PID=""
fi

# Запускаем основное приложение
echo "Запуск основного приложения..."
exec gunicorn --bind 0.0.0.0:5000 --worker-class eventlet --workers 1 --timeout 120 wsgi:app

# Если основное приложение завершится, убиваем фоновые задачи
if [ ! -z "$BACKGROUND_PID" ]; then
    trap "echo 'Завершение работы...'; kill $BACKGROUND_PID; exit" SIGTERM SIGINT
else
    trap "echo 'Завершение работы...'; exit" SIGTERM SIGINT
fi
