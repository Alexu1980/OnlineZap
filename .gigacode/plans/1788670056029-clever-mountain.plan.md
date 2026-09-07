# План реализации личного кабинета

## Цель
Добавить личный кабинет с кнопкой "Мои записи" в главное меню с возможностью:
- Просмотра всех записей (подтверждённые, завершённые, отменённые)
- Быстрых действий: перенос, отмена для активных записей
- Фильтрации по статусу
- Просмотра детальной информации по каждой записи

## Изменяемые файлы

### 1. `keyboards/inline.py`
- Добавить кнопку "📋 Мои записи" в `build_welcome_keyboard()`
- Создать `build_personal_cabinet_keyboard()` для навигации по записям

### 2. `handlers/user/personal_cabinet.py` (новый файл)
- Обработчик `/my_bookings` или callback `personal_cabinet`
- Отображение списка всех подтверждённых записей пользователя
- Для каждой записи: дата, время, специалист, статус
- Кнопки для каждой записи: перенос, отмена
- Пагинация если записей много
- Обработка случая когда записей нет

### 3. `handlers/user/start.py`
- Добавить регистрацию router из `handlers/user/personal_cabinet.py`

### 4. `main.py`
- Добавить импорт и регистрацию router personal_cabinet

### 5. `utils/helpers.py`
- Убедиться что есть функция для красивого форматирования даты/времени

## Реализация

### Шаг 1: Обновить клавиатуру
```python
def build_welcome_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Записаться на консультацию", callback_data="start_booking")
    builder.button(text="📋 Мои записи", callback_data="personal_cabinet")
    builder.adjust(1, 1)
    return builder.as_markup()
```

### Шаг 2: Создать handler personal_cabinet.py
```python
@router.callback_query(F.data == "personal_cabinet")
async def cb_personal_cabinet(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as db:
        bookings = await get_bookings_by_user(db, user_id)
    
    if not bookings:
        await callback.message.answer(
            "📋 У вас пока нет записей.\n\n"
            "Записаться на консультацию можно по кнопке ниже:",
            reply_markup=build_welcome_keyboard()
        )
        return
    
    # Отобразить записи (макс 5 на экран)
    for booking in bookings[:5]:
        kb = build_booking_action_keyboard(booking.id)
        message = format_booking_message(booking)
        await callback.message.answer(message, reply_markup=kb)
    
    await callback.answer()
```

### Шаг 3: Форматирование записи
```python
def format_booking_message(booking) -> str:
    return (
        f"📅 {booking.consultation_date} в {booking.consultation_time}\n"
        f"👨‍⚕️ Специалист: {booking.specialist_name}\n"
        f"📊 Статус: {booking.status}\n"
        f"🆔 ID: {booking.id}"
    )
```

### Шаг 4: Регистрация router
В `main.py` добавить:
```python
from handlers.user import personal_cabinet as user_personal_cabinet
dp.include_router(user_personal_cabinet.router)
```

## Проверка
1. Нажать `/start`
2. Нажать "📋 Мои записи"
3. Проверить отображение записей
4. Проверить кнопки переноса/отмены
5. Проверить отображение когда записей нет
