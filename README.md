# Spletni

Веб-приложение для обмена сплетнями и слухами с поддержкой мобильных устройств и HTTPS.

## ✨ Особенности

- 📱 **Адаптивный дизайн** - отлично выглядит на всех устройствах
- 🔒 **HTTPS поддержка** - безопасное соединение с SSL сертификатами
- 🚀 **Быстрое развертывание** - готовые Docker конфигурации
- 🤖 **AI интеграция** - автоматическая генерация контента
- 🎮 **Система квестов** - геймификация для пользователей
- 💰 **Виртуальная валюта** - система коинов и магазин
- 🎨 **Кастомизация профилей** - украшения и рамки
- 📊 **Панель администратора** - полное управление системой

## 📱 Мобильная версия

Приложение полностью адаптировано для мобильных устройств:
- Адаптивная навигация
- Touch-friendly интерфейс
- Оптимизированные размеры кнопок
- Поддержка жестов
- Быстрая загрузка на медленных соединениях

## 🚀 Быстрый старт

### С Docker (рекомендуется)

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/your-username/spletni.git
   cd spletni
   ```

2. **Исправьте права доступа (если нужно):**
   ```bash
   # Windows
   fix-permissions.bat
   
   # Linux/macOS
   chmod +x fix-permissions.sh
   ./fix-permissions.sh
   ```

3. **Запустите приложение:**
   ```bash
   # Windows
   start-docker.bat
   
   # Linux/macOS
   chmod +x start-docker.sh
   ./start-docker.sh
   ```

4. **Откройте в браузере:**
   - http://localhost (основное приложение)
   - http://localhost/developer_login (панель разработчика)

### 🔧 Решение проблем

Если возникает ошибка `sqlite3.OperationalError: attempt to write a readonly database`:

1. **Автоматическое исправление:**
   ```bash
   # Windows
   fix-permissions.bat
   
   # Linux/macOS
   ./fix-permissions.sh
   ```

2. **Ручное исправление:**
   ```bash
   docker-compose down
   sudo chown -R 1000:1000 instance database_backups bug_reports
   docker-compose build --no-cache
   docker-compose up -d
   ```

Подробнее: [🔧 Исправление прав доступа](PERMISSIONS_FIX.md)

### С HTTPS

Для продакшена с SSL сертификатами:

```bash
# Настройка HTTPS
./setup-https.sh your-domain.com your-email@example.com
```

## 📚 Документация

- [📖 Подробная документация](DOCKER_README.md)
- [🔒 Настройка HTTPS](HTTPS_SETUP.md)
- [⚡ Быстрый старт](QUICK_START.md)
- [🐳 Установка Docker](INSTALL_DOCKER.md)
- [🔧 Исправление прав доступа](PERMISSIONS_FIX.md)

## 🛠 Технологии

- **Backend:** Flask, SQLAlchemy, Flask-SocketIO
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap
- **База данных:** SQLite (с возможностью PostgreSQL)
- **Контейнеризация:** Docker, Docker Compose
- **Web Server:** Nginx (для HTTPS)
- **SSL:** Let's Encrypt
- **AI:** OpenAI GPT-4

## 📱 Поддерживаемые устройства

- ✅ iPhone (iOS 12+)
- ✅ Android (8.0+)
- ✅ iPad
- ✅ Планшеты
- ✅ Десктопы
- ✅ Ноутбуки

## 🔒 Безопасность

- HTTPS с современными SSL настройками
- CSRF защита
- Rate limiting
- Валидация входных данных
- Безопасные заголовки HTTP
- Защита от XSS и SQL инъекций

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для подробностей.

## 🆘 Поддержка

Если у вас возникли проблемы:

1. Проверьте [документацию](DOCKER_README.md)
2. Посмотрите [FAQ](FAQ.md)
3. Создайте [Issue](https://github.com/your-username/spletni/issues)

## 🎉 Благодарности

Спасибо всем, кто внес вклад в развитие проекта!
