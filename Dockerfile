# =====================
# Этап 1: Сборка фронтенда
# =====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Копируем package.json для кэширования
COPY app/package.json ./

# Устанавливаем зависимости
RUN npm install

# Копируем исходный код
COPY app/ ./

# Собираем фронтенд
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# =====================
# Этап 2: Backend
# =====================
FROM python:3.12-slim AS backend

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
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

# Создаём папку для базы данных
RUN mkdir -p /app/Data

# Открываем порты
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
