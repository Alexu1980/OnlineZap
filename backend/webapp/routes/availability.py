"""Маршрут для получения доступных дат для специалиста."""
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from webapp.dependencies import get_db_session
from webapp.schemas import AvailabilityResponse
from database.models import Availability, Booking

logger = logging.getLogger("availability")

router = APIRouter()


@router.get("/availability")
async def get_availability_list(
    specialist_id: int = Query(..., description="ID специалиста"),
    days: int = Query(30, ge=1, le=90, description="Количество дней для проверки"),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение доступных дат для специалиста на заданный период."""
    logger.info(f"get_availability_list: specialist_id={specialist_id}, days={days}")
    return await _get_availability_data(specialist_id, days, db)


@router.get("/availability/")
async def get_availability_list_trailing(
    specialist_id: int = Query(..., description="ID специалиста"),
    days: int = Query(30, ge=1, le=90, description="Количество дней для проверки"),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение доступных дат для специалиста (с trailing slash)."""
    logger.info(f"get_availability_list_trailing: specialist_id={specialist_id}, days={days}")
    return await _get_availability_data(specialist_id, days, db)


async def _get_availability_data(specialist_id: int, days: int, db: AsyncSession):
    """Общие данные для получения расписания."""
    # Проверка существования специалиста
    from database.repositories import get_specialist_by_id
    specialist = await get_specialist_by_id(db, specialist_id)
    if not specialist:
        logger.warning(f"Specialist {specialist_id} not found")
        raise HTTPException(status_code=404, detail="Специалист не найден")
    
    # Получение расписания специалиста (все доступные слоты)
    result = await db.execute(
        select(Availability)
        .where(
            Availability.specialist_id == specialist_id,
            Availability.is_active == True  # noqa: E712
        )
    )
    availabilities = result.scalars().all()
    
    if not availabilities:
        return {"dates": []}
    
    # Общее количество слотов в день
    total_slots_per_day = len(availabilities)
    
    # Определение рабочих дней (day_of_week из Availability)
    working_days = {avail.day_of_week for avail in availabilities}
    
    # Получаем ВСЕ бронирования на период
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today + timedelta(days=days)
    
    bookings_result = await db.execute(
        select(Booking)
        .where(
            Booking.specialist_id == specialist_id,
            Booking.consultation_date >= today.strftime("%Y-%m-%d"),
            Booking.consultation_date < end_date.strftime("%Y-%m-%d"),
            Booking.status != "Отменена"
        )
    )
    all_bookings = bookings_result.scalars().all()
    
    # Группируем бронирования по датам
    bookings_by_date = {}
    for booking in all_bookings:
        date_str = booking.consultation_date
        if date_str not in bookings_by_date:
            bookings_by_date[date_str] = []
        bookings_by_date[date_str].append(booking)
    
    # Генерация дат на указанный период
    dates = []
    
    for i in range(days):
        date = today + timedelta(days=i)
        day_of_week = date.weekday()
        date_str = date.strftime("%Y-%m-%d")
        
        # Проверка, является ли день рабочим
        is_working_day = day_of_week in working_days
        
        if is_working_day:
            # Считаем занятые слоты на эту дату
            booked_count = len(bookings_by_date.get(date_str, []))
            
            # Доступные слоты = общее количество - занятые
            available_count = max(0, total_slots_per_day - booked_count)
            
            has_slots = available_count > 0
            
            logger.info(f"Date {date_str}: total={total_slots_per_day}, booked={booked_count}, available={available_count}")
            
            dates.append(AvailabilityResponse(
                date=date_str,
                has_slots=has_slots,
                slots_count=available_count,
            ).model_dump())
    
    return {"dates": dates}
