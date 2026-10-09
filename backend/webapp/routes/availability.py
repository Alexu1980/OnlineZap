"""Маршрут для получения доступных дат для специалиста."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from webapp.dependencies import get_db_session
from webapp.schemas import AvailabilityResponse
from database.models import Availability, Booking

router = APIRouter()


@router.get("")
async def get_availability(
    specialist_id: int = Query(..., description="ID специалиста"),
    days: int = Query(30, ge=1, le=90, description="Количество дней для проверки"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение доступных дат для специалиста на заданный период.
    
    Возвращает список дат с информацией о наличии слотов.
    """
    # Проверка существования специалиста
    from database.repositories import get_specialist_by_id
    specialist = await get_specialist_by_id(db, specialist_id)
    if not specialist:
        raise HTTPException(status_code=404, detail="Специалист не найден")
    
    # Получение расписания специалиста
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
    
    # Определение рабочих дней (day_of_week из Availability)
    working_days = {avail.day_of_week for avail in availabilities}
    
    # Генерация дат на указанный период
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    dates = []
    
    for i in range(days):
        date = today + timedelta(days=i)
        day_of_week = date.weekday()
        
        # Проверка, является ли день рабочим
        is_working_day = day_of_week in working_days
        
        if is_working_day:
            # Проверка занятых слотов на эту дату
            date_str = date.strftime("%Y-%m-%d")
            booking_result = await db.execute(
                select(Booking)
                .where(
                    Booking.specialist_id == specialist_id,
                    Booking.consultation_date == date_str,
                    Booking.status != "Отменена"
                )
            )
            booked_bookings = booking_result.scalars().all()
            
            # Подсчет доступных слотов
            total_slots = len(availabilities)
            booked_count = len(booked_bookings)
            available_count = max(0, total_slots - booked_count)
            
            dates.append(AvailabilityResponse(
                date=date_str,
                has_slots=available_count > 0,
                slots_count=available_count,
            ).model_dump())
    
    return {"dates": dates}
