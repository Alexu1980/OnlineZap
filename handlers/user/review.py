import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

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
    create_booking as db_create_booking,
)
from database.models import Booking
from services.sheet_service import SheetService
from services.scheduler_service import SchedulerService
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "confirm_booking")
async def cb_confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    telegram_username = callback.from_user.username
    
    specialist_id = data.get("specialist_id")
    # Поддерживаем как обычную запись (selected_date), так и перенос (reschedule_date)
    date_str = data.get("selected_date") or data.get("reschedule_date")
    time_str = data.get("selected_time") or data.get("reschedule_time")
    slot_key = data.get("slot_key")
    name = data.get("user_name")
    phone = data.get("user_phone")
    additional_info = data.get("additional_info")

    logger.info(f"[CONFIRM] User {user_id} confirmed booking")
    logger.info(f"[CONFIRM] specialist_id={specialist_id}, date={date_str}, time={time_str}")
    logger.info(f"[CONFIRM] name={name}, phone={phone}")
    logger.info(f"[CONFIRM] Full state data: {data}")

    if not date_str or not time_str:
        logger.error(f"[CONFIRM] Missing date ({date_str}) or time ({time_str}) in state")
        await callback.message.answer(
            "❌ При создании записи произошла ошибка: отсутствуют дата или время.\n"
            "Пожалуйста, начните запись заново: /start"
        )
        await state.clear()
        return

    try:
        async with AsyncSessionLocal() as db:
            # Создаём запись напрямую
            logger.info(f"[CONFIRM] Creating booking record...")
            
            consultation_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            consultation_utc = datetime(
                consultation_dt.year, consultation_dt.month, consultation_dt.day,
                consultation_dt.hour, consultation_dt.minute,
                tzinfo=timezone.utc,
            )
            
            # Получаем имя специалиста
            from database.repositories import get_specialist_by_id
            specialist = await get_specialist_by_id(db, specialist_id)
            if not specialist:
                raise Exception("Специалист не найден")
            
            # Проверяем, есть ли уже запись на это время к другому специалисту
            conflict_booking = await db.execute(
                select(Booking).where(
                    Booking.user_telegram_id == user_id,
                    Booking.consultation_date == date_str,
                    Booking.consultation_time == time_str,
                    Booking.specialist_id != specialist_id,
                    Booking.status == "Подтверждена",
                )
            )
            conflicting = conflict_booking.scalars().first()
            
            if conflicting:
                logger.warning(f"[CONFIRM] Time conflict for user {user_id}: already booked with {conflicting.specialist_name}")
                await callback.message.answer(
                    f"⚠️ У вас уже есть запись на это время:\n\n"
                    f"👨‍⚕️ {conflicting.specialist_name}\n"
                    f"📅 {date_str} в {time_str}\n\n"
                    f"Вы не можете быть у двух специалистов одновременно.\n\n"
                    f"Пожалуйста, выберите другое время или отмените текущую запись.",
                )
                await state.clear()
                return
            
            # Создаём booking
            booking = Booking(
                user_telegram_id=user_id,
                user_username=telegram_username or "",
                user_name=name,
                user_phone=phone,
                specialist_id=specialist_id,
                specialist_name=specialist.name,
                consultation_date=date_str,
                consultation_time=time_str,
                consultation_datetime=consultation_utc,
                additional_info=additional_info,
                status="Подтверждена",
            )
            
            db.add(booking)
            logger.info(f"[CONFIRM] Booking added to session, flushing...")
            await db.flush()  # Получаем booking.id
            
            booking_id = booking.id
            logger.info(f"[CONFIRM] Booking #{booking_id} flushed, committing...")
            await db.commit()
            logger.info(f"[CONFIRM] Booking #{booking_id} COMMITTED to database!")
            
            # Записываем в Google Sheets
            try:
                sheet_service = SheetService()
                row_number = await sheet_service.append_booking({
                    "id": booking_id,
                    "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                    "user_name": name,
                    "user_phone": phone,
                    "user_username": telegram_username or "",
                    "user_telegram_id": user_id,
                    "specialist_name": specialist.name,
                    "consultation_date": date_str,
                    "consultation_time": time_str,
                    "status": "Подтверждена",
                    "manager_comment": additional_info or "",
                })
                
                # Сохраняем номер строки в booking
                if row_number and row_number > 0:
                    booking.google_sheet_row = row_number
                    await db.commit()
                    logger.info(f"[CONFIRM] Booking #{booking_id} saved to Google Sheets row {row_number}")
                else:
                    logger.warning(f"[CONFIRM] Google Sheets returned invalid row number: {row_number}")
            except Exception as e:
                logger.warning(f"[CONFIRM] Google Sheets error (non-fatal): {e}")
            
            # Удаляем резерв слота
            await delete_reservation_by_slot_key(db, slot_key)
            await db.commit()
            logger.info(f"[CONFIRM] Reservation deleted for slot {slot_key}")
            
            # Настраиваем напоминания
            scheduler = SchedulerService.get_instance()
            if scheduler:
                scheduler.schedule_reminders(booking)
                logger.info(f"[CONFIRM] Reminders scheduled for booking #{booking_id}")
            
            logger.info(f"[CONFIRM] Booking #{booking_id} SUCCESSFULLY created!")

        await state.clear()

        confirm_msg = (
            f"✅ Ваша запись подтверждена!\n\n"
            f"👨‍⚕️ Специалист: {specialist.name}\n"
            f"📅 Дата: {get_datetime_display(date_str, time_str)}\n"
            f"🕐 Время: {time_str}\n\n"
            f"Мы отправим вам напоминание за 24 часа до консультации.\n\n"
            f"Для управления записью используйте кнопки ниже:"
        )

        from keyboards.inline import build_booking_action_keyboard, InlineKeyboardButton, InlineKeyboardBuilder
        
        # Создаём клавиатуру с кнопками
        kb = InlineKeyboardBuilder()
        
        # Кнопки управления записью
        kb.button(text="🔄 Перенести", callback_data=f"reschedule_{booking_id}")
        kb.button(text="❌ Отменить", callback_data=f"cancel_{booking_id}")
        
        # Кнопка личного кабинета
        kb.button(text="📋 Личный кабинет", callback_data="personal_cabinet")
        
        kb.adjust(2, 1)  # 2 кнопки в ряд, затем 1
        
        await callback.message.answer(confirm_msg, reply_markup=kb.as_markup())
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
