"""Маршрут для получения записей пользователя."""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from webapp.dependencies import get_db_session
from database.models import Booking

logger = logging.getLogger("user_bookings")

router = APIRouter()


@router.get("/user/bookings")
async def get_user_bookings(
    user_telegram_id: int = Query(..., description="Telegram ID пользователя"),
    show_history: bool = Query(False, description="Показывать историю записей"),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение всех записей пользователя."""
    logger.info(f"get_user_bookings: user_telegram_id={user_telegram_id}, show_history={show_history}")
    
    now = datetime.now(timezone.utc)
    
    # Получаем все записи пользователя
    result = await db.execute(
        select(Booking)
        .where(Booking.user_telegram_id == user_telegram_id)
        .order_by(Booking.created_at.desc())
    )
    bookings = result.scalars().all()
    
    if not bookings:
        logger.info(f"get_user_bookings: No bookings found for user {user_telegram_id}")
        return {
            "active_bookings": [],
            "past_bookings": [],
            "has_history": False
        }
    
    # Разделяем на активные и прошлые
    active_bookings = []
    past_bookings = []
    
    for booking in bookings:
        consult_dt = booking.consultation_datetime
        if consult_dt and consult_dt.tzinfo is None:
            consult_dt = consult_dt.replace(tzinfo=timezone.utc)
        
        if consult_dt and consult_dt > now and booking.status != "Отменена":
            active_bookings.append(booking)
        else:
            past_bookings.append(booking)
    
    # Форматируем ответы
    active_response = []
    for b in active_bookings[:5]:  # Максимум 5 активных
        active_response.append({
            "id": b.id,
            "specialist_name": b.specialist_name,
            "consultation_date": b.consultation_date,
            "consultation_time": b.consultation_time,
            "status": b.status,
            "created_at": b.created_at.strftime("%d.%m.%Y %H:%M") if b.created_at else None,
        })
    
    past_response = []
    if show_history or len(past_bookings) > 0:
        for b in past_bookings[:10]:  # Максимум 10 прошлых
            past_response.append({
                "id": b.id,
                "specialist_name": b.specialist_name,
                "consultation_date": b.consultation_date,
                "consultation_time": b.consultation_time,
                "status": b.status,
                "created_at": b.created_at.strftime("%d.%m.%Y %H:%M") if b.created_at else None,
            })
    
    logger.info(f"get_user_bookings: Found {len(active_bookings)} active, {len(past_bookings)} past bookings")
    
    return {
        "active_bookings": active_response,
        "past_bookings": past_response,
        "has_history": len(past_bookings) > 0
    }
