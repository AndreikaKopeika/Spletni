# 🐳 Установка Docker

## Windows

### 1. Docker Desktop (рекомендуется)
1. Скачайте [Docker Desktop для Windows](https://www.docker.com/products/docker-desktop/)
2. Запустите установщик и следуйте инструкциям
3. Перезагрузите компьютер
4. Запустите Docker Desktop

### 2. Проверка установки
```cmd
docker --version
docker-compose --version
```

### 3. Требования
- Windows 10/11 Pro, Enterprise или Education
- WSL 2 (Windows Subsystem for Linux 2)
- Виртуализация включена в BIOS

## macOS

### 1. Docker Desktop
1. Скачайте [Docker Desktop для Mac](https://www.docker.com/products/docker-desktop/)
2. Перетащите Docker.app в папку Applications
3. Запустите Docker Desktop

### 2. Проверка установки
```bash
docker --version
docker-compose --version
```

## Linux (Ubuntu/Debian)

### 1. Установка Docker Engine
```bash
# Обновляем пакеты
sudo apt-get update

# Устанавливаем зависимости
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавляем GPG ключ Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавляем репозиторий Docker
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Устанавливаем Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Запускаем Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. Установка Docker Compose
```bash
# Скачиваем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Делаем исполняемым
sudo chmod +x /usr/local/bin/docker-compose

# Проверяем установку
docker-compose --version
```

### 3. Перезагрузите систему или выйдите/войдите в систему

## Linux (CentOS/RHEL/Fedora)

### 1. Установка Docker Engine
```bash
# Устанавливаем зависимости
sudo yum install -y yum-utils

# Добавляем репозиторий Docker
sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo

# Устанавливаем Docker Engine
sudo yum install -y docker-ce docker-ce-cli containerd.io

# Запускаем Docker
sudo systemctl start docker
sudo systemctl enable docker

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER
```

### 2. Установка Docker Compose
```bash
# Скачиваем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Делаем исполняемым
sudo chmod +x /usr/local/bin/docker-compose
```

## Проверка установки

После установки проверьте, что Docker работает:

```bash
# Проверка версии Docker
docker --version

# Проверка версии Docker Compose
docker-compose --version

# Тестовый запуск контейнера
docker run hello-world
```

## Устранение неполадок

### Windows
- Убедитесь, что WSL 2 установлен и включен
- Проверьте, что виртуализация включена в BIOS
- Перезагрузите компьютер после установки

### Linux
- Перезагрузите систему после добавления пользователя в группу docker
- Или выполните: `newgrp docker`

### macOS
- Убедитесь, что Docker Desktop запущен
- Проверьте настройки безопасности в System Preferences

## Альтернативные способы установки

### Через пакетный менеджер (Linux)
```bash
# Ubuntu/Debian
sudo apt install docker.io docker-compose

# Fedora
sudo dnf install docker docker-compose

# Arch Linux
sudo pacman -S docker docker-compose
```

### Через snap (Ubuntu)
```bash
sudo snap install docker
```

## После установки

Теперь вы можете запустить Spletni:

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
docker-compose up -d
```

## 🎉 Готово!

Docker установлен и готов к использованию! 🚀
