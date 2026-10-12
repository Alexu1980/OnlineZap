"""Маршрут для управления записями (отмена, перенос)."""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from webapp.dependencies import get_db_session
from database.models import Booking
from database.repositories import update_booking_status

logger = logging.getLogger("booking_management")

router = APIRouter()


@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    user_telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: AsyncSession = Depends(get_db_session)
):
    """Отмена записи пользователя."""
    logger.info(f"CANCEL: User {user_telegram_id} cancelling booking #{booking_id}")
    
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
        raise HTTPException(status_code=400, detail="Запись уже отменена")
    
    # Отменяем запись
    await update_booking_status(db, booking_id, "Отменена")
    await db.commit()
    
    logger.info(f"CANCEL: Booking #{booking_id} cancelled by user {user_telegram_id}")
    
    return {
        "success": True,
        "message": f"Запись #{booking_id} отменена"
    }


@router.get("/bookings/{booking_id}/available-slots")
async def get_available_slots_for_reschedule(
    booking_id: int,
    user_telegram_id: int = Query(..., description="Telegram ID пользователя"),
    days: int = Query(30, ge=1, le=90, description="Количество дней для проверки"),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение доступных слотов для переноса."""
    logger.info(f"RESCHEDULE: User {user_telegram_id} getting slots for booking #{booking_id}")
    
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
    
    # Получаем specialist
    specialist_id = booking.specialist_id
    
    # Получаем все availability для специалиста
    from database.models import Availability
    result = await db.execute(
        select(Availability).where(
            Availability.specialist_id == specialist_id,
            Availability.is_active == True
        )
    )
    availabilities = result.scalars().all()
    
    if not availabilities:
        return {"dates": []}
    
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
    end_date = today + __import__('datetime').timedelta(days=days)
    
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
        date = today + __import__('datetime').timedelta(days=i)
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
