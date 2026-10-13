"""Маршрут для создания бронирований."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from webapp.dependencies import get_db_session
from webapp.schemas import BookingCreate, BookingResponse
from services.booking_service import BookingService
from database.models import Booking
from database.repositories import update_booking_status

logger = logging.getLogger("bookings")

router = APIRouter()


@router.post("/bookings", response_model=BookingResponse)
async def create_booking(
    request: Request,
    data: BookingCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Создание бронирования из MiniApp."""
    try:
        # Получаем user_id из headers (Telegram WebApp)
        telegram_user_id = request.headers.get('X-Telegram-User-Id', '0')
        telegram_username = request.headers.get('X-Telegram-Username', data.name)
        
        logger.info(f"Booking request: user_id={telegram_user_id}, username={telegram_username}")
        
        result = await BookingService.create_booking(
            db=db,
            user_id=int(telegram_user_id),  # Используем реальный Telegram ID
            telegram_username=telegram_username,
            specialist_id=data.specialist_id,
            date_str=data.date,
            time_str=data.time,
            slot_key=f"{data.specialist_id}_{data.date}_{data.time}",
            name=data.name,
            phone=data.phone,
            additional_info=data.additional_info,
        )
        
        logger.info(f"Booking created: {result['id']} for user {telegram_user_id}")
        
        return BookingResponse(
            id=result['id'],
            specialist_name=result['specialist_name'],
            consultation_date=result['consultation_date'],
            consultation_time=result['consultation_time'],
            status=result['status'],
        )
        
    except Exception as e:
        logger.error(f"Error creating booking: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bookings/", response_model=BookingResponse)
async def create_booking_trailing(
    request: Request,
    data: BookingCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Создание бронирования (с trailing slash)."""
    try:
        telegram_user_id = request.headers.get('X-Telegram-User-Id', '0')
        telegram_username = request.headers.get('X-Telegram-Username', data.name)
        
        result = await BookingService.create_booking(
            db=db,
            user_id=int(telegram_user_id),
            telegram_username=telegram_username,
            specialist_id=data.specialist_id,
            date_str=data.date,
            time_str=data.time,
            slot_key=f"{data.specialist_id}_{data.date}_{data.time}",
            name=data.name,
            phone=data.phone,
            additional_info=data.additional_info,
        )
        
        logger.info(f"Booking created: {result['id']} for user {telegram_user_id}")
        
        return BookingResponse(
            id=result['id'],
            specialist_name=result['specialist_name'],
            consultation_date=result['consultation_date'],
            consultation_time=result['consultation_time'],
            status=result['status'],
        )
        
    except Exception as e:
        logger.error(f"Error creating booking: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


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
