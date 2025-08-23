#!/bin/bash

echo "🔧 Исправление прав доступа к базе данных..."

# Останавливаем контейнеры
echo "📦 Останавливаем контейнеры..."
docker-compose down

# Исправляем права доступа на хосте
echo "🔐 Исправляем права доступа..."
sudo chown -R 1000:1000 instance database_backups bug_reports
sudo chmod -R 755 instance database_backups bug_reports

# Если база данных уже существует, исправляем права на неё
if [ -f "instance/gossip.db" ]; then
    echo "🗄️ Исправляем права на существующую базу данных..."
    sudo chown 1000:1000 instance/gossip.db
    sudo chmod 644 instance/gossip.db
fi

# Пересобираем образ с новыми правами
echo "🔨 Пересобираем Docker образ..."
docker-compose build --no-cache

# Запускаем контейнеры
echo "🚀 Запускаем приложение..."
docker-compose up -d

echo "✅ Права доступа исправлены!"
echo "🌐 Приложение доступно по адресу: http://localhost"
echo ""
echo "Если проблема сохраняется, попробуйте:"
echo "1. docker-compose logs spletni-app"
echo "2. Проверить права: ls -la instance/"
echo "3. Перезапустить: docker-compose restart"
