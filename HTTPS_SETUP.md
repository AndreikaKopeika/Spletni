# 🔒 Настройка HTTPS для Spletni

Этот документ описывает, как настроить HTTPS для вашего приложения Spletni с использованием Let's Encrypt SSL сертификатов.

## 📋 Требования

1. **Домен** - у вас должен быть зарегистрированный домен
2. **VPS/Сервер** - с публичным IP адресом
3. **Docker и Docker Compose** - уже установлены
4. **Открытые порты** - 80 и 443 должны быть открыты в файрволе

## 🚀 Быстрая настройка

### Шаг 1: Подготовка

1. Убедитесь, что ваш домен указывает на IP адрес сервера:
   ```bash
   # Проверьте DNS записи
   nslookup your-domain.com
   ```

2. Откройте порты 80 и 443:
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 80
   sudo ufw allow 443
   
   # CentOS/RHEL
   sudo firewall-cmd --permanent --add-port=80/tcp
   sudo firewall-cmd --permanent --add-port=443/tcp
   sudo firewall-cmd --reload
   ```

### Шаг 2: Запуск с HTTPS

1. Сделайте скрипт исполняемым:
   ```bash
   chmod +x setup-https.sh
   ```

2. Запустите настройку HTTPS:
   ```bash
   ./setup-https.sh your-domain.com your-email@example.com
   ```

3. Дождитесь завершения процесса (может занять 5-10 минут)

## 🔧 Ручная настройка

Если автоматический скрипт не работает, выполните настройку вручную:

### Шаг 1: Обновление конфигурации

1. Отредактируйте `nginx.conf`:
   ```bash
   sed -i "s/your-domain.com/YOUR_ACTUAL_DOMAIN/g" nginx.conf
   ```

2. Отредактируйте `docker-compose-https.yml`:
   ```bash
   sed -i "s/your-domain.com/YOUR_ACTUAL_DOMAIN/g" docker-compose-https.yml
   sed -i "s/your-email@example.com/YOUR_ACTUAL_EMAIL/g" docker-compose-https.yml
   ```

### Шаг 2: Запуск сервисов

1. Создайте директории:
   ```bash
   mkdir -p ssl static
   ```

2. Запустите nginx:
   ```bash
   docker-compose -f docker-compose-https.yml up -d nginx
   ```

3. Получите SSL сертификат:
   ```bash
   docker-compose -f docker-compose-https.yml run --rm certbot
   ```

4. Запустите все сервисы:
   ```bash
   docker-compose -f docker-compose-https.yml up -d
   ```

## 📊 Управление

### Полезные команды

```bash
# Просмотр логов
docker-compose -f docker-compose-https.yml logs -f

# Остановка
docker-compose -f docker-compose-https.yml down

# Перезапуск
docker-compose -f docker-compose-https.yml restart

# Обновление сертификата
docker-compose -f docker-compose-https.yml run --rm certbot renew

# Проверка статуса сертификата
docker-compose -f docker-compose-https.yml run --rm certbot certificates
```

### Автоматическое обновление сертификатов

Добавьте в crontab для автоматического обновления:

```bash
# Откройте crontab
crontab -e

# Добавьте строку (замените /path/to/spletni на реальный путь)
0 12 * * * cd /path/to/spletni && docker-compose -f docker-compose-https.yml run --rm certbot renew && docker-compose -f docker-compose-https.yml restart nginx
```

## 🔍 Устранение неполадок

### Проблема: Сертификат не получен

1. Проверьте DNS записи:
   ```bash
   nslookup your-domain.com
   ```

2. Проверьте доступность порта 80:
   ```bash
   curl -I http://your-domain.com
   ```

3. Проверьте логи certbot:
   ```bash
   docker-compose -f docker-compose-https.yml logs certbot
   ```

### Проблема: Nginx не запускается

1. Проверьте конфигурацию nginx:
   ```bash
   docker-compose -f docker-compose-https.yml exec nginx nginx -t
   ```

2. Проверьте логи nginx:
   ```bash
   docker-compose -f docker-compose-https.yml logs nginx
   ```

### Проблема: Приложение недоступно

1. Проверьте статус контейнеров:
   ```bash
   docker-compose -f docker-compose-https.yml ps
   ```

2. Проверьте логи приложения:
   ```bash
   docker-compose -f docker-compose-https.yml logs spletni-app
   ```

## 🔒 Безопасность

### Рекомендации

1. **Регулярно обновляйте** Docker образы
2. **Мониторьте логи** на подозрительную активность
3. **Используйте сложные пароли** в `.env` файле
4. **Ограничьте доступ** к панели разработчика
5. **Настройте бэкапы** базы данных

### Дополнительные заголовки безопасности

Nginx уже настроен с базовыми заголовками безопасности:
- HSTS (HTTP Strict Transport Security)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy

## 📈 Мониторинг

### Проверка SSL сертификата

```bash
# Проверка срока действия
openssl s_client -connect your-domain.com:443 -servername your-domain.com < /dev/null 2>/dev/null | openssl x509 -noout -dates

# Проверка цепочки сертификатов
openssl s_client -connect your-domain.com:443 -servername your-domain.com < /dev/null 2>/dev/null | openssl x509 -noout -text
```

### Мониторинг доступности

```bash
# Проверка HTTP редиректа
curl -I http://your-domain.com

# Проверка HTTPS
curl -I https://your-domain.com
```

## 🎉 Готово!

После успешной настройки ваше приложение будет доступно по адресу:
- **Основное приложение**: https://your-domain.com
- **Панель разработчика**: https://your-domain.com/developer_login

Все HTTP запросы будут автоматически перенаправляться на HTTPS.
