#!/bin/bash

# Скрипт для настройки HTTPS для Spletni
# Использование: ./setup-https.sh your-domain.com your-email@example.com

set -e

# Проверяем аргументы
if [ $# -ne 2 ]; then
    echo "Использование: $0 <domain> <email>"
    echo "Пример: $0 example.com admin@example.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2

echo "🔒 Настройка HTTPS для домена: $DOMAIN"
echo "📧 Email для уведомлений: $EMAIL"
echo ""

# Проверяем Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker сначала."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose сначала."
    exit 1
fi

# Создаем необходимые директории
echo "📁 Создание директорий..."
mkdir -p ssl
mkdir -p static

# Обновляем nginx.conf с правильным доменом
echo "⚙️  Обновление конфигурации nginx..."
sed -i "s/your-domain.com/$DOMAIN/g" nginx.conf

# Обновляем docker-compose-https.yml с правильными данными
echo "⚙️  Обновление docker-compose-https.yml..."
sed -i "s/your-domain.com/$DOMAIN/g" docker-compose-https.yml
sed -i "s/your-email@example.com/$EMAIL/g" docker-compose-https.yml

# Останавливаем существующие контейнеры
echo "🛑 Остановка существующих контейнеров..."
docker-compose down 2>/dev/null || true

# Запускаем nginx для получения сертификата
echo "🚀 Запуск nginx для получения SSL сертификата..."
docker-compose -f docker-compose-https.yml up -d nginx

# Ждем запуска nginx
echo "⏳ Ожидание запуска nginx..."
sleep 10

# Получаем SSL сертификат
echo "🔐 Получение SSL сертификата от Let's Encrypt..."
docker-compose -f docker-compose-https.yml run --rm certbot

# Перезапускаем nginx с сертификатом
echo "🔄 Перезапуск nginx с SSL сертификатом..."
docker-compose -f docker-compose-https.yml restart nginx

# Запускаем все сервисы
echo "🚀 Запуск всех сервисов..."
docker-compose -f docker-compose-https.yml up -d

# Ждем запуска
echo "⏳ Ожидание запуска приложения..."
sleep 15

# Проверяем статус
if docker-compose -f docker-compose-https.yml ps | grep -q "Up"; then
    echo ""
    echo "✅ Spletni успешно запущена с HTTPS!"
    echo "🌐 Откройте https://$DOMAIN в браузере"
    echo "🔧 Панель разработчика: https://$DOMAIN/developer_login"
    echo ""
    echo "📋 Полезные команды:"
    echo "  docker-compose -f docker-compose-https.yml logs -f    # Просмотр логов"
    echo "  docker-compose -f docker-compose-https.yml down       # Остановить приложение"
    echo "  docker-compose -f docker-compose-https.yml restart    # Перезапустить"
    echo ""
    echo "🔄 Обновление сертификата (автоматически каждые 60 дней):"
    echo "  docker-compose -f docker-compose-https.yml run --rm certbot renew"
    echo ""
    echo "📝 Добавьте в crontab для автоматического обновления:"
    echo "  0 12 * * * cd $(pwd) && docker-compose -f docker-compose-https.yml run --rm certbot renew && docker-compose -f docker-compose-https.yml restart nginx"
else
    echo "❌ Ошибка запуска. Проверьте логи:"
    docker-compose -f docker-compose-https.yml logs
    exit 1
fi
