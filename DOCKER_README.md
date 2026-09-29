# 🐳 Docker Deployment Guide

## 📋 Требования

- Docker 20.10+
- Docker Compose v2.0+
- 2GB+ RAM
- 10GB+ свободного дискового пространства

## 🚀 Быстрый старт

### 1. Подготовка

```bash
# Скопируйте пример .env
cp .env.example .env

# Отредактируйте .env
# Замените значения на ваши:
# - BOT_TOKEN
# - GOOGLE_SHEET_ID
# - ADMIN_IDS_CSV
# - ADMIN_CHAT_ID_CSV
# - MINIAPP_URL (для продакшена используйте HTTPS)
```

### 2. Развёртывание

#### Вариант A: Использование deploy.sh (рекомендуется)

```bash
# Сделайте скрипт исполняемым
chmod +x deploy.sh

# Запустите развёртывание
sudo ./deploy.sh deploy
```

Скрипт автоматически:
- Установит Docker и Docker Compose (если не установлены)
- Настроит firewall
- Предложит настроить SSL сертификат
- Собирает и запустит контейнеры

#### Вариант B: Ручное развёртывание

```bash
# Собираем и запускаем
docker-compose up -d --build

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f app
```

### 3. Проверка

```bash
# Проверка health
curl http://localhost:8000/api/health

# Открытие MiniApp
# http://localhost:8000/app
```

## 🔧 Настройка

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | required |
| `ADMIN_IDS_CSV` | ID админов | `1853449775` |
| `ADMIN_CHAT_ID_CSV` | ID чата админов | `-1001234567890` |
| `DATABASE_URL` | URL базы данных | `sqlite+aiosqlite:////app/Data/bookings.db` |
| `GOOGLE_SHEET_ID` | ID Google таблицы | required |
| `GOOGLE_SHEET_NAME` | Название листа | `Bookings` |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Путь к credentials | `credentials.json` |
| `SLOT_DURATION_MINUTES` | Длительность слота | `60` |
| `RESERVATION_TIMEOUT_SECONDS` | Таймаут резерва | `300` |
| `REMINDER_24H_ENABLED` | Напоминание 24ч | `true` |
| `REMINDER_2H_ENABLED` | Напоминание 2ч | `true` |
| `MINIAPP_URL` | URL MiniApp | `http://localhost:8000/app` |

### SSL сертификат

```bash
# Установите домен и email
export DOMAIN=your-domain.com
export EMAIL=your-email@example.com

# Получите SSL сертификат
sudo certbot certonly --standalone -d $DOMAIN -m $EMAIL --agree-tos --non-interactive

# Скопируйте сертификаты
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/key.pem
sudo chmod 600 nginx/ssl/key.pem

# Обновите MINIAPP_URL в .env
export MINIAPP_URL=https://$DOMAIN/app

# Перезапустите
docker-compose down
docker-compose up -d
```

### PostgreSQL (опционально)

Раскомментируйте сервис `db` в `docker-compose.yml`:

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    # ...
```

Обновите `.env`:

```env
DATABASE_URL=postgresql+asyncpg://onlinezap:change_me_in_production@db:5432/onlinezap
POSTGRES_USER=onlinezap
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_DB=onlinezap
```

## 📁 Структура томов

| Том | Путь | Описание |
|-----|------|----------|
| `db-data` | `/app/Data` | База данных SQLite |
| `logs` | `/app` | Логи приложения |
| `./credentials.json` | `/app/credentials.json` | Google Sheets credentials |

## 🛠 Управление

### Команды

```bash
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

# Обновление
git pull
docker-compose down
docker-compose up -d --build

# Очистка
docker-compose down -v
docker system prune -f
```

### Health Check

```bash
# Проверка статуса контейнера
docker inspect --format='{{.State.Health.Status}}' onlinezap-app

# Проверка API
curl http://localhost:8000/api/health
```

## 🔍 Отладка

### Просмотр логов

```bash
# Все логи
docker-compose logs

# Логи приложения
docker-compose logs -f app

# Логи Nginx
docker-compose logs -f nginx

# Логи за последний час
docker-compose logs --since 1h app
```

### Вход в контейнер

```bash
# Bash в контейнере app
docker exec -it onlinezap-app sh

# Bash в контейнере nginx
docker exec -it onlinezap-nginx sh
```

### Проверка базы данных

```bash
# Подключение к SQLite
docker exec -it onlinezap-app sh -c "cd /app/Data && sqlite3 bookings.db"

# Просмотр таблиц
sqlite> .tables

# Просмотр записей
sqlite> SELECT * FROM bookings LIMIT 10;
```

### Проверка API

```bash
# Получить специалистов
curl http://localhost:8000/api/specialists

# Получить слоты
curl "http://localhost:8000/api/slots?specialist_id=1&date=2026-10-05"
```

## 🚨 Устранение неполадок

### Контейнер не запускается

```bash
# Проверка логов
docker-compose logs app

# Проверка переменных окружения
docker exec -it onlinezap-app sh -c "env | grep BOT_TOKEN"

# Пересборка
docker-compose build --no-cache
```

### База данных не создаётся

```bash
# Проверка прав на папку Data
ls -la Data/

# Пересоздание томов
docker-compose down -v
docker-compose up -d
```

### Google Sheets не подключается

```bash
# Проверка credentials.json
docker exec -it onlinezap-app sh -c "ls -la /app/credentials.json"

# Проверка доступа
docker exec -it onlinezap-app sh -c "cat /app/credentials.json"
```

### Nginx не запускается

```bash
# Проверка конфигурации
docker exec -it onlinezap-nginx nginx -t

# Перезапуск
docker-compose restart nginx
```

## 📊 Мониторинг

### Ресурсы

```bash
# Использование ресурсов
docker stats

# Дисковое пространство
docker system df
```

### Автоматический перезапуск

Docker Compose уже настроен с `restart: unless-stopped`.

Для дополнительного мониторинга используйте:

```yaml
# docker-compose.yml
services:
  app:
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## 🔐 Безопасность

### Рекомендации

1. **Никогда не коммитьте `.env` и `credentials.json`**
2. **Используйте HTTPS** для production
3. **Смените пароли PostgreSQL** по умолчанию
4. **Регулярно обновляйте Docker образы**
5. **Настройте firewall** (скрипт deploy.sh делает это автоматически)
6. **Используйте сильные пароли** для базы данных

### Обновление безопасности

```bash
# Обновление Docker образов
docker-compose pull
docker-compose up -d

# Обновление Python зависимостей
docker exec -it onlinezap-app sh -c "pip install --upgrade -r requirements.txt"
```

## 📈 Production Checklist

- [ ] `.env` настроен с правильными значениями
- [ ] `credentials.json` скопирован на сервер
- [ ] SSL сертификат настроен
- [ ] Firewall настроен
- [ ] Backup настроен для томов `db-data` и `logs`
- [ ] Monitoring настроен (опционально)
- [ ] MiniApp URL обновлён в `.env`
- [ ] Telegram BotFather настроен для WebApp
- [ ] Google Sheets API включён
- [ ] Service Account добавлен в Google таблицу

## 📞 Поддержка

При проблемах:
1. Проверьте логи: `docker-compose logs -f app`
2. Проверьте health: `curl http://localhost:8000/api/health`
3. Проверьте переменные окружения: `docker exec -it onlinezap-app env`
4. Обратитесь к документации: [Telegram Web Apps](https://core.telegram.org/bots/webapps)
