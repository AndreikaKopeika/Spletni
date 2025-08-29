#!/bin/bash

# Скрипт для настройки HTTPS через Cloudflare
# Использование: ./setup-cloudflare.sh your-domain.com

set -e

# Проверяем аргументы
if [ $# -ne 1 ]; then
    echo "Использование: $0 <domain>"
    echo "Пример: $0 example.com"
    exit 1
fi

DOMAIN=$1

echo "🌐 Настройка HTTPS через Cloudflare для домена: $DOMAIN"
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

# Создаем nginx.conf для Cloudflare
echo "⚙️  Создание конфигурации nginx для Cloudflare..."
cat > nginx-cloudflare.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    # Логи
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;
    
    # Основное приложение
    location / {
        proxy_pass http://spletni-app:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket поддержка
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Статические файлы
    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Безопасность
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Cloudflare реальные IP
    set_real_ip_from 173.245.48.0/20;
    set_real_ip_from 103.21.244.0/22;
    set_real_ip_from 103.22.200.0/22;
    set_real_ip_from 103.31.4.0/22;
    set_real_ip_from 141.101.64.0/18;
    set_real_ip_from 108.162.192.0/18;
    set_real_ip_from 190.93.240.0/20;
    set_real_ip_from 188.114.96.0/20;
    set_real_ip_from 197.234.240.0/22;
    set_real_ip_from 198.41.128.0/17;
    set_real_ip_from 162.158.0.0/15;
    set_real_ip_from 104.16.0.0/13;
    set_real_ip_from 104.24.0.0/14;
    set_real_ip_from 172.64.0.0/13;
    set_real_ip_from 131.0.72.0/22;
    real_ip_header CF-Connecting-IP;
}
EOF

# Создаем docker-compose-cloudflare.yml
echo "⚙️  Создание docker-compose-cloudflare.yml..."
cat > docker-compose-cloudflare.yml << EOF
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx-cloudflare.conf:/etc/nginx/conf.d/default.conf:ro
      - ./static:/app/static:ro
    depends_on:
      - spletni-app
    restart: unless-stopped
    networks:
      - spletni-network

  spletni-app:
    build: .
    environment:
      - FLASK_APP=app.py
      - FLASK_ENV=production
      - SECRET_KEY=\${SECRET_KEY:-OhhhSoYouHackedSecretKey?WellGoAheadAndBreakMyApp!@#$%^&*()_+{}|:<>?[]\;',./1234567890abcdef}
      - OPENAI_API_KEY=\${OPENAI_API_KEY:-NEW_OPENAI_API_KEY_HERE_REPLACE_THIS}
      - DEVELOPER_PASSWORD=\${DEVELOPER_PASSWORD:-admin123}
      - DATABASE_URL=sqlite:////app/instance/gossip.db
    volumes:
      - ./instance:/app/instance:rw
      - ./database_backups:/app/database_backups:rw
      - ./bug_reports:/app/bug_reports:rw
    restart: unless-stopped
    networks:
      - spletni-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  spletni-network:
    driver: bridge
EOF

# Останавливаем существующие контейнеры
echo "🛑 Остановка существующих контейнеров..."
docker-compose down 2>/dev/null || true

# Запускаем с новой конфигурацией
echo "🚀 Запуск приложения с Cloudflare конфигурацией..."
docker-compose -f docker-compose-cloudflare.yml up -d

# Ждем запуска
echo "⏳ Ожидание запуска приложения..."
sleep 15

# Проверяем статус
if docker-compose -f docker-compose-cloudflare.yml ps | grep -q "Up"; then
    echo ""
    echo "✅ Spletni успешно запущена с Cloudflare конфигурацией!"
    echo "🌐 Откройте https://$DOMAIN в браузере"
    echo "🔧 Панель разработчика: https://$DOMAIN/developer_login"
    echo ""
    echo "📋 Следующие шаги:"
    echo "1. Убедитесь, что DNS записи настроены в Cloudflare"
    echo "2. Проверьте, что домен указывает на ваш сервер"
    echo "3. Включите 'Always Use HTTPS' в Cloudflare"
    echo ""
    echo "📋 Полезные команды:"
    echo "  docker-compose -f docker-compose-cloudflare.yml logs -f    # Просмотр логов"
    echo "  docker-compose -f docker-compose-cloudflare.yml down       # Остановить приложение"
    echo "  docker-compose -f docker-compose-cloudflare.yml restart    # Перезапустить"
    echo ""
    echo "🔒 Преимущества Cloudflare:"
    echo "  - Бесплатный SSL сертификат"
    echo "  - Защита от DDoS атак"
    echo "  - Кеширование статических файлов"
    echo "  - CDN по всему миру"
else
    echo "❌ Ошибка запуска. Проверьте логи:"
    docker-compose -f docker-compose-cloudflare.yml logs
    exit 1
fi
