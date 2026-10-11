"""Маршрут для получения данных пользователя из последней записи."""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from webapp.dependencies import get_db_session
from database.models import Booking

logger = logging.getLogger("user_data")

router = APIRouter()


@router.get("/user/data")
async def get_user_data(
    user_telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение имени и телефона из последней записи пользователя."""
    logger.info(f"get_user_data: user_telegram_id={user_telegram_id}")
    
    # Ищем последнюю запись пользователя (любую, включая отменённые)
    result = await db.execute(
        select(Booking)
        .where(Booking.user_telegram_id == user_telegram_id)
        .order_by(Booking.created_at.desc())
        .limit(1)
    )
    last_booking = result.scalar_one_or_none()
    
    if not last_booking:
        logger.info(f"get_user_data: No bookings found for user {user_telegram_id}")
        return {
            "name": None,
            "phone": None,
            "found": False
        }
    
    logger.info(f"get_user_data: Found booking #{last_booking.id}, name={last_booking.user_name}, phone={last_booking.user_phone}")
    
    return {
        "name": last_booking.user_name,
        "phone": last_booking.user_phone,
        "found": True
    }
