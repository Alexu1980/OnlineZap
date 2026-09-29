# 🚀 Развёртывание OnlineZap на сервере

## 📋 Предварительные требования

1. **Сервер** (Ubuntu 20.04+ или Debian 10+)
   - 2GB+ RAM
   - 10GB+ свободного места
   - Docker 20.10+
   - Docker Compose v2.0+

2. **Домен** (опционально, для HTTPS)
   - Укажите A-запись на IP сервера

3. **Файлы**
   - `credentials.json` — для Google Sheets

---

## ⚡ Быстрое развёртывание (рекомендуется)

### 1. Загрузка файлов на сервер

```bash
# Скопируйте проект на сервер
scp -r /path/to/OnlineZap user@your-server:/opt/onlinezap/

# Или через git
git clone <your-repo-url> /opt/onlinezap
cd /opt/onlinezap
```

### 2. Настройка переменных окружения

```bash
cd /opt/onlinezap

# Скопируйте пример
cp .env.example .env

# Отредактируйте
nano .env
```

**Обязательные изменения:**
```env
BOT_TOKEN=6989509563:AAHzyndAoIgGVV2rhUOtZAHuQ9s285QFhS0
ADMIN_IDS_CSV=1853449775
ADMIN_CHAT_ID_CSV=-1001234567890
GOOGLE_SHEET_ID=11WfXPmyuQ1wlhyPNwm_A9ds1UfEgyjQYDcA1gnAMUJ0
MINIAPP_URL=https://your-domain.com/app
```

### 3. Копирование credentials.json

```bash
# Скопируйте файл Google Sheets credentials
sudo cp /path/to/credentials.json /opt/onlinezap/credentials.json
sudo chmod 644 /opt/onlinezap/credentials.json
```

### 4. Запуск скрипта развёртывания

```bash
sudo chmod +x deploy.sh
sudo ./deploy.sh deploy
```

Скрипт автоматически:
- ✅ Установит Docker и Docker Compose
- ✅ Настроит firewall
- ✅ Предложит настроить SSL
- ✅ Собирает и запустит контейнеры

### 5. Проверка

```bash
# Проверка статуса
docker-compose ps

# Проверка API
curl http://localhost:8000/api/health

# Открытие MiniApp
# http://your-domain.com/app
```

---

## 🔧 Ручное развёртывание

### 1. Установка Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### 2. Установка Docker Compose

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. Настройка проекта

```bash
cd /opt/onlinezap
cp .env.example .env
nano .env  # Отредактируйте переменные
sudo cp credentials.json .
```

### 4. Сборка и запуск

```bash
docker-compose up -d --build
```

### 5. Настройка SSL (Let's Encrypt)

```bash
# Установка Certbot
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# Получение сертификата
sudo certbot certonly --standalone -d your-domain.com -m your-email@example.com --agree-tos --non-interactive

# Копирование сертификатов
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
sudo chmod 600 nginx/ssl/key.pem

# Обновление MINIAPP_URL в .env
export MINIAPP_URL=https://your-domain.com/app

# Перезапуск
docker-compose down
docker-compose up -d
```

---

## 📊 Управление

### Основные команды

```bash
cd /opt/onlinezap

# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f app

# Пересборка
docker-compose build --no-cache

# Обновление (git pull)
git pull
docker-compose down
docker-compose up -d --build
```

### Резервное копирование

```bash
# Ручной бэкап
sudo chmod +x backup.sh
sudo ./backup.sh

# Автоматический бэкап (каждый день в 2:00)
sudo cp backup.crontab /etc/cron.d/onlinezap-backup
sudo chmod 644 /etc/cron.d/onlinezap-backup
```

### Мониторинг

```bash
# Использование ресурсов
docker stats

# Проверка здоровья
docker inspect --format='{{.State.Health.Status}}' onlinezap-app

# Просмотр логов
docker-compose logs --tail 100 app
```

---

## 🔍 Отладка

### Приложение не запускается

```bash
# Проверка логов
docker-compose logs app

# Проверка переменных окружения
docker exec -it onlinezap-app env | grep BOT_TOKEN

# Пересборка
docker-compose build --no-cache
docker-compose up -d
```

### База данных не создаётся

```bash
# Проверка прав
docker exec -it onlinezap-app ls -la /app/Data/

# Пересоздание томов
docker-compose down -v
docker-compose up -d
```

### Google Sheets не подключается

```bash
# Проверка файла
docker exec -it onlinezap-app ls -la /app/credentials.json

# Проверка содержимого
docker exec -it onlinezap-app cat /app/credentials.json
```

---

## 🚨 Устранение неполадок

### Порт 8000 уже используется

```bash
# Проверка, что использует порт
sudo lsof -i :8000

# Изменение порта в docker-compose.yml
# ports:
#   - "8001:8000"
```

### Не хватает памяти

```bash
# Проверка ресурсов
free -h
docker stats

# Остановка ненужных сервисов
sudo systemctl stop apache2  # или другой сервис
```

### Ошибка SSL

```bash
# Проверка сертификатов
ls -la nginx/ssl/

# Перезапуск Nginx
docker-compose restart nginx
```

---

## 📈 Production Checklist

- [x] Docker и Docker Compose установлены
- [x] `.env` настроен с правильными значениями
- [x] `credentials.json` скопирован
- [x] SSL сертификат настроен
- [x] Firewall настроен (порты 80, 443)
- [x] Backup настроен
- [x] Monitoring настроен (опционально)
- [x] MiniApp URL обновлён
- [x] Telegram BotFather настроен для WebApp
- [x] Google Sheets API включён
- [x] Service Account добавлен в таблицу

---

## 📞 Поддержка

При проблемах:
1. Проверьте логи: `docker-compose logs -f app`
2. Проверьте health: `curl http://localhost:8000/api/health`
3. Проверьте переменные: `docker exec -it onlinezap-app env`
4. Обратитесь к документации:
   - [DOCKER_README.md](DOCKER_README.md)
   - [MINIAPP_README.md](MINIAPP_README.md)
