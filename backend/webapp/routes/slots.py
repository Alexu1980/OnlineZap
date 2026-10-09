"""Маршрут для получения временных слотов."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.dependencies import get_db_session
from webapp.schemas import SlotResponse
from database.repositories import get_available_slots

router = APIRouter()


@router.get("")
async def get_slots(
    specialist_id: int = Query(..., description="ID специалиста"),
    date: str = Query(..., description="Дата в формате YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получение доступных временных слотов для специалиста и даты.
    
    Возвращает список слотов с временем и флагом доступности.
    """
    # Проверка формата даты
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")
    
    # Получение доступных слотов
    slots = await get_available_slots(db, specialist_id, target_date)
    
    return {
        "slots": [
            SlotResponse(
                time=slot["time"],
                slot_key=slot["slot_key"],
                available=True
            ).model_dump()
            for slot in slots
        ]
    }
