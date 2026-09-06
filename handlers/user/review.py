import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from handlers.user.start import BookingFSM
from keyboards.inline import build_review_keyboard
from utils.helpers import get_datetime_display
from database.engine import AsyncSessionLocal
from database.repositories import (
    get_booking_by_id,
    get_bookings_by_user,
    delete_reservation_by_slot_key,
    update_booking_status,
    update_booking_field,
)
from services.booking_service import BookingService
from services.sheet_service import SheetService
from services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "confirm_booking")
async def cb_confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    telegram_username = callback.from_user.username

    try:
        async with AsyncSessionLocal() as db:
            booking = await BookingService.create_booking(
                db=db,
                user_id=user_id,
                telegram_username=telegram_username,
                specialist_id=data["specialist_id"],
                date_str=data["selected_date"],
                time_str=data["selected_time"],
                slot_key=data["slot_key"],
                name=data["user_name"],
                phone=data["user_phone"],
                additional_info=data.get("additional_info"),
            )

            # Clean up reservation
            await delete_reservation_by_slot_key(db, data["slot_key"])
            await db.commit()

        # Clear state
        await state.clear()

        # Send confirmation
        confirm_msg = (
            f"✅ Ваша запись подтверждена!\n\n"
            f"👨‍⚕️ Специалист: {booking['specialist_name']}\n"
            f"📅 Дата: {get_datetime_display(booking['consultation_date'], booking['consultation_time'])}\n"
            f"🕐 Время: {booking['consultation_time']}\n\n"
            f"Мы отправим вам напоминание за 24 часа до консультации.\n\n"
            f"Для управления записью используйте кнопки ниже:"
        )

        from keyboards.inline import build_booking_action_keyboard
        kb = build_booking_action_keyboard(booking["id"])
        await callback.message.answer(confirm_msg, reply_markup=kb)
        await callback.answer()

    except Exception as e:
        logger = __import__('logging').getLogger(__name__)
        logger.error(f"Ошибка при подтверждении записи: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ При создании записи произошла ошибка: {str(e)}\n"
            "Пожалуйста, попробуйте записаться снова."
        )
        await state.clear()


@router.callback_query(F.data == "edit_booking")
async def cb_edit_booking(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingFSM.AWAITING_NAME)
    await callback.message.answer(
        "✏️ Введите ваше имя заново:",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("my_bookings_"))
async def cb_my_bookings(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as db:
        bookings = await get_bookings_by_user(db, user_id)

    if not bookings:
        await callback.message.answer("У вас нет активных записей.")
        await callback.answer()
        return

    msg = "📋 Ваши активные записи:\n\n"
    for b in bookings:
        msg += (
            f"🔹 {get_datetime_display(b.consultation_date, b.consultation_time)}\n"
            f"   👨‍⚕️ {b.specialist_name}\n"
            f"   📊 Статус: {b.status}\n\n"
        )

    from keyboards.inline import build_booking_action_keyboard
    kb = build_booking_action_keyboard(bookings[0].id)
    await callback.message.answer(msg, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("reschedule_"))
async def cb_reschedule(callback: CallbackQuery, state: FSMContext):
    from handlers.user.reschedule import handle_reschedule_callback
    await handle_reschedule_callback(callback, state)


@router.callback_query(F.data.startswith("cancel_"))
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    from handlers.user.cancel import handle_cancel_callback
    await handle_cancel_callback(callback, state)
