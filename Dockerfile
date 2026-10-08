# =====================
# Этап 1: Сборка фронтенда
# =====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Копируем package.json для кэширования
COPY app/package.json ./

# Устанавливаем зависимости
RUN rm -rf node_modules
RUN npm install

# Копируем исходный код
COPY app/ ./

# Собираем фронтенд в dist/
RUN rm -rf node_modules/.vite
RUN npm run build

# =====================
# Этап 2: Backend (Python)
# =====================
FROM python:3.12-slim AS backend

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Python зависимости
WORKDIR /app

# Копируем requirements.txt
COPY requirements.txt .

# Создаём виртуальное окружение и устанавливаем зависимости
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код проекта
COPY . .

# Копируем собранный фронтенд из frontend-builder
COPY --from=frontend-builder /app/dist /app/static/app

# Создаём папку для credentials
RUN mkdir -p /app

# Открываем порты
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Команда запуска (запускает main.py, который включает и бот, и FastAPI)
CMD ["/opt/venv/bin/python3", "main.py"]
