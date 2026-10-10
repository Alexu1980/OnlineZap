"""Маршрут для создания бронирований."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.dependencies import get_db_session
from webapp.schemas import BookingCreate, BookingResponse
from services.booking_service import BookingService

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
