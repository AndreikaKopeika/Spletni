@echo off
chcp 65001 >nul
echo 🚀 Запуск Spletni в Docker...

REM Проверяем Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker не установлен. Установите Docker Desktop.
    pause
    exit /b 1
)

REM Проверяем Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose не установлен. Установите Docker Compose.
    pause
    exit /b 1
)

REM Создаем .env файл если его нет
if not exist .env (
    if exist env.example (
        echo 📝 Настраиваем .env файл из env.example...
        powershell -ExecutionPolicy Bypass -File setup-env.ps1
    ) else (
        echo 📝 Создаем .env файл с настройками по умолчанию...
        (
            echo # Настройки Spletni
            echo SECRET_KEY=OhhhSoYouHackedSecretKey?WellGoAheadAndBreakMyApp!@#$%%^&*()_+{}^|:^<^>?[]\;',./1234567890abcdef
            echo OPENAI_API_KEY=NEW_OPENAI_API_KEY_HERE_REPLACE_THIS
            echo DEVELOPER_PASSWORD=admin123
            echo DATABASE_URL=sqlite:///gossip.db
        ) > .env
        echo ✅ .env файл создан. Отредактируйте его при необходимости.
    )
)

REM Создаем необходимые директории
if not exist instance mkdir instance
if not exist database_backups\automatic mkdir database_backups\automatic
if not exist database_backups\manual mkdir database_backups\manual
if not exist bug_reports mkdir bug_reports

REM Останавливаем существующие контейнеры
echo 🛑 Останавливаем существующие контейнеры...
docker-compose down

REM Собираем и запускаем
echo 🔨 Собираем Docker образ...
docker-compose build

echo 🚀 Запускаем приложение...
docker-compose up -d

REM Ждем запуска
echo ⏳ Ждем запуска приложения...
timeout /t 10 /nobreak >nul

REM Проверяем статус
docker-compose ps | findstr "Up" >nul
if errorlevel 1 (
    echo ❌ Ошибка запуска. Проверьте логи:
    docker-compose logs
) else (
    echo ✅ Spletni успешно запущена!
    echo 🌐 Откройте http://localhost:5000 в браузере
    echo 🔧 Панель разработчика: http://localhost:5000/developer_login
    echo.
    echo 📋 Полезные команды:
    echo   docker-compose logs -f    # Просмотр логов
    echo   docker-compose down       # Остановить приложение
    echo   docker-compose restart    # Перезапустить
)

pause
