# 🌐 Настройка HTTPS через Cloudflare

## 📋 Пошаговая инструкция

### Шаг 1: Регистрация домена

#### Вариант A - Бесплатный домен (Freenom)
1. Зайдите на [Freenom.com](https://www.freenom.com)
2. Зарегистрируйте бесплатный домен:
   - `.tk` (Токелау)
   - `.ml` (Мали)
   - `.ga` (Габон)
   - `.cf` (ЦАР)
   - `.gq` (Экваториальная Гвинея)
3. Пример: `ваш-сайт.tk`

#### Вариант B - Платный домен
1. Купите домен на любом регистраторе
2. Пример: `ваш-сайт.com`

### Шаг 2: Настройка Cloudflare

#### 1. Регистрация в Cloudflare
1. Зайдите на [cloudflare.com](https://cloudflare.com)
2. Создайте бесплатный аккаунт
3. Подтвердите email

#### 2. Добавление домена
1. Нажмите "Add a Site"
2. Введите ваш домен (например: `ваш-сайт.tk`)
3. Выберите бесплатный план "Free"
4. Нажмите "Continue"

#### 3. Настройка DNS записей
В разделе "DNS" добавьте запись:
```
Type: A
Name: @ (или оставьте пустым)
Content: IP_ВАШЕГО_СЕРВЕРА (например: 213.199.34.108)
Proxy status: Proxied (оранжевое облачко)
```

#### 4. Изменение nameservers
1. Cloudflare покажет вам 2 nameserver'а (например):
   - `nina.ns.cloudflare.com`
   - `rick.ns.cloudflare.com`

2. Зайдите в панель управления доменом (Freenom):
   - Перейдите в "Manage Domain"
   - Выберите "Nameservers"
   - Измените на nameservers от Cloudflare
   - Сохраните изменения

3. Подождите 24-48 часа для распространения DNS

### Шаг 3: Настройка SSL в Cloudflare

#### 1. Включение SSL
1. В Cloudflare перейдите в "SSL/TLS"
2. Установите "Encryption mode" на "Full (strict)"
3. Включите "Always Use HTTPS"

#### 2. Настройка правил
1. Перейдите в "Rules" → "Page Rules"
2. Создайте правило:
   - URL: `http://ваш-домен.com/*`
   - Setting: "Always Use HTTPS"

### Шаг 4: Запуск на сервере

#### 1. Подключитесь к серверу
```bash
ssh root@ваш-ip-сервера
```

#### 2. Клонируйте проект (если еще не сделано)
```bash
git clone https://github.com/ваш-username/Spletni.git
cd Spletni
```

#### 3. Запустите скрипт настройки
```bash
./setup-cloudflare.sh ваш-домен.com
```

### Шаг 5: Проверка работы

#### 1. Проверьте DNS
```bash
# Проверьте, что домен указывает на ваш сервер
nslookup ваш-домен.com
```

#### 2. Проверьте SSL
```bash
# Проверьте SSL сертификат
curl -I https://ваш-домен.com
```

#### 3. Откройте сайт
- Откройте `https://ваш-домен.com` в браузере
- Должен быть зеленый замок в адресной строке

## 🔒 Преимущества Cloudflare

### ✅ Бесплатные функции:
- **SSL сертификат** - автоматически обновляется
- **DDoS защита** - защита от атак
- **CDN** - ускорение загрузки по всему миру
- **Кеширование** - статические файлы кешируются
- **Безопасность** - защита от ботов и спама

### ✅ Дополнительные возможности:
- **Аналитика** - статистика посещений
- **Правила** - настройка редиректов
- **Workers** - выполнение кода на edge
- **Pages** - хостинг статических сайтов

## 🛠️ Управление

### Полезные команды:
```bash
# Просмотр логов
docker-compose -f docker-compose-cloudflare.yml logs -f

# Перезапуск
docker-compose -f docker-compose-cloudflare.yml restart

# Остановка
docker-compose -f docker-compose-cloudflare.yml down

# Обновление
git pull
docker-compose -f docker-compose-cloudflare.yml restart
```

### Мониторинг в Cloudflare:
- **Analytics** - статистика трафика
- **Security** - угрозы и атаки
- **Performance** - скорость загрузки
- **DNS** - управление записями

## 🚨 Устранение проблем

### Проблема: Домен не работает
1. Проверьте DNS записи в Cloudflare
2. Убедитесь, что nameservers изменены
3. Подождите 24-48 часа

### Проблема: SSL не работает
1. Проверьте "Encryption mode" в Cloudflare
2. Убедитесь, что включен "Always Use HTTPS"
3. Проверьте Page Rules

### Проблема: Сайт не загружается
1. Проверьте логи: `docker-compose -f docker-compose-cloudflare.yml logs`
2. Убедитесь, что контейнеры запущены
3. Проверьте firewall на сервере

## 📞 Поддержка

- **Cloudflare Support**: [support.cloudflare.com](https://support.cloudflare.com)
- **Freenom Support**: [support.freenom.com](https://support.freenom.com)
- **Документация**: [developers.cloudflare.com](https://developers.cloudflare.com)

## 🎉 Готово!

После выполнения всех шагов у вас будет:
- ✅ Безопасный HTTPS сайт
- ✅ Защита от DDoS атак
- ✅ Быстрая загрузка по всему миру
- ✅ Бесплатный SSL сертификат
- ✅ Профессиональный домен
