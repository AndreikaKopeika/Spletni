#!/bin/bash

# Скрипт для быстрого запуска Spletni в Docker

echo "🚀 Запуск Spletni в Docker..."

# Проверяем, установлен ли Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker Desktop или Docker Engine."
    exit 1
fi

# Проверяем, установлен ли Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose."
    exit 1
fi

# Создаем .env файл если его нет
if [ ! -f .env ]; then
    if [ -f env.example ]; then
        echo "📝 Копируем env.example в .env с готовыми значениями..."
        cp env.example .env
        
        # Заменяем значения на готовые
        sed -i 's/your_secret_key_here_make_it_long_and_random/OhhhSoYouHackedSecretKey?WellGoAheadAndBreakMyApp!@#$%^&*()_+{}|:<>?[]\;'\''",.\/1234567890abcdef/g' .env
        sed -i 's/sk-your_openai_api_key_here/NEW_OPENAI_API_KEY_HERE_REPLACE_THIS/g' .env
        sed -i 's/your_developer_panel_password/admin123/g' .env
        
        echo "✅ .env файл создан из env.example с готовыми значениями."
    else
        echo "📝 Создаем .env файл с настройками по умолчанию..."
        cat > .env << EOF
# Настройки Spletni
SECRET_KEY=OhhhSoYouHackedSecretKey?WellGoAheadAndBreakMyApp!@#$%^&*()_+{}|:<>?[]\;',./1234567890abcdef
OPENAI_API_KEY=NEW_OPENAI_API_KEY_HERE_REPLACE_THIS
DEVELOPER_PASSWORD=admin123
DATABASE_URL=sqlite:///gossip.db
EOF
        echo "✅ .env файл создан. Отредактируйте его при необходимости."
    fi
fi

# Создаем необходимые директории
mkdir -p instance database_backups/automatic database_backups/manual bug_reports

# Останавливаем существующие контейнеры
echo "🛑 Останавливаем существующие контейнеры..."
docker-compose down

# Собираем и запускаем
echo "🔨 Собираем Docker образ..."
docker-compose build

echo "🚀 Запускаем приложение..."
docker-compose up -d

# Ждем запуска
echo "⏳ Ждем запуска приложения..."
sleep 10

# Проверяем статус
if docker-compose ps | grep -q "Up"; then
    echo "✅ Spletni успешно запущена!"
    echo "🌐 Откройте http://localhost:5000 в браузере"
    echo "🔧 Панель разработчика: http://localhost:5000/developer_login"
    echo ""
    echo "📋 Полезные команды:"
    echo "  docker-compose logs -f    # Просмотр логов"
    echo "  docker-compose down       # Остановить приложение"
    echo "  docker-compose restart    # Перезапустить"
else
    echo "❌ Ошибка запуска. Проверьте логи:"
    docker-compose logs
fi
