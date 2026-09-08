import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.engine import AsyncSessionLocal
from database.repositories import (
    get_available_slots,
    get_active_reservation,
    has_booking_at,
    create_reservation,
    get_active_specialists,
    get_all_availability,
)
from exceptions.booking import SlotAlreadyReserved, SlotAlreadyBooked
from utils.helpers import get_future_dates, get_date_display
from keyboards.inline import build_date_keyboard, build_time_keyboard
from handlers.user.start import BookingFSM
from config.settings import settings

logger = logging.getLogger(__name__)
router = Router()


async def get_available_dates(specialist_id: int) -> list:
    """Возвращает список дат с хотя бы одним доступным слотом."""
    dates = get_future_dates(30)
    available_dates = []

    async with AsyncSessionLocal() as db:
        availabilities = await get_all_availability(db)
        for date_str in dates:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue

            day_of_week = dt.weekday()
            has_availability = any(
                a.specialist_id == specialist_id and a.day_of_week == day_of_week
                for a in availabilities
            )
            if not has_availability:
                continue

            slots = await get_available_slots(db, specialist_id, dt)
            if slots:
                available_dates.append(date_str)

    return available_dates


@router.callback_query(lambda c: c.data.startswith("date_"))
async def cb_select_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_", 1)[1]
    logger.info(f"[DATE] User {callback.from_user.id} selected date {date_str}")

    # Проверяем, не является ли это переносом (обработается в reschedule.py)
    data = await state.get_data()
    if data.get("reschedule_booking_id"):
        # Это перенос - передаём обработку в reschedule.py
        from handlers.user.reschedule import handle_reschedule_date
        await handle_reschedule_date(callback, state)
        return

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"[DATE] Invalid date format from user {callback.from_user.id}: {date_str}")
        await callback.answer("Неверный формат даты.")
        return

    specialist_id = data.get("specialist_id")

    if not specialist_id:
        logger.error(f"[DATE] No specialist_id in state for user {callback.from_user.id}")
        await callback.message.answer("Произошла ошибка. Начните заново: /start")
        await state.clear()
        return

    async with AsyncSessionLocal() as db:
        slots = await get_available_slots(db, specialist_id, selected_date)

    logger.info(f"[DATE] Found {len(slots)} slots for user {callback.from_user.id} on {date_str}")

    if not slots:
        logger.info(f"[DATE] No slots available for user {callback.from_user.id} on {date_str}")
        await callback.message.answer(
            "⚠️ На эту дату нет доступных слотов. Пожалуйста, выберите другую дату."
        )
        dates = await get_available_dates(specialist_id)
        keyboard = build_date_keyboard(dates, back_callback="back_to_specialist")
        await callback.message.answer(
            "📅 Выберите другую дату:",
            reply_markup=keyboard,
        )
        return

    await state.update_data(selected_date=date_str)
    await state.set_state(BookingFSM.AWAITING_TIME)

    keyboard = build_time_keyboard(slots, back_callback="back_to_date")
    await callback.message.answer(
        f"🕐 Выберите время консультации:\n\n"
        f"{get_date_display(date_str)}",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_to_date")
async def cb_back_to_date(callback: CallbackQuery, state: FSMContext):
    logger.info(f"[BACK] User {callback.from_user.id} went back to date selection")
    specialist_id = (await state.get_data()).get("specialist_id")
    if specialist_id:
        dates = await get_available_dates(specialist_id)
        keyboard = build_date_keyboard(dates, back_callback="back_to_specialist")
        await callback.message.answer(
            "📅 Выберите дату консультации:",
            reply_markup=keyboard,
        )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("time_"))
async def cb_select_time(callback: CallbackQuery, state: FSMContext):
    slot_key = callback.data.split("_", 1)[1]
    data = await state.get_data()
    specialist_id = data.get("specialist_id")
    date_str = data.get("selected_date")

    logger.info(f"[TIME] User {callback.from_user.id} selected slot {slot_key}")

    if not specialist_id or not date_str:
        logger.error(f"[TIME] Missing specialist_id or date for user {callback.from_user.id}")
        await callback.message.answer("Произошла ошибка. Начните заново: /start")
        await state.clear()
        return

    try:
        time_part = slot_key.split("_")[-1]
        consultation_dt = datetime.strptime(f"{date_str} {time_part}", "%Y-%m-%d %H:%M")
    except ValueError:
        logger.error(f"[TIME] Invalid time format: {slot_key}")
        await callback.message.answer("Ошибка при обработке времени. Попробуйте снова.")
        return

    async with AsyncSessionLocal() as db:
        if await has_booking_at(db, specialist_id, consultation_dt):
            logger.warning(f"[TIME] Slot {slot_key} already booked for user {callback.from_user.id}")
            slots = await get_available_slots(db, specialist_id, datetime.strptime(date_str, "%Y-%m-%d"))
            keyboard = build_time_keyboard(slots, back_callback="back_to_date")
            await callback.message.answer(
                "⚠️ Это время уже занято. Пожалуйста, выберите другой слот.",
                reply_markup=keyboard,
            )
            return

        existing = await get_active_reservation(db, slot_key)
        if existing:
            logger.warning(f"[TIME] Slot {slot_key} already reserved by another user")
            await callback.answer("Этот слот уже зарезервирован.")
            return

        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.reservation_timeout_seconds
        )
        reservation = await create_reservation(
            db, slot_key, callback.from_user.id, expires_at,
        )

    logger.info(f"[TIME] Slot {slot_key} reserved by user {callback.from_user.id} (expires in {settings.reservation_timeout_seconds}s)")

    await state.update_data(
        slot_key=slot_key,
        selected_time=time_part,
        consultation_datetime=consultation_dt.isoformat(),
        reservation_id=reservation.id,
    )

    await callback.answer("Слот зарезервирован! Введите ваше имя.")
    await state.set_state(BookingFSM.AWAITING_NAME)
    await callback.message.answer(
        "✏️ Введите ваше имя:\n\n"
        "Это имя будет использовано для записи на консультацию.",
    )
