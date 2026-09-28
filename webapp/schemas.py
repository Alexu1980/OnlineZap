"""Pydantic модели для API."""
from pydantic import BaseModel, Field
from typing import Optional


class SpecialistResponse(BaseModel):
    """Ответ с данными специалиста."""
    id: int
    name: str
    specialization: str


class SlotResponse(BaseModel):
    """Ответ с данными слота."""
    time: str
    slot_key: str
    available: bool = True


class AvailabilityResponse(BaseModel):
    """Ответ с данными доступности."""
    date: str
    has_slots: bool
    slots_count: int = 0


class BookingCreate(BaseModel):
    """Модель для создания бронирования."""
    specialist_id: int = Field(..., description="ID специалиста")
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")
    time: str = Field(..., description="Время в формате HH:MM")
    name: str = Field(..., min_length=1, max_length=100, description="Имя пользователя")
    phone: str = Field(..., min_length=1, max_length=20, description="Телефон пользователя")
    additional_info: Optional[str] = Field(None, description="Дополнительная информация")


class BookingResponse(BaseModel):
    """Ответ с данными созданного бронирования."""
    id: int
    specialist_name: str
    consultation_date: str
    consultation_time: str
    status: str
