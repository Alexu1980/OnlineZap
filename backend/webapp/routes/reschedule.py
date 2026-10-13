"""Маршрут для переноса бронирований."""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import func

from webapp.dependencies import get_db_session
from database.models import Booking, Availability
from database.repositories import update_booking_field, get_specialist_by_id

logger = logging.getLogger("reschedule")

router = APIRouter()


@router.post("/bookings/{booking_id}/reschedule")
async def reschedule_booking(
    booking_id: int,
    new_date: str = Query(..., description="Новая дата YYYY-MM-DD"),
    new_time: str = Query(..., description="Новое время HH:MM"),
    user_telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: AsyncSession = Depends(get_db_session)
):
    """Перенос записи на новую дату и время."""
    logger.info(f"RESCHEDULE: User {user_telegram_id} rescheduling booking #{booking_id} to {new_date} {new_time}")
    
    # Проверяем, что запись принадлежит пользователю
    result = await db.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.user_telegram_id == user_telegram_id
        )
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    if booking.status == "Отменена":
        raise HTTPException(status_code=400, detail="Нельзя перенести отменённую запись")
    
    # Проверяем, что время не занято
    existing_check = await db.execute(
        select(Booking).where(
            Booking.specialist_id == booking.specialist_id,
            Booking.consultation_date == new_date,
            Booking.consultation_time == new_time,
            Booking.status.in_(["Подтверждена", "Перенесена"])
        )
    )
    if existing_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Это время уже занято")
    
    # Обновляем запись
    new_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
    new_datetime_utc = datetime(
        new_datetime.year, new_datetime.month, new_datetime.day,
        new_datetime.hour, new_datetime.minute,
        tzinfo=timezone.utc,
    )
    
    await update_booking_field(db, booking_id, "consultation_date", new_date)
    await update_booking_field(db, booking_id, "consultation_time", new_time)
    await update_booking_field(db, booking_id, "consultation_datetime", new_datetime_utc)
    await update_booking_field(db, booking_id, "status", "Перенесена")
    await db.commit()
    
    logger.info(f"RESCHEDULE: Booking #{booking_id} rescheduled from {booking.consultation_date} {booking.consultation_time} to {new_date} {new_time}")
    
    return {
        "success": True,
        "message": f"Консультация перенесена на {new_date} {new_time}",
        "booking_id": booking_id,
        "new_date": new_date,
        "new_time": new_time
    }


@router.get("/bookings/{booking_id}/available-slots")
async def get_available_slots_for_reschedule(
    booking_id: int,
    user_telegram_id: int = Query(..., description="Telegram ID пользователя"),
    days: int = Query(30, ge=1, le=90, description="Количество дней для проверки"),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение доступных слотов для переноса."""
    logger.info(f"RESCHEDULE_SLOTS: User {user_telegram_id} getting slots for booking #{booking_id}")
    
    # Проверяем, что запись принадлежит пользователю
    result = await db.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.user_telegram_id == user_telegram_id
        )
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    if booking.status == "Отменена":
        raise HTTPException(status_code=400, detail="Нельзя перенести отменённую запись")
    
    specialist_id = booking.specialist_id
    
    # Получаем все availability для специалиста
    result = await db.execute(
        select(Availability).where(
            Availability.specialist_id == specialist_id,
            Availability.is_active == True
        )
    )
    availabilities = result.scalars().all()
    
    if not availabilities:
        return {"dates": [], "specialist_id": specialist_id}
    
    # Группируем по дням недели
    availabilities_by_dow = {}
    for avail in availabilities:
        dow = avail.day_of_week
        if dow not in availabilities_by_dow:
            availabilities_by_dow[dow] = []
        availabilities_by_dow[dow].append(avail)
    
    working_days = set(availabilities_by_dow.keys())
    
    # Получаем все бронирования на период
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today + timedelta(days=days)
    
    bookings_result = await db.execute(
        select(Booking).where(
            Booking.specialist_id == specialist_id,
            Booking.consultation_date >= today.strftime("%Y-%m-%d"),
            Booking.consultation_date < end_date.strftime("%Y-%m-%d"),
            Booking.status.in_(["Подтверждена", "Перенесена"])
        )
    )
    all_bookings = bookings_result.scalars().all()
    
    # Группируем по датам
    bookings_by_date = {}
    for b in all_bookings:
        if b.consultation_date not in bookings_by_date:
            bookings_by_date[b.consultation_date] = []
        bookings_by_date[b.consultation_date].append(b)
    
    # Генерируем даты
    dates = []
    for i in range(days):
        date = today + timedelta(days=i)
        day_of_week = date.weekday()
        date_str = date.strftime("%Y-%m-%d")
        
        is_working_day = day_of_week in working_days
        
        if is_working_day:
            day_avail_count = len(availabilities_by_dow.get(day_of_week, []))
            booked_count = len(bookings_by_date.get(date_str, []))
            available_count = max(0, day_avail_count - booked_count)
            
            dates.append({
                "date": date_str,
                "has_slots": available_count > 0,
                "slots_count": available_count
            })
    
    return {"dates": dates}
