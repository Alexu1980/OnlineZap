"""Маршрут для создания бронирований."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.auth import verify_telegram_init_data
from webapp.dependencies import get_db_session
from webapp.schemas import BookingCreate, BookingResponse
from services.booking_service import BookingService

router = APIRouter()


@router.post("", response_model=BookingResponse)
async def create_booking(
    data: BookingCreate,
    init_data: str = None,  # Telegram WebApp init data
    user_data: dict = Depends(lambda: verify_telegram_init_data(init_data) if init_data else {}),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Создание бронирования из MiniApp.
    
    Требует аутентификацию через Telegram WebApp init data.
    """
    try:
        # Получение username из Telegram
        telegram_username = user_data.get('username') or user_data.get('link')
        
        # Создание бронирования
        result = await BookingService.create_booking(
            db=db,
            user_id=int(user_data['id']),
            telegram_username=telegram_username,
            specialist_id=data.specialist_id,
            date_str=data.date,
            time_str=data.time,
            slot_key=f"{data.specialist_id}_{data.date}_{data.time}",
            name=data.name,
            phone=data.phone,
            additional_info=data.additional_info,
        )
        
        return BookingResponse(
            id=result['id'],
            specialist_name=result['specialist_name'],
            consultation_date=result['consultation_date'],
            consultation_time=result['consultation_time'],
            status=result['status'],
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
