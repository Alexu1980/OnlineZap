# 🔧 Настройка Google Sheets для бота

## 📋 Требования

### 1. Google Cloud Project
1. Зайдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект (или используйте существующий)
3. Включите API: **Google Sheets API**
   - API & Services → Library → search "Google Sheets API" → Enable

### 2. Service Account
1. Перейдите в **API & Services → Credentials**
2. Нажмите **Create Credentials → Service account**
3. Заполните:
   - Account ID: `bot-sheets`
   - Name: `Bot Google Sheets`
4. Нажмите **Create and Continue** → **Done**

### 3. Создание ключа (JSON)
1. Найдите созданного Service Account в списке
2. Нажмите **⋮ (actions) → Manage keys**
3. Нажмите **Add key → Create new key**
4. Выберите **JSON** → **Create**
5. Файл `credentials.json` скачается в Downloads

### 4. Настройка файла credentials.json
Файл содержит:
```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "bot-sheets@project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

**ВАЖНО:** `client_email` — это email, который нужно добавить в Google таблицу!

### 5. Создание Google Таблицы
1. Создайте новую таблицу в Google Sheets
2. Назовите лист (внизу) `Bookings` (или другое в `.env`)
3. Добавьте заголовки (строка 1):
   ```
   A: ID
   B: Дата создания
   C: Имя
   D: Телефон
   E: Username
   F: Telegram ID
   G: Специалист
   H: Дата консультации
   I: Время
   J: Статус
   K: Комментарий
   ```

### 6. Доступ к таблице
1. Нажмите кнопку **Поделиться** (справа сверху)
2. Введите email из `client_email` в credentials.json
3. Выберите роль: **Редактор** (Editor)
4. Нажмите **Share**

### 7. Получение ID таблицы
URL таблицы:
```
https://docs.google.com/spreadsheets/d/ЭТО_ID/edit#gid=0
```

ID таблицы: `ЭТО_ID` (длинная строка между `/d/` и `/edit`)

### 8. Настройка .env
```env
# Путь к credentials.json
GOOGLE_SHEETS_CREDENTIALS_PATH=credentials.json

# ID таблицы
GOOGLE_SHEET_ID=your_long_sheet_id_here

# Название листа (должно совпадать с вкладкой внизу)
GOOGLE_SHEET_NAME=Bookings
```

### 9. Размещение файла
Файл `credentials.json` нужно поместить туда, где бот его найдёт:

**Варианты:**
```
Проект/
├── credentials.json          # В корне (если GOOGLE_SHEETS_CREDENTIALS_PATH=credentials.json)
├── .env
└── main.py
```

**ИЛИ на сервере:**
```
/app/
├── app/
│   └── credentials.json      # Если GOOGLE_SHEETS_CREDENTIALS_PATH=/app/app/credentials.json
├── .env
└── main.py
```

## ✅ Проверка

### 1. Проверка файла credentials.json
```bash
# Файл существует?
ls -la credentials.json

# Валидный JSON?
python -c "import json; json.load(open('credentials.json')); print('OK')"
```

### 2. Проверка доступа к таблице
```python
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(
    'credentials.json',
    scopes=SCOPES
)
client = gspread.Client(credentials=creds, scope=SCOPES)
client.authorize()

# Открываем таблицу
sheet = client.open_by_key('YOUR_SHEET_ID')
print(f"Таблица: {sheet.title}")

# Получаем лист
worksheet = sheet.worksheet('Bookings')
print(f"Лист: {worksheet.title}")
print(f"Строк: {worksheet.row_count}")
```

### 3. Проверка через бота
1. Запустите бота
2. Запишитесь на консультацию
3. Проверьте Google Sheets — должна появиться новая строка

## 🐛 Возможные проблемы

### ❌ "Лист 'Bookings' не найден"
**Решение:** Проверьте название листа (вкладка внизу таблицы). Должно совпадать с `GOOGLE_SHEET_NAME` в `.env`

### ❌ "Permission denied"
**Решение:** Убедитесь, что `client_email` из credentials.json добавлен в таблицу как Редактор

### ❌ "Invalid credentials"
**Решение:** 
- Проверьте, что файл credentials.json не повреждён
- Убедитесь, что это JSON, а не текст
- Проверьте, что Service Account активен

### ❌ "Quota exceeded"
**Решение:** Лимит API исчерпан. Подождите или увеличьте квоту в Google Cloud Console

## 📊 Структура таблицы

| Столбец | Поле | Пример |
|---------|------|--------|
| A | ID | 1 |
| B | Дата создания | 2026-09-07 14:30 |
| C | Имя | Алексей |
| D | Телефон | +79644203553 |
| E | Username | @alexey |
| F | Telegram ID | 1853449775 |
| G | Специалист | Анна Петрова |
| H | Дата консультации | 2026-10-05 |
| I | Время | 14:00 |
| J | Статус | Подтверждена |
| K | Комментарий | |

## 🔒 Безопасность

- **НИКОГДА** не коммитьте credentials.json в git
- Файл уже добавлен в `.gitignore`
- На сервере храните в защищённой директории
- Регулярноrotate ключи (создавайте новые и удаляйте старые)
