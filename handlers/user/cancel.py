import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.engine import AsyncSessionLocal
from database.repositories import (
    get_booking_by_id,
    update_booking_status,
    delete_reservation_by_slot_key,
)
from keyboards.inline import build_booking_action_keyboard, build_confirm_cancel_keyboard
from utils.helpers import get_datetime_display
from services.sheet_service import SheetService
from services.scheduler_service import SchedulerService
from handlers.user.reschedule import _notify_manager

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(lambda c: c.data.startswith("cancel_") and not c.data.startswith("cancel_reschedule") and not c.data.startswith("confirm_cancel") and not c.data.startswith("cancel_action"))
async def handle_cancel_callback(callback: CallbackQuery, state: FSMContext):
    # Проверяем что callback имеет формат cancel_{booking_id}
    parts = callback.data.split("_")
    if len(parts) != 2:
        logger.warning(f"[CANCEL] Invalid callback format: {callback.data}")
        await callback.answer("Произошла ошибка. Попробуйте снова.")
        return
    
    try:
        booking_id = int(parts[1])
    except ValueError:
        logger.warning(f"[CANCEL] Invalid booking_id in callback: {callback.data}")
        await callback.answer("Произошла ошибка. Попробуйте снова.")
        return
    logger.info(f"[CANCEL_REQUEST] User {callback.from_user.id} requested to cancel booking #{booking_id}")

    async with AsyncSessionLocal() as db:
        booking = await get_booking_by_id(db, booking_id)

    if not booking:
        logger.warning(f"[CANCEL_REQUEST] Booking #{booking_id} not found")
        await callback.message.answer("Запись не найдена.")
        await callback.answer()
        return

    if booking.status == "Отменена":
        logger.warning(f"[CANCEL_REQUEST] Booking #{booking_id} already cancelled")
        await callback.message.answer("Эта запись уже отменена.")
        await callback.answer()
        return

    cancel_msg = (
        f"❌ Отмена консультации\n\n"
        f"👨‍⚕️ Специалист: {booking.specialist_name}\n"
        f"📅 Дата: {get_datetime_display(booking.consultation_date, booking.consultation_time)}\n\n"
        f"Вы уверены, что хотите отменить запись?"
    )

    kb = build_confirm_cancel_keyboard(booking_id)
    await callback.message.answer(cancel_msg, reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("confirm_cancel_"))
async def handle_confirm_cancel(callback: CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.split("_")[2])
    logger.info(f"[CANCEL_CONFIRM] User {callback.from_user.id} confirmed cancellation of booking #{booking_id}")

    async with AsyncSessionLocal() as db:
        booking = await get_booking_by_id(db, booking_id)
        if not booking:
            logger.warning(f"[CANCEL_CONFIRM] Booking #{booking_id} not found")
            await callback.message.answer("Запись не найдена.")
            await callback.answer()
            return

        if booking.status == "Отменена":
            logger.warning(f"[CANCEL_CONFIRM] Booking #{booking_id} already cancelled")
            await callback.message.answer("Эта запись уже отменена.")
            await callback.answer()
            return

        await update_booking_status(db, booking_id, "Отменена")
        logger.info(f"[CANCEL_CONFIRM] Booking #{booking_id} status updated to 'Отменена'")

        sheet_service = SheetService()
        if booking.google_sheet_row:
            sheet_service.update_booking_status(booking.google_sheet_row, "Отменена")
            logger.info(f"[CANCEL_CONFIRM] Google Sheets updated for booking #{booking_id}")

        await _notify_manager(booking, "Отменена")
        logger.info(f"[CANCEL_CONFIRM] Manager notified about cancellation of booking #{booking_id}")

        kb = build_booking_action_keyboard(booking_id)
        await callback.message.answer(
            f"❌ Запись #{booking_id} отменена.\n\n"
            f"Мы освободили зарезервированное время. "
            f"Если у вас есть вопросы, свяжитесь с менеджером.",
            reply_markup=kb,
        )
        await state.clear()

    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("cancel_action_"))
async def handle_cancel_action(callback: CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.split("_")[1])
    logger.info(f"[CANCEL_ACTION] User {callback.from_user.id} cancelled the cancel action for booking #{booking_id}")
    kb = build_booking_action_keyboard(booking_id)
    await callback.message.answer(
        "Отмена отменена. Ваша запись в силе.",
        reply_markup=kb,
    )
    await callback.answer()
