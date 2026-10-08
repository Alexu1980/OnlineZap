# OnlineZap - Запись на консультацию психолога

Telegram бот + MiniApp для записи на психологическую консультацию.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      Amvera Platform                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              PostgreSQL Managed DB                   │  │
│  └────────────────────────┬─────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼─────────────────────────────┐  │
│  │          onlinezap-backend (Python)                  │  │
│  │  - Telegram Bot (aiogram)                            │  │
│  │  - FastAPI API                                       │  │
│  │  - MiniApp Static Files                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         onlinezap-frontend (React/Vite)              │  │
│  │  - Built React app                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Стек технологий

- **Backend**: Python 3.12, FastAPI, aiogram 3.x, SQLAlchemy 2.x
- **Frontend**: React 18, Vite 5, TypeScript, TailwindCSS
- **Database**: PostgreSQL (Amvera Managed)
- **Deployment**: Amvera PaaS

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/Alexu1980/OnlineZap.git
cd OnlineZap
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
# Отредактируйте .env и добавьте свои значения
```

### 3. Локальная разработка (SQLite)

```bash
# Backend
pip install -r requirements.txt
python main.py

# Frontend (отдельный терминал)
cd app
npm install
npm run dev
```

### 4. Деплой на Amvera

#### Шаг 1: Создание проекта на Amvera

1. Зайдите в панель Amvera: https://app.amvera.ru
2. Создайте новый проект
3. Подключите Git репозиторий

#### Шаг 2: Настройка PostgreSQL

1. В панели проекта добавьте сервис **PostgreSQL**
2. Запишите connection string (автоматически добавится в env vars)

#### Шаг 3: Настройка переменных окружения

В панели Amvera добавьте:
- `BOT_TOKEN` - токен от @BotFather
- `ADMIN_IDS_CSV` - ID админов
- `ADMIN_CHAT_ID_CSV` - ID чата админов
- `GOOGLE_SHEET_ID` - ID Google Sheets
- `GOOGLE_SHEETS_CREDENTIALS_PATH` - путь к credentials.json

#### Шаг 4: Загрузка credentials.json

1. Скачайте `credentials.json` из Google Cloud Console
2. В панели Amvera загрузите как **Secret** с именем `google_sheets_credentials`

#### Шаг 5: Деплой

```bash
# Push в Git
git add .
git commit -m "Deploy to Amvera"
git push
```

Amvera автоматически:
- Соберёт Docker images
- Запустит PostgreSQL
- Запустит backend и frontend
- Настроит SSL сертификаты

## Структура проекта

```
OnlineZap/
├── amvera.yml              # Конфигурация Amvera
├── Dockerfile.backend      # Dockerfile для backend
├── Dockerfile.frontend     # Dockerfile для frontend
├── nginx.conf              # Nginx конфигурация для frontend
├── requirements.txt        # Python зависимости
├── .env.example            # Пример переменных окружения
│
├── app/                    # Frontend (React/Vite)
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── api/
│       ├── components/
│       ├── store/
│       └── App.tsx
│
├── config/                 # Конфигурация
│   └── settings.py
│
├── database/               # Database layer
│   ├── engine.py
│   ├── models.py
│   └── repositories.py
│
├── handlers/               # Telegram bot handlers
│   ├── user/
│   └── admin/
│
├── services/               # Business logic
│   ├── booking_service.py
│   ├── scheduler_service.py
│   └── sheet_service.py
│
├── webapp/                 # FastAPI API
│   ├── main.py
│   ├── routes/
│   ├── schemas.py
│   └── auth.py
│
└── main.py                 # Точка входа (бот + API)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/specialists` | Список специалистов |
| GET | `/api/specialists/{id}` | Данные специалиста |
| GET | `/api/availability` | Доступные даты |
| GET | `/api/slots` | Доступные слоты |
| POST | `/api/bookings` | Создание бронирования |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram Bot token | Yes |
| `ADMIN_IDS_CSV` | Admin IDs (comma-separated) | Yes |
| `ADMIN_CHAT_ID_CSV` | Admin chat ID | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `GOOGLE_SHEET_ID` | Google Sheets ID | Yes |
| `GOOGLE_SHEET_NAME` | Google Sheets name | No |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Path to credentials.json | Yes |

## Development

### Local PostgreSQL

```bash
# Docker PostgreSQL
docker run -d \
  --name onlinezap-db \
  -e POSTGRES_USER=onlinezap \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=onlinezap \
  -p 5432:5432 \
  postgres:16-alpine

# Update .env
DATABASE_URL=postgresql+asyncpg://onlinezap:password@localhost:5432/onlinezap
```

### Build Frontend

```bash
# Для backend (static files)
cd app && npm run build:backend

# Для frontend app
cd app && npm run build:frontend
```

## Troubleshooting

### Telegram API недоступен

Если порт 443 заблокирован:
- Используйте Telegram Bot API через proxy
- Или переключитесь на Webhook mode

### Database connection errors

Проверьте:
- Правильность DATABASE_URL
- Доступность PostgreSQL сервиса
- Network policies в Amvera

### CORS errors

Убедитесь, что в `webapp/main.py` добавлен домен frontend в `allow_origins`.

## License

MIT
