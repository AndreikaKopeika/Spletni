# 🐳 Развертывание Spletni в Docker

## Быстрый старт

### Windows
```bash
# Запустите файл start-docker.bat
start-docker.bat
```

### Linux/Mac
```bash
# Сделайте скрипт исполняемым и запустите
chmod +x start-docker.sh
./start-docker.sh
```

### Ручной запуск
```bash
# 1. Создайте .env файл (если его нет)
cp env.example .env

# 2. Отредактируйте .env файл (опционально)
# SECRET_KEY=ваш_секретный_ключ
# OPENAI_API_KEY=ваш_openai_ключ
# DEVELOPER_PASSWORD=пароль_для_панели_разработчика

# 3. Запустите Docker Compose
docker-compose up -d
```

**Примечание**: Скрипты `start-docker.sh` и `start-docker.bat` автоматически создают `.env` файл из `env.example` с готовыми значениями.

## 📁 Структура файлов

```
Spletni/
├── Dockerfile              # Конфигурация Docker образа
├── docker-compose.yml      # Конфигурация сервисов
├── .dockerignore          # Исключения для Docker
├── start-docker.sh        # Скрипт запуска (Linux/Mac)
├── start-docker.bat       # Скрипт запуска (Windows)
├── requirements.txt       # Python зависимости
├── app.py                # Основное приложение
├── wsgi.py               # WSGI точка входа
└── gunicorn.conf.py      # Конфигурация Gunicorn
```

## 🔧 Настройка

### Переменные окружения (.env файл)

```env
# Обязательные
SECRET_KEY=ваш_длинный_случайный_ключ
OPENAI_API_KEY=sk-ваш_openai_ключ
DEVELOPER_PASSWORD=пароль_для_панели_разработчика

# Опциональные
DATABASE_URL=sqlite:///gossip.db
FLASK_ENV=production
```

### Порт
По умолчанию приложение доступно на порту `5000`.
Измените в `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Внешний порт 8080
```

## 🚀 Команды управления

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f

# Пересборка образа
docker-compose build --no-cache

# Остановка и удаление контейнеров
docker-compose down -v
```

## 📊 Мониторинг

### Проверка статуса
```bash
docker-compose ps
```

### Логи приложения
```bash
docker-compose logs -f spletni-app
```

### Использование ресурсов
```bash
docker stats
```

## 🔒 Безопасность

### Рекомендации для продакшена:

1. **Измените SECRET_KEY** на случайный длинный ключ
2. **Установите DEVELOPER_PASSWORD** на сложный пароль
3. **Настройте HTTPS** через reverse proxy (nginx)
4. **Ограничьте доступ** к панели разработчика
5. **Регулярно обновляйте** Docker образы

### Пример .env для продакшена:
```env
SECRET_KEY=$(openssl rand -hex 32)
OPENAI_API_KEY=sk-ваш_реальный_ключ
DEVELOPER_PASSWORD=сложный_пароль_123!
FLASK_ENV=production
```

## 🗄️ База данных

### SQLite (по умолчанию)
- Файл базы данных сохраняется в `./instance/`
- Автоматические бэкапы в `./database_backups/`

### PostgreSQL (опционально)
Измените в `docker-compose.yml`:
```yaml
environment:
  - DATABASE_URL=postgresql://user:pass@postgres:5432/spletni

# Добавьте сервис PostgreSQL
postgres:
  image: postgres:15
  environment:
    POSTGRES_DB: spletni
    POSTGRES_USER: user
    POSTGRES_PASSWORD: pass
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

## 🔧 Устранение неполадок

### Приложение не запускается
```bash
# Проверьте логи
docker-compose logs spletni-app

# Проверьте переменные окружения
docker-compose exec spletni-app env | grep -E "(SECRET_KEY|OPENAI_API_KEY)"
```

### Проблемы с правами доступа
```bash
# Исправьте права на директории
sudo chown -R $USER:$USER instance database_backups bug_reports
```

### Очистка Docker
```bash
# Удалите неиспользуемые образы
docker system prune -a

# Удалите все контейнеры и образы
docker system prune -a --volumes
```

## 📈 Масштабирование

### Увеличение количества воркеров
Измените в `Dockerfile`:
```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "8", "--timeout", "120", "wsgi:app"]
```

### Добавление Redis для кеширования
Раскомментируйте в `docker-compose.yml`:
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

## 🌐 Доступ к приложению

После запуска приложение будет доступно по адресам:
- **Основное приложение**: http://localhost:5000
- **Панель разработчика**: http://localhost:5000/developer_login
- **API документация**: http://localhost:5000/api/docs (если есть)

## 📝 Полезные команды

```bash
# Войти в контейнер
docker-compose exec spletni-app bash

# Создать бэкап базы данных
docker-compose exec spletni-app python -c "from app import create_database_backup; create_database_backup('manual')"

# Проверить статус ботов
docker-compose exec spletni-app python -c "from app import User; print([u.username for u in User.query.filter_by(is_bot=True).all()])"
```

## 🎉 Готово!

Ваше приложение Spletni теперь работает в Docker! 🚀
