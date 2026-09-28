# 📱 Telegram MiniApp - OnlineZap

## 🚀 Быстрый старт

### 1. Установка зависимостей

#### Backend (Python)
```bash
pip install fastapi uvicorn[standard] python-multipart
```

#### Frontend (Node.js)
```bash
cd app
npm install
```

### 2. Запуск разработки

#### Backend API
```bash
# В основной директории проекта
uvicorn webapp.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd app
npm run dev
```

Frontend будет доступен на: http://localhost:3000/app/
Backend API будет доступен на: http://localhost:8000/api/

### 3. Тестирование с Telegram

#### Локальное тестирование
1. Запустите backend и frontend
2. Используйте ngrok для экспорта локального сервера:
   ```bash
   ngrok http 3000
   ```
3. Полученный URL (например, `https://abc123.ngrok.io`) используйте как `MINIAPP_URL` в `.env`
4. Откройте бота в Telegram и нажмите кнопку "Записаться через MiniApp"

#### Продакшен
1. Соберите фронтенд:
   ```bash
   cd app
   npm run build
   ```
2. Файлы будут в `static/app/`
3. Настройте HTTPS через Nginx/Caddy или используйте хостинг с поддержкой HTTPS
4. Обновите `MINIAPP_URL` в `.env` на реальный домен

## 📁 Структура MiniApp

```
app/
├── src/
│   ├── components/          # React компоненты
│   │   ├── ClinicHeader.tsx    # Логотип и название клиники
│   │   ├── SpecialistSelect.tsx # Выбор специалиста
│   │   ├── Calendar.tsx        # Календарь с датами
│   │   ├── TimeSlots.tsx       # Временные слоты
│   │   ├── ContactForm.tsx     # Форма контактов
│   │   └── Confirmation.tsx    # Подтверждение записи
│   ├── store/               # State management (Zustand)
│   ├── api/                 # API клиент и типы
│   ├── styles/              # CSS стили
│   └── App.tsx              # Главное приложение
├── package.json
├── vite.config.ts
└── tailwind.config.js
```

## 🔧 Настройка

### Переменные окружения

Добавьте в `.env`:
```env
MINIAPP_URL=http://localhost:3000/app
```

Для продакшена замените на реальный HTTPS URL.

### API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/specialists` | Список специалистов |
| GET | `/api/specialists/{id}` | Данные специалиста |
| GET | `/api/availability?specialist_id=&days=` | Доступные даты |
| GET | `/api/slots?specialist_id=&date=` | Временные слоты |
| POST | `/api/bookings` | Создание бронирования |

## 🎨 Кастомизация

### Изменение названия клиники и логотипа

Отредактируйте `app/src/components/ClinicHeader.tsx`:
```tsx
// Название клиники
<h1 className="text-lg font-bold">Ваша Клиника</h1>

// Логотип (замените SVG на изображение)
<img src="/logo.png" alt="Логотип" className="w-12 h-12" />
```

### Цветовая схема

Отредактируйте `app/tailwind.config.js`:
```javascript
theme: {
  extend: {
    colors: {
      primary: '#YOUR_COLOR',
      secondary: '#YOUR_COLOR',
    },
  },
}
```

## 🐛 Устранение неполадок

### Frontend не загружается
- Убедитесь, что dependencies установлены: `npm install`
- Проверьте порт: по умолчанию 3000
- Очистите кэш браузера

### Backend не отвечает
- Убедитесь, что dependencies установлены
- Проверьте порт: по умолчанию 8000
- Проверьте `.env` файл

### Telegram не открывает MiniApp
- Убедитесь, что URL использует HTTPS
- Проверьте `MINIAPP_URL` в `.env`
- Используйте ngrok для локального тестирования

## 📚 Дополнительные ресурсы

- [Telegram Web Apps Docs](https://core.telegram.org/bots/webapps)
- [React Docs](https://react.dev)
- [Vite Docs](https://vitejs.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [Zustand](https://github.com/pmndrs/zustand)
