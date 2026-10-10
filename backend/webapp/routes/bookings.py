"""Маршрут для создания бронирований."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.dependencies import get_db_session
from webapp.schemas import BookingCreate, BookingResponse
from services.booking_service import BookingService

logger = logging.getLogger("bookings")

router = APIRouter()


@router.post("/bookings", response_model=BookingResponse)
async def create_booking(
    data: BookingCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Создание бронирования из MiniApp."""
    try:
        # Для MVP используем user_id=0 (без аутентификации)
        result = await BookingService.create_booking(
            db=db,
            user_id=0,  # MVP: без аутентификации
            telegram_username=data.name,  # Используем имя как username
            specialist_id=data.specialist_id,
            date_str=data.date,
            time_str=data.time,
            slot_key=f"{data.specialist_id}_{data.date}_{data.time}",
            name=data.name,
            phone=data.phone,
            additional_info=data.additional_info,
        )
        
        logger.info(f"Booking created: {result['id']} for specialist {data.specialist_id}")
        
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
    data: BookingCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Создание бронирования (с trailing slash)."""
    try:
        result = await BookingService.create_booking(
            db=db,
            user_id=0,
            telegram_username=data.name,
            specialist_id=data.specialist_id,
            date_str=data.date,
            time_str=data.time,
            slot_key=f"{data.specialist_id}_{data.date}_{data.time}",
            name=data.name,
            phone=data.phone,
            additional_info=data.additional_info,
        )
        
        logger.info(f"Booking created: {result['id']} for specialist {data.specialist_id}")
        
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
