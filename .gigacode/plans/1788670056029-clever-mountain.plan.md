# План: Telegram бот для записи на консультацию

## Стек технологий
- **Python 3.10+**
- **aiogram 3.x** — async Telegram bot framework
- **SQLite + SQLAlchemy 2.0 (async)** — локальное хранение состояния
- **Google Sheets API v4 (gspread)** — запись заявок
- **APScheduler (AsyncIOScheduler)** — напоминания
- **pydantic-settings** — конфигурация из `.env`

## Структура проекта

```
OnlineZap/
├── .env                          # Переменные окружения
├── .env.example                  # Шаблон .env
├── requirements.txt              # Зависимости
├── main.py                       # Точка входа
├── config/
│   ├── __init__.py
│   └── settings.py               # Pydantic Settings из .env
├── database/
│   ├── __init__.py
│   ├── models.py                 # SQLAlchemy ORM модели
│   ├── engine.py                 # Async engine + инициализация
│   └── repositories.py           # CRUD операции
├── services/
│   ├── __init__.py
│   ├── booking_service.py        # Логика: создать/перенести/отменить
│   ├── sheet_service.py          # Google Sheets API
│   └── scheduler_service.py      # APScheduler напоминаний
├── handlers/
│   ├── __init__.py
│   ├── user/
│   │   ├── __init__.py
│   │   ├── start.py              # /start, приветствие
│   │   ├── consent.py            # Согласие на ПДН
│   │   ├── specialist.py         # Выбор специалиста
│   │   ├── scheduling.py         # Дата и время
│   │   ├── contacts.py           # Контакты (имя, телефон)
│   │   ├── additional.py         # Дополнительный вопрос
│   │   ├── review.py             # Проверка и подтверждение
│   │   ├── reschedule.py         # Перенос консультации
│   │   └── cancel.py             # Отмена консультации
│   └── admin/
│       ├── __init__.py
│       ├── bookings.py           # Просмотр/управление заявками
│       └── sheets.py             # Отладка синхронизации с Sheets
├── keyboards/
│   ├── __init__.py
│   └── inline.py                 # Все inline-клавиатуры
├── middlewares/
│   ├── __init__.py
│   └── database.py               # DB session middleware
├── filters/
│   ├── __init__.py
│   └── admin.py                  # Фильтр админа
├── exceptions/
│   ├── __init__.py
│   └── booking.py                # Кастомные исключения
└── utils/
    ├── __init__.py
    ├── slot_lock.py              # Механизм блокировки слотов
    ├── reminders.py              # Форматирование напоминаний
    └── helpers.py                # Утилиты (форматирование телефона и т.д.)
```

## Схема базы данных (SQLite)

### bookings
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | Внутренний ID |
| user_telegram_id | BIGINT | Telegram user ID |
| user_username | TEXT | Telegram username |
| user_name | TEXT | Имя клиента |
| user_phone | TEXT | Телефон |
| specialist_id | INTEGER | Специалист (FK) |
| specialist_name | TEXT | Имя специалиста |
| consultation_date | TEXT | YYYY-MM-DD |
| consultation_time | TEXT | HH:MM |
| consultation_datetime | DATETIME | Полная дата (UTC) |
| additional_info | TEXT | Доп. информация |
| status | TEXT | Подтверждена/Перенесена/Отменена |
| manager_comment | TEXT | Комментарий менеджера |
| reminder_24h_sent | BOOLEAN | Напоминание 24ч отправлено |
| reminder_2h_sent | BOOLEAN | Напоминание 2ч отправлено |
| created_at | DATETIME | Дата создания |
| updated_at | DATETIME | Дата обновления |

### slot_reservations
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| slot_key | TEXT UNIQUE | {specialist_id}_{date}_{time} |
| user_telegram_id | BIGINT | Кто зарезервировал |
| expires_at | DATETIME | Время истечения |

### specialists (справочник)
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | Имя |
| specialization | TEXT | Специализация |

### availability (расписание специалистов)
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| specialist_id | INTEGER | Специалист |
| day_of_week | INTEGER | 0=Пн...6=Вс |
| start_time | TEXT | HH:MM |
| end_time | TEXT | HH:MM |

### consent_log
| Колонка | Тип | Описание |
|---|---|---|
| id | INTEGER PK | |
| user_telegram_id | BIGINT UNIQUE | |
| consented_at | DATETIME | |
| consent_version | TEXT | Версия текста согласия |

## Машина состояний (FSM)

