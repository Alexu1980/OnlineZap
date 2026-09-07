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

    logger.info(f"[CONFIRM] User {user_id} confirmed booking: specialist={data.get('specialist_id')}, date={data.get('selected_date')}, time={data.get('selected_time')}")
    logger.info(f"[CONFIRM] User data: name={data.get('user_name')}, phone={data.get('user_phone')}")

    try:
        async with AsyncSessionLocal() as db:
            logger.info(f"[CONFIRM] Starting booking creation for user {user_id}")
            logger.info(f"[CONFIRM] Data: specialist={data.get('specialist_id')}, date={data.get('selected_date')}, time={data.get('selected_time')}")
            logger.info(f"[CONFIRM] User data: name={data.get('user_name')}, phone={data.get('user_phone')}")
            logger.info(f"[CONFIRM] Slot key: {data.get('slot_key')}")
            
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

            # Освобождаем резерв слота
            logger.info(f"[CONFIRM] Deleting reservation for slot {data.get('slot_key')}")
            await delete_reservation_by_slot_key(db, data["slot_key"])
            logger.info(f"[CONFIRM] Booking #{booking['id']} saved successfully")

        logger.info(f"[CONFIRM] Booking #{booking['id']} created successfully for user {user_id}")

        await state.clear()

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
        logger.info(f"[CONFIRM] Confirmation message sent to user {user_id}")

    except Exception as e:
        logger.error(f"[CONFIRM] Error creating booking for user {user_id}: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ При создании записи произошла ошибка: {str(e)}\n"
            "Пожалуйста, попробуйте записаться снова."
        )
        await state.clear()


@router.callback_query(F.data == "edit_booking")
async def cb_edit_booking(callback: CallbackQuery, state: FSMContext):
    logger.info(f"[EDIT] User {callback.from_user.id} requested to edit booking data")
    await state.set_state(BookingFSM.AWAITING_NAME)
    await callback.message.answer(
        "✏️ Введите ваше имя заново:",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("my_bookings_"))
async def cb_my_bookings(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"[MY_BOOKINGS] User {user_id} requested their bookings")
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
    logger.info(f"[MY_BOOKINGS] Showing {len(bookings)} bookings to user {user_id}")


@router.callback_query(F.data.startswith("reschedule_"))
async def cb_reschedule(callback: CallbackQuery, state: FSMContext):
    from handlers.user.reschedule import handle_reschedule_callback
    logger.info(f"[RESCHEDULE] User {callback.from_user.id} clicked reschedule")
    await handle_reschedule_callback(callback, state)


@router.callback_query(F.data.startswith("cancel_"))
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    # Проверяем тип callback
    if callback.data.startswith("cancel_action_") or callback.data.startswith("confirm_cancel_"):
        # Это внутренние callback для отмены/подтверждения - передаём в cancel.py
        pass
    
    from handlers.user.cancel import handle_cancel_callback
    logger.info(f"[CANCEL] User {callback.from_user.id} clicked cancel")
    await handle_cancel_callback(callback, state)
