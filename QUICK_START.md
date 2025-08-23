# 🚀 Быстрый запуск Spletni

## Шаг 1: Установите Docker
Следуйте инструкции в [INSTALL_DOCKER.md](INSTALL_DOCKER.md)

## Шаг 2: Запустите приложение

### Windows
```cmd
start-docker.bat
```

### Linux/macOS
```bash
chmod +x start-docker.sh
./start-docker.sh
```

### Ручной запуск
```bash
# 1. Создайте .env файл
cp env.example .env

# 2. Отредактируйте .env (опционально)
# SECRET_KEY=ваш_ключ
# OPENAI_API_KEY=ваш_openai_ключ
# DEVELOPER_PASSWORD=пароль

# 3. Запустите
docker-compose up -d
```

**Примечание**: Скрипты автоматически создают `.env` с готовыми значениями из `env.example`.

## Шаг 3: Откройте приложение
- **Основное приложение**: http://localhost:5000
- **Панель разработчика**: http://localhost:5000/developer_login

## Полезные команды
```bash
# Остановить
docker-compose down

# Логи
docker-compose logs -f

# Перезапустить
docker-compose restart
```

## 🎉 Готово!
Ваше приложение Spletni работает! 🚀

---
📖 Подробная документация: [DOCKER_README.md](DOCKER_README.md)
