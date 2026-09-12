from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from database.repositories import (
    get_all_bookings,
    get_booking_by_id,
    get_bookings_by_status,
    update_manager_comment,
    update_booking_status,
)
from keyboards.inline import build_confirm_cancel_keyboard
from services.booking_service import BookingService
from utils.helpers import get_datetime_display

router = Router()


@router.message(Command("bookings"))
async def cmd_bookings(message: Message, db_session):
    """Просмотр всех активных записей."""
    bookings = await get_all_bookings(db_session, limit=50)

    if not bookings:
        await message.answer("📋 Нет активных записей.")
        return

    msg = "📋 <b>Все записи (последние 50):</b>\n\n"
    for b in bookings[:20]:  # Limit display
        msg += (
            f"🔹 <b>#{b.id}</b> | {b.status}\n"
            f"   👤 {b.user_name} (@{b.user_username or 'n/a'})\n"
            f"   👨‍⚕️ {b.specialist_name}\n"
            f"   📅 {b.consultation_date} {b.consultation_time}\n\n"
        )

    if len(bookings) > 20:
        msg += f"... и ещё {len(bookings) - 20} записей"

    await message.answer(msg, parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("booking_status_"))
async def cb_update_status(callback: CallbackQuery, db_session):
    """Обновление статуса записи."""
    parts = callback.data.split("_")
    booking_id = int(parts[2])
    new_status = parts[3] if len(parts) > 3 else "Подтверждена"

    await update_booking_status(db_session, booking_id, new_status)
    await callback.message.answer(f"Статус записи #{booking_id} обновлён на {new_status}.")
    await callback.answer()
    """Обновление статуса записи."""
    parts = callback.data.split("_")
    booking_id = int(parts[2])
    new_status = parts[3] if len(parts) > 3 else "Подтверждена"

    await callback.message.answer(f"Статус записи #{booking_id} обновлён на {new_status}.")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_comment_"))
async def cb_admin_comment(callback: CallbackQuery, state: FSMContext, db_session):
    """Запрос комментария менеджера."""
    booking_id = int(callback.data.split("_")[2])
    await state.update_data(admin_comment_booking_id=booking_id)
    await state.set_state("ADMIN_AWAITING_COMMENT")

    await callback.message.answer(
        f"Введите комментарий для записи #{booking_id}:"
    )
    await callback.answer()


@router.message(F.text & ~Command("admin_view", "test_base", "bookings", "sync"))
async def handle_admin_comment(message: Message, state: FSMContext, db_session):
    """Обработка комментария менеджера."""
    data = await state.get_data()
    booking_id = data.get("admin_comment_booking_id")

    if booking_id:
        await update_manager_comment(db_session, booking_id, message.text)

        from services.sheet_service import SheetService
        sheet_service = SheetService()
        booking = await get_booking_by_id(db_session, booking_id)
        if booking and booking.google_sheet_row:
            sheet_service.update_booking_comment(booking.google_sheet_row, message.text)

        await message.answer(f"✅ Комментарий для записи #{booking_id} сохранён.")
        await state.clear()


@router.callback_query(lambda c: c.data.startswith("admin_bookings_"))
async def cb_admin_bookings(callback: CallbackQuery, db_session):
    """Фильтрация записей по статусу."""
    status = callback.data.split("_", 2)[2]

    bookings = await get_bookings_by_status(db_session, status)

    if not bookings:
        await callback.message.answer(f"📋 Нет записей со статусом: {status}")
        await callback.answer()
        return

    msg = f"📋 Записи со статусом: <b>{status}</b>\n\n"
    for b in bookings[:30]:
        msg += (
            f"🔹 <b>#{b.id}</b>\n"
            f"   👤 {b.user_name} | 📱 {b.user_phone}\n"
            f"   👨‍⚕️ {b.specialist_name}\n"
            f"   📅 {b.consultation_date} {b.consultation_time}\n"
            f"   💬 {b.manager_comment or 'нет'}\n\n"
        )

    await callback.message.answer(msg, parse_mode="HTML")
    await callback.answer()
