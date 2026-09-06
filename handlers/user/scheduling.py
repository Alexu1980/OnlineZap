from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery
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

router = Router()


async def get_available_dates(specialist_id: int) -> list[str]:
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
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await callback.answer("Неверный формат даты.")
        return

    data = await state.get_data()
    specialist_id = data.get("specialist_id")

    if not specialist_id:
        await callback.message.answer("Произошла ошибка. Начните заново: /start")
        await state.clear()
        return

    async with AsyncSessionLocal() as db:
        slots = await get_available_slots(db, specialist_id, selected_date)

    if not slots:
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

    if not specialist_id or not date_str:
        await callback.message.answer("Произошла ошибка. Начните заново: /start")
        await state.clear()
        return

    # Parse slot key: {specialist_id}_{date}_{time}
    try:
        time_part = slot_key.split("_")[-1]
        consultation_dt = datetime.strptime(f"{date_str} {time_part}", "%Y-%m-%d %H:%M")
    except ValueError:
        await callback.message.answer("Ошибка при обработке времени. Попробуйте снова.")
        return

    async with AsyncSessionLocal() as db:
        # Check if already booked
        if await has_booking_at(db, specialist_id, consultation_dt):
            slots = await get_available_slots(db, specialist_id, datetime.strptime(date_str, "%Y-%m-%d"))
            keyboard = build_time_keyboard(slots, back_callback="back_to_date")
            await callback.message.answer(
                "⚠️ Это время уже занято. Пожалуйста, выберите другой слот.",
                reply_markup=keyboard,
            )
            return

        # Check if reserved by someone else
        existing = await get_active_reservation(db, slot_key)
        if existing:
            await callback.answer("Этот слот уже зарезервирован.")
            return

        # Reserve the slot
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.reservation_timeout_seconds
        )
        reservation = await create_reservation(
            db, slot_key, callback.from_user.id, expires_at,
        )

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
