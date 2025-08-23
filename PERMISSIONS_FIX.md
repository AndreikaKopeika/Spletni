# 🔧 Исправление проблемы с правами доступа к базе данных

## Проблема
Ошибка `sqlite3.OperationalError: attempt to write a readonly database` возникает, когда приложение не может записывать в базу данных из-за недостаточных прав доступа.

## Решение

### Автоматическое исправление

#### Для Linux/macOS:
```bash
chmod +x fix-permissions.sh
./fix-permissions.sh
```

#### Для Windows:
```cmd
fix-permissions.bat
```

### Ручное исправление

#### 1. Остановите контейнеры:
```bash
docker-compose down
```

#### 2. Исправьте права доступа:

**Linux/macOS:**
```bash
sudo chown -R 1000:1000 instance database_backups bug_reports
sudo chmod -R 755 instance database_backups bug_reports

# Если база данных уже существует:
sudo chown 1000:1000 instance/gossip.db
sudo chmod 644 instance/gossip.db
```

**Windows:**
```cmd
icacls instance /grant Everyone:F /T
icacls database_backups /grant Everyone:F /T
icacls bug_reports /grant Everyone:F /T
```

#### 3. Пересоберите образ:
```bash
docker-compose build --no-cache
```

#### 4. Запустите приложение:
```bash
docker-compose up -d
```

## Проверка решения

### Проверьте права доступа:
```bash
ls -la instance/
ls -la database_backups/
ls -la bug_reports/
```

### Проверьте логи:
```bash
docker-compose logs spletni-app
```

### Проверьте работу приложения:
Откройте http://localhost и попробуйте зарегистрировать нового пользователя.

## Дополнительные решения

### Если проблема сохраняется:

1. **Удалите существующую базу данных:**
   ```bash
   rm -f instance/gossip.db
   docker-compose up -d
   ```

2. **Используйте абсолютные пути в Docker:**
   ```yaml
   volumes:
     - ./instance:/app/instance:rw
   ```

3. **Проверьте SELinux (если используется):**
   ```bash
   sudo setsebool -P container_manage_cgroup 1
   ```

4. **Используйте другой пользователь в контейнере:**
   Измените `USER appuser` на `USER root` в Dockerfile (временно для отладки).

## Профилактика

1. Всегда используйте скрипты `fix-permissions.sh` или `fix-permissions.bat` после клонирования репозитория
2. Убедитесь, что директории `instance`, `database_backups`, `bug_reports` существуют и имеют правильные права
3. При развертывании на новом сервере всегда проверяйте права доступа

## Структура директорий

```
Spletni/
├── instance/           # База данных SQLite
├── database_backups/   # Резервные копии
├── bug_reports/        # Отчеты об ошибках
├── fix-permissions.sh  # Скрипт для Linux/macOS
├── fix-permissions.bat # Скрипт для Windows
└── ...
```

## Контакты

Если проблема не решается, создайте issue в репозитории с логами:
```bash
docker-compose logs spletni-app > logs.txt
```
