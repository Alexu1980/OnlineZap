import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from handlers.user.start import BookingFSM

logger = logging.getLogger(__name__)
from handlers.user.scheduling import get_available_dates
from keyboards.inline import build_date_keyboard, build_time_keyboard, build_booking_action_keyboard
from database.engine import AsyncSessionLocal
from database.repositories import (
    get_booking_by_id,
    get_bookings_by_user,
    delete_reservation_by_slot_key,
    update_booking_field,
    has_booking_at,
)
from utils.helpers import get_datetime_display

router = Router()


@router.callback_query(lambda c: c.data.startswith("reschedule_"))
async def handle_reschedule_callback(callback: CallbackQuery, state: FSMContext):
    """Начало процесса переноса."""
    booking_id = int(callback.data.split("_")[1])

    async with AsyncSessionLocal() as db:
        booking = await get_booking_by_id(db, booking_id)

    if not booking:
        await callback.message.answer("Запись не найдена.")
        await callback.answer()
        return

    if booking.status == "Отменена":
        await callback.message.answer("Эта запись уже отменена.")
        await callback.answer()
        return

    await state.update_data(reschedule_booking_id=booking_id)
    await state.set_state(BookingFSM.AWAITING_DATE)

    dates = await get_available_dates(booking.specialist_id)
    keyboard = build_date_keyboard(dates, back_callback=f"cancel_reschedule_{booking_id}")

    await callback.message.answer(
        f"🔄 Перенос консультации\n\n"
        f"Текущая запись:\n"
        f"👨‍⚕️ {booking.specialist_name}\n"
        f"📅 {get_datetime_display(booking.consultation_date, booking.consultation_time)}\n\n"
        f"Выберите новую дату:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("cancel_reschedule_"))
async def handle_cancel_reschedule(callback: CallbackQuery, state: FSMContext):
    """Отмена процесса переноса."""
    booking_id = int(callback.data.split("_")[2])
    kb = build_booking_action_keyboard(booking_id)
    await callback.message.answer(
        "Перенос отменён.",
        reply_markup=kb,
    )
    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("date_") and c.data not in ["date_back"])
async def handle_reschedule_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты при переносе."""
    date_str = callback.data.split("_", 1)[1]
    data = await state.get_data()
    booking_id = data.get("reschedule_booking_id")

    if not booking_id:
        await callback.message.answer("Произошла ошибка. Начните заново.")
        await state.clear()
        return

    async with AsyncSessionLocal() as db:
        booking = await get_booking_by_id(db, booking_id)
        if not booking:
            await callback.message.answer("Запись не найдена.")
            await callback.answer()
            return

        from database.repositories import get_available_slots
        from datetime import datetime
        slots = await get_available_slots(db, booking.specialist_id, datetime.strptime(date_str, "%Y-%m-%d"))

    if not slots:
        await callback.message.answer("⚠️ На эту дату нет доступных слотов. Выберите другую.")
        dates = await get_available_dates(booking.specialist_id)
        keyboard = build_date_keyboard(dates, back_callback=f"cancel_reschedule_{booking_id}")
        await callback.message.answer(
            "📅 Выберите новую дату:",
            reply_markup=keyboard,
        )
        return

    await state.update_data(reschedule_date=date_str)
    keyboard = build_time_keyboard(slots, back_callback=f"cancel_reschedule_{booking_id}")
    await callback.message.answer(
        f"🕐 Выберите новое время:\n\n"
        f"{get_datetime_display(date_str, '—')}",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("time_"))
async def handle_reschedule_time(callback: CallbackQuery, state: FSMContext):
    """Выбор времени при переносе."""
    slot_key = callback.data.split("_", 1)[1]
    data = await state.get_data()
    booking_id = data.get("reschedule_booking_id")
    date_str = data.get("reschedule_date")

    if not booking_id or not date_str:
        await callback.message.answer("Произошла ошибка. Начните заново.")
        await state.clear()
        return

    time_part = slot_key.split("_")[-1]

    try:
        new_dt = datetime.strptime(f"{date_str} {time_part}", "%Y-%m-%d %H:%M")
    except ValueError:
        await callback.message.answer("Ошибка при обработке времени.")
        return

    from datetime import timezone
    async with AsyncSessionLocal() as db:
        booking = await get_booking_by_id(db, booking_id)
        if not booking:
            await callback.message.answer("Запись не найдена.")
            return

        # Check if new slot is available
        if await has_booking_at(db, booking.specialist_id, new_dt):
            await callback.message.answer("⚠️ Это время уже занято. Выберите другой слот.")
            return

        # Perform reschedule
        old_date = booking.consultation_date
        old_time = booking.consultation_time

        new_datetime = datetime(
            new_dt.year, new_dt.month, new_dt.day,
            new_dt.hour, new_dt.minute,
            tzinfo=timezone.utc,
        )

        await update_booking_field(db, booking_id, "consultation_date", date_str)
        await update_booking_field(db, booking_id, "consultation_time", time_part)
        await update_booking_field(db, booking_id, "consultation_datetime", new_datetime)
        await update_booking_field(db, booking_id, "status", "Перенесена")
        await db.commit()

        # Update Google Sheets
        from services.sheet_service import SheetService
        sheet_service = SheetService()
        if booking.google_sheet_row:
            sheet_service.update_booking_status(booking.google_sheet_row, "Перенесена")

        # Reschedule reminders
        scheduler = SchedulerService.get_instance()
        if scheduler:
            scheduler.reschedule_reminders(booking_id, new_datetime)

        # Notify manager
        await _notify_manager(booking, f"Перенесена с {old_date} {old_time} на {date_str} {time_part}")

    kb = build_booking_action_keyboard(booking_id)
    await callback.message.answer(
        f"✅ Консультация перенесена!\n\n"
        f"📅 Новая дата: {get_datetime_display(date_str, time_part)}\n\n"
        f"Для управления записью используйте кнопки ниже:",
        reply_markup=kb,
    )
    await state.clear()
    await callback.answer()


from datetime import datetime, timezone
from services.scheduler_service import SchedulerService


async def _notify_manager(booking, reason: str = ""):
    """Уведомление менеджера."""
    from config.settings import settings
    from aiogram import Bot

    msg = (
        f"📋 <b>Заявка #{booking.id}</b>\n\n"
        f"👤 Имя: {booking.user_name}\n"
        f"📱 Телефон: {booking.user_phone}\n"
        f"🔗 Telegram: @{booking.user_username or 'не указан'}\n"
        f"🆔 ID: {booking.user_telegram_id}\n\n"
        f"👨‍⚕️ Специалист: {booking.specialist_name}\n"
        f"📅 Дата: {booking.consultation_date}\n"
        f"🕐 Время: {booking.consultation_time}\n"
        f"📊 Статус: {booking.status}"
    )
    if booking.additional_info:
        msg += f"\n\n💬 Комментарий: {booking.additional_info}"
    if reason:
        msg += f"\n\n📝 {reason}"

    try:
        from main import _bot_ref as bot
        if bot:
            await bot.send_message(
                chat_id=settings.admin_chat_id,
                text=msg,
                parse_mode="HTML",
            )
    except Exception as e:
        logger = __import__('logging').getLogger(__name__)
        logger.error(f"Ошибка уведомления менеджера: {e}")