```
/start → Welcome → "Записаться"
  ↓
AWAITING_CONSENT → "Согласен(а)" → CONSENT_GIVEN
  ↓
AWAITING_SPECIALIST → выбор специалиста
  ↓
AWAITING_DATE → выбор даты → AWAITING_TIME → выбор времени (резерв слота 5 мин)
  ↓
AWAITING_NAME → ввод имени → AWAITING_PHONE → ввод телефона
  ↓
AWAITING_ADDITIONAL → доп. вопрос (опционально) → AWAITING_REVIEW
  ↓
Обзор данных �� "Подтвердить" → CONFIRMED
                    → "Изменить" → возврат на нужный шаг
```

## Ключевые механизмы

### Защита от двойной записи
- При выборе времени слот резервируется в `slot_reservations` с TTL (по умолчанию 5 мин)
- Если слот зарезервирован и не истёк — другому пользователю недоступен
- Истёкшие резервы очищаются периодической задачей (каждую минуту)
- При подтверждении записи резерв удаляется, создаётся запись в `bookings`

### Google Sheets (Service Account)
- `gspread` + `google-auth` с JSON credentials
- 11 столбцов: ID, Дата создания, Имя, Телефон, Username, Telegram ID, Специалист, Дата, Время, Статус, Комментарий
- При перезапуске бота: `_schedule_all_pending_reminders()` восстанавливает напоминания из БД

### Напоминания (APScheduler)
- Два напоминания: за 24ч и за 2ч до консультации
- При подтверждении записи — планируются триггеры
- При перезапуске бота — все будущие записи пересчитываются

## Конфигурация (.env)

```env
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_IDS=123456789
GOOGLE_SHEETS_CREDENTIALS_PATH=credentials.json
GOOGLE_SHEET_ID=your_spreadsheet_id_here
SLOT_DURATION_MINUTES=60
RESERVATION_TIMEOUT_SECONDS=300
REMINDER_24H_ENABLED=true
REMINDER_2H_ENABLED=true
DATABASE_URL=sqlite+aiosqlite:///./bookings.db
ADMIN_CHAT_ID=-1001234567890
```

## Зависимости (requirements.txt)

```
aiogram>=3.10.0
aiohttp>=3.9.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
SQLAlchemy[asyncio]>=2.0.25
aiosqlite>=0.19.0
apscheduler>=3.10.4
gspread>=6.1.0
google-auth>=2.23.0
python-dateutil>=2.8.0
```

## Порядок реализации (фазы)

### Фаза 1: Фундамент (features 1-2)
1. Структура проекта, `__init__.py`, `.env.example`
2. `config/settings.py` — pydantic settings
3. `requirements.txt`, установка зависимостей
4. `database/engine.py` — async engine, инициализация таблиц
5. `database/models.py` — ORM модели
6. `database/repositories.py` — CRUD для consent_log, specialists
7. `keyboards/inline.py` — клавиатуры приветствия и согласия
8. `handlers/user/start.py` — /start, приветствие
9. `handlers/user/consent.py` — согласие на ПДН
10. `main.py` — сборка приложения, регистрация обработчиков

### Фаза 2: Основной поток записи (features 3-7)
11. `database/repositories.py` — запросы специалистов, доступности
12. `handlers/user/specialist.py` — выбор специалиста
13. `keyboards/inline.py` — клавиатуры специалистов, дат, времени
14. `handlers/user/scheduling.py` — выбор даты/времени, slot_lock
15. `utils/slot_lock.py` — резервирование слотов с TTL
16. `handlers/user/contacts.py` — имя, телефон (кнопка «Поделиться»)
17. `handlers/user/additional.py` — доп. вопрос
18. `middlewares/database.py` — DB session middleware
19. `filters/admin.py` — фильтр админа

### Фаза 3: Подтверждение и интеграция (features 8-11)
20. `handlers/user/review.py` — экран проверки данных
21. `services/booking_service.py` — create_booking()
22. `services/sheet_service.py` — Google Sheets append
23. Уведомление менеджеру в отдельный чат
24. Запись в Google Sheets

### Фаза 4: Напоминания и перенос (features 12-13)
25. `services/scheduler_service.py` — APScheduler
26. `utils/reminders.py` — форматирование напоминаний
27. Интеграция scheduler в main.py
28. `handlers/user/reschedule.py` — перенос консультации
29. `services/booking_service.py` — reschedule_booking()

### Фаза 5: Отмена и админ (features 14-15)
30. `handlers/user/cancel.py` — отмена с подтверждением
31. `services/booking_service.py` — cancel_booking()
32. `handlers/admin/bookings.py` — управление заявками

### Фаза 6: Полировка
33. Периодическая очистка истёкших резервов
34. Обработка ошибок, логирование
35. Тестирование полного потока
