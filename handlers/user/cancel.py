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

router = Router()


@router.callback_query(lambda c: c.data.startswith("cancel_") and not c.data.startswith("cancel_reschedule") and not c.data.startswith("confirm_cancel") and not c.data.startswith("cancel_action"))
async def handle_cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Начало процесса отмены."""
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
    """Подтверждение отмены."""
    booking_id = int(callback.data.split("_")[2])

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

        # Update status
        await update_booking_status(db, booking_id, "Отменена")

        # Update Google Sheets
        sheet_service = SheetService()
        if booking.google_sheet_row:
            sheet_service.update_booking_status(booking.google_sheet_row, "Отменена")

        # Notify manager
        await _notify_manager(booking, "Отменена")

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
    """Отмена действия отмены (пользователь передумал)."""
    booking_id = int(callback.data.split("_")[1])
    kb = build_booking_action_keyboard(booking_id)
    await callback.message.answer(
        "Отмена отменена. Ваша запись в силе.",
        reply_markup=kb,
    )
    await callback.answer()
