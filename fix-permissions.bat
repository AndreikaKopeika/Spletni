@echo off
echo 🔧 Исправление прав доступа к базе данных...

echo 📦 Останавливаем контейнеры...
docker-compose down

echo 🔐 Исправляем права доступа...
if exist instance (
    icacls instance /grant Everyone:F /T
    icacls instance /grant Users:F /T
)

if exist database_backups (
    icacls database_backups /grant Everyone:F /T
    icacls database_backups /grant Users:F /T
)

if exist bug_reports (
    icacls bug_reports /grant Everyone:F /T
    icacls bug_reports /grant Users:F /T
)

echo 🔨 Пересобираем Docker образ...
docker-compose build --no-cache

echo 🚀 Запускаем приложение...
docker-compose up -d

echo ✅ Права доступа исправлены!
echo 🌐 Приложение доступно по адресу: http://localhost
echo.
echo Если проблема сохраняется, попробуйте:
echo 1. docker-compose logs spletni-app
echo 2. Проверить права: dir instance
echo 3. Перезапустить: docker-compose restart

pause
