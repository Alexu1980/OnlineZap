"""Маршрут для получения списка специалистов."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from webapp.dependencies import get_db_session
from webapp.schemas import SpecialistResponse
from database.models import Specialist

router = APIRouter()


@router.get("")
async def get_specialists(
    db: AsyncSession = Depends(get_db_session)
):
    """Получение списка активных специалистов."""
    result = await db.execute(
        select(Specialist)
        .where(Specialist.is_active == True)  # noqa: E712
    )
    specialists = result.scalars().all()
    
    return {
        "specialists": [
            SpecialistResponse(
                id=spec.id,
                name=spec.name,
                specialization=spec.specialization,
            ).model_dump()
            for spec in specialists
        ]
    }


@router.get("/{specialist_id}")
async def get_specialist(
    specialist_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """Получение данных конкретного специалиста."""
    result = await db.execute(
        select(Specialist)
        .where(
            Specialist.id == specialist_id,
            Specialist.is_active == True  # noqa: E712
        )
    )
    specialist = result.scalar_one_or_none()
    
    if not specialist:
        raise HTTPException(status_code=404, detail="Специалист не найден")
    
    return SpecialistResponse(
        id=specialist.id,
        name=specialist.name,
        specialization=specialist.specialization,
    ).model_dump()
