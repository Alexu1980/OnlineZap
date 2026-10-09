from datetime import datetime, timezone
from sqlalchemy import (
    Integer, String, Boolean, BigInteger, DateTime, Text,
    UniqueConstraint, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base


class Specialist(Base):
    __tablename__ = "specialists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    specialization: Mapped[str] = mapped_column(String(200), default="Общий психолог")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    availability = relationship("Availability", back_populates="specialist")
    bookings = relationship("Booking", back_populates="specialist")


class Availability(Base):
    __tablename__ = "availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    specialist_id: Mapped[int] = mapped_column(Integer, ForeignKey("specialists.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon...6=Sun
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    specialist = relationship("Specialist", back_populates="availability")


class ConsentLog(Base):
    __tablename__ = "consent_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    consent_version: Mapped[str] = mapped_column(String(10), default="1.0")


class SlotReservation(Base):
    __tablename__ = "slot_reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_username: Mapped[str | None] = mapped_column(String(50), default=None)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    specialist_id: Mapped[int] = mapped_column(Integer, ForeignKey("specialists.id"), nullable=False)
    specialist_name: Mapped[str] = mapped_column(String(100), nullable=False)
    consultation_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    consultation_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    consultation_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    additional_info: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="Подтверждена")
    manager_comment: Mapped[str | None] = mapped_column(Text, default=None)
    reminder_24h_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_2h_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    google_sheet_row: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    specialist = relationship("Specialist", back_populates="bookings")
