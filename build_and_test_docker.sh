#!/bin/bash

# Скрипт для сборки и тестирования Docker образа с автоматическим обновлением базы данных

echo "🐳 Сборка Docker образа для Spletni..."

# Собираем образ
docker build -t spletni-app .

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при сборке Docker образа!"
    exit 1
fi

echo "✅ Docker образ успешно собран!"

# Создаем тестовый контейнер
echo "🧪 Тестирование обновления базы данных в контейнере..."

# Создаем временную директорию для тестирования
mkdir -p test_instance

# Запускаем контейнер для тестирования
docker run --rm \
    -v "$(pwd)/test_instance:/app/instance" \
    -e FLASK_APP=app.py \
    -e FLASK_ENV=production \
    spletni-app \
    python update_database.py

if [ $? -eq 0 ]; then
    echo "✅ Тестирование обновления базы данных прошло успешно!"
else
    echo "❌ Ошибка при тестировании обновления базы данных!"
fi

# Очищаем тестовую директорию
rm -rf test_instance

echo "🎉 Готово! Docker образ готов к использованию."
echo ""
echo "Для запуска приложения используйте:"
echo "docker-compose up -d"
echo ""
echo "Или для запуска без docker-compose:"
echo "docker run -d -p 80:5000 -v ./instance:/app/instance spletni-app"
