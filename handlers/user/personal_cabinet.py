import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.engine import AsyncSessionLocal
from database.repositories import get_bookings_by_user, get_booking_by_id, update_booking_status, get_all_bookings
from keyboards.inline import build_booking_action_keyboard, build_welcome_keyboard
from utils.helpers import get_datetime_display

logger = logging.getLogger(__name__)
router = Router()

# Проверяем что datetime доступен
assert datetime is not None, "datetime должен быть импортирован"


@router.callback_query(F.data == "personal_cabinet")
async def cb_personal_cabinet(callback: CallbackQuery):
    """Открытие личного кабинета с отображением всех записей."""
    logger.info(f"[PERSONAL_CABINET] User {callback.from_user.id} opened personal cabinet")
    user_id = callback.from_user.id
    
    async with AsyncSessionLocal() as db:
        # Получаем все записи (не только подтверждённые)
        from database.repositories import get_all_bookings
        all_bookings = await get_all_bookings(db, limit=50)
        user_bookings = [b for b in all_bookings if b.user_telegram_id == user_id]
    
    if not user_bookings:
        await callback.message.answer(
            "📋 У вас пока нет записей.\n\n"
            "Записаться на консультацию можно по кнопке ниже:",
            reply_markup=build_welcome_keyboard(),
        )
        await callback.answer()
        return
    
    # Сортируем: сначала будущие, потом прошлые
    from datetime import datetime, timezone
    
    # Получаем текущее время без timezone для сравнения
    now_naive = datetime.now()
    
    active_bookings = []
    past_bookings = []
    
    for booking in user_bookings:
        # Конвертируем consultation_datetime в naive если нужно
        consult_dt = booking.consultation_datetime
        if consult_dt and consult_dt.tzinfo is not None:
            consult_dt = consult_dt.replace(tzinfo=None)
        
        if consult_dt and consult_dt > now_naive:
            if booking.status != "Отменена":
                active_bookings.append(booking)
        else:
            past_bookings.append(booking)
    
    # Отображаем активные записи
    if active_bookings:
        await callback.message.answer(
            "📋 <b>Мои записи:</b>",
            parse_mode="HTML",
        )
        
        for booking in active_bookings[:5]:  # Максимум 5 записей на экран
            message = _format_booking_message(booking)
            kb = build_booking_action_keyboard(booking.id)
            
            try:
                await callback.message.answer(message, reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                logger.error(f"[PERSONAL_CABINET] Error sending booking message: {e}")
    
    # Кнопка для просмотра истории
    if past_bookings:
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"📜 История ({len(past_bookings)} записей)",
            callback_data="past_bookings",
        )
        builder.button(
            text="← Назад",
            callback_data="personal_cabinet",
        )
        builder.adjust(1, 1)
        
        await callback.message.answer(
            f"📜 У вас есть {len(past_bookings)} завершённых/отменённых записей.\n"
            "Нажмите на кнопку ниже, чтобы посмотреть историю.",
            reply_markup=builder.as_markup(),
        )
    
    await callback.answer()


@router.callback_query(F.data == "past_bookings")
async def cb_past_bookings(callback: CallbackQuery):
    """Отображение прошлых записей."""
    logger.info(f"[PAST_BOOKINGS] User {callback.from_user.id} viewing past bookings")
    user_id = callback.from_user.id
    
    async with AsyncSessionLocal() as db:
        from database.repositories import get_all_bookings
        all_bookings = await get_all_bookings(db, limit=50)
        user_bookings = [b for b in all_bookings if b.user_telegram_id == user_id]
    
    from datetime import datetime, timezone
    # Используем naive datetime для сравнения
    now_naive = datetime.now()
    past_bookings = []
    
    for b in user_bookings:
        consult_dt = b.consultation_datetime
        if consult_dt and consult_dt.tzinfo is not None:
            consult_dt = consult_dt.replace(tzinfo=None)
        
        if not b.consultation_datetime or consult_dt <= now_naive or b.status == "Отменена":
            past_bookings.append(b)
    
    if not past_bookings:
        await callback.message.answer("История записей пуста.")
        await callback.answer()
        return
    
    # Отображаем историю
    await callback.message.answer(
        "📜 <b>История записей:</b>",
        parse_mode="HTML",
    )
    
    for booking in past_bookings[:10]:  # Максимум 10 записей
        message = _format_booking_message(booking, show_history=True)
        await callback.message.answer(message, parse_mode="HTML")
    
    await callback.answer()


@router.callback_query(F.data == "back_to_cabinet")
async def cb_back_to_cabinet(callback: CallbackQuery):
    """Возврат в личный кабинет."""
    logger.info(f"[BACK_TO_CABINET] User {callback.from_user.id} returning to cabinet")
    await cb_personal_cabinet(callback)


def _format_booking_message(booking, show_history: bool = False) -> str:
    """Форматирование сообщения о записи."""
    date_str = booking.consultation_date or "Не указана"
    time_str = booking.consultation_time or "Не указано"
    specialist = booking.specialist_name or "Не указан"
    status = booking.status or "Неизвестно"
    
    # Форматируем дату для отображения
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = dt.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        date_display = date_str
    
    status_emoji = {
        "Подтверждена": "✅",
        "Отменена": "❌",
        "Завершена": "✔️",
        "Ожидает": "⏳",
    }
    status_icon = status_emoji.get(status, "📌")
    
    message = (
        f"{status_icon} <b>Запись #{booking.id}</b>\n\n"
        f"📅 Дата: {date_display}\n"
        f"🕐 Время: {time_str}\n"
        f"👨‍⚕️ Специалист: {specialist}\n"
        f"📊 Статус: {status}"
    )
    
    if booking.manager_comment:
        message += f"\n\n💬 <b>Комментарий:</b> {booking.manager_comment}"
    
    if show_history:
        try:
            created_at = booking.created_at.strftime("%d.%m.%Y %H:%M") if booking.created_at else "Неизвестно"
            message += f"\n\n📝 Дата создания: {created_at}"
        except Exception:
            pass
    
    return message
