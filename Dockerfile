# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем необходимые директории с правильными правами
RUN mkdir -p database_backups/automatic database_backups/manual bug_reports instance

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Устанавливаем правильные права на директории
RUN chmod -R 755 /app/instance /app/database_backups /app/bug_reports

# Делаем скрипты исполняемыми
RUN chmod +x start_app.sh
RUN chmod +x update_database.py
RUN chmod +x test_database_update.py
RUN chmod +x build_and_test_docker.sh

# Переключаемся на пользователя приложения
USER appuser

# Открываем порт
EXPOSE 5000

# Переменные окружения
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Запускаем приложение с фоновыми задачами
CMD ["./start_app.sh"]
