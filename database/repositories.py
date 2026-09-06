from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    ConsentLog, Specialist, Availability, SlotReservation, Booking,
)


# ==================== Consent ====================

async def save_consent(db: AsyncSession, user_id: int) -> None:
    consent = ConsentLog(user_telegram_id=user_id)
    db.add(consent)
    await db.commit()


async def has_consent(db: AsyncSession, user_id: int) -> bool:
    result = await db.execute(
        select(ConsentLog).where(ConsentLog.user_telegram_id == user_id)
    )
    return result.scalar_one_or_none() is not None


# ==================== Specialists ====================

async def get_active_specialists(db: AsyncSession) -> list[Specialist]:
    result = await db.execute(
        select(Specialist).where(Specialist.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def get_specialist_by_id(db: AsyncSession, specialist_id: int) -> Specialist | None:
    result = await db.execute(
        select(Specialist).where(Specialist.id == specialist_id, Specialist.is_active == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


# ==================== Availability ====================

async def get_availability_for_specialist(
    db: AsyncSession, specialist_id: int, day_of_week: int
) -> list[Availability]:
    result = await db.execute(
        select(Availability).where(
            Availability.specialist_id == specialist_id,
            Availability.day_of_week == day_of_week,
            Availability.is_active == True,  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def get_all_availability(db: AsyncSession) -> list[Availability]:
    result = await db.execute(
        select(Availability).where(Availability.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def add_default_availability(db: AsyncSession) -> None:
    """Добавление расписания по умолчанию для всех специалистов (Пн-Пт, 09:00-18:00)."""
    specialists = await get_active_specialists(db)
    if not specialists:
        return

    existing = await get_all_availability(db)
    if existing:
        return

    days = list(range(5))  # Пн-Пт
    times = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]

    for spec in specialists:
        for dow in days:
            for start in times:
                hour = int(start.split(":")[0])
                end_hour = hour + 1
                end = f"{end_hour:02d}:00"
                avail = Availability(
                    specialist_id=spec.id,
                    day_of_week=dow,
                    start_time=start,
                    end_time=end,
                )
                db.add(avail)
    await db.commit()


# ==================== Slot Reservations ====================

async def create_reservation(
    db: AsyncSession, slot_key: str, user_id: int, expires_at: datetime
) -> SlotReservation:
    reservation = SlotReservation(
        slot_key=slot_key,
        user_telegram_id=user_id,
        expires_at=expires_at,
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return reservation


async def get_active_reservation(db: AsyncSession, slot_key: str) -> SlotReservation | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(SlotReservation).where(
            SlotReservation.slot_key == slot_key,
            SlotReservation.expires_at > now,
        )
    )
    return result.scalar_one_or_none()


async def delete_reservation(db: AsyncSession, reservation_id: int) -> None:
    await db.execute(
        delete(SlotReservation).where(SlotReservation.id == reservation_id)
    )
    await db.commit()


async def delete_reservation_by_slot_key(db: AsyncSession, slot_key: str) -> None:
    await db.execute(
        delete(SlotReservation).where(SlotReservation.slot_key == slot_key)
    )
    await db.commit()


async def cleanup_expired_reservations(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        delete(SlotReservation).where(SlotReservation.expires_at <= now)
    )
    await db.commit()
    return result.rowcount


# ==================== Bookings ====================

async def has_booking_at(
    db: AsyncSession, specialist_id: int, consultation_datetime: datetime
) -> bool:
    date_str = consultation_datetime.strftime("%Y-%m-%d")
    time_str = consultation_datetime.strftime("%H:%M")
    result = await db.execute(
        select(Booking).where(
            Booking.specialist_id == specialist_id,
            Booking.consultation_date == date_str,
            Booking.consultation_time == time_str,
            Booking.status != "Отменена",
        )
    )
    return result.scalar_one_or_none() is not None


async def create_booking(db: AsyncSession, **kwargs) -> Booking:
    booking = Booking(**kwargs)
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


async def get_booking_by_id(db: AsyncSession, booking_id: int) -> Booking | None:
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    return result.scalar_one_or_none()


async def get_bookings_by_user(db: AsyncSession, user_id: int) -> list[Booking]:
    result = await db.execute(
        select(Booking).where(
            Booking.user_telegram_id == user_id,
            Booking.status == "Подтверждена",
        ).order_by(Booking.consultation_datetime.asc())
    )
    return list(result.scalars().all())


async def get_active_bookings(db: AsyncSession) -> list[Booking]:
    result = await db.execute(
        select(Booking).where(
            Booking.status == "Подтверждена",
            Booking.consultation_datetime > datetime.now(timezone.utc),
        ).order_by(Booking.consultation_datetime.asc())
    )
    return list(result.scalars().all())


async def update_booking_status(db: AsyncSession, booking_id: int, status: str) -> None:
    await db.execute(
        update(Booking)
        .where(Booking.id == booking_id)
        .values(status=status, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def update_booking_field(db: AsyncSession, booking_id: int, field: str, value) -> None:
    await db.execute(
        update(Booking)
        .where(Booking.id == booking_id)
        .values(**{field: value}, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def update_manager_comment(db: AsyncSession, booking_id: int, comment: str) -> None:
    await db.execute(
        update(Booking)
        .where(Booking.id == booking_id)
        .values(manager_comment=comment, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def get_all_bookings(db: AsyncSession, limit: int = 50) -> list[Booking]:
    result = await db.execute(
        select(Booking)
        .order_by(Booking.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_bookings_by_status(db: AsyncSession, status: str) -> list[Booking]:
    result = await db.execute(
        select(Booking).where(Booking.status == status).order_by(Booking.consultation_datetime.desc())
    )
    return list(result.scalars().all())


async def get_available_slots(
    db: AsyncSession,
    specialist_id: int,
    target_date: datetime,
) -> list[dict]:
    """Возвращает доступные слоты для выбранной даты и специалиста."""
    day_of_week = target_date.weekday()  # 0=Mon...6=Sun

    availabilities = await get_availability_for_specialist(db, specialist_id, day_of_week)
    if not availabilities:
        return []

    date_str = target_date.strftime("%Y-%m-%d")
    existing = await db.execute(
        select(Booking).where(
            Booking.specialist_id == specialist_id,
            Booking.consultation_date == date_str,
            Booking.status != "Отменена",
        )
    )
    booked_times = {b.consultation_time for b in existing.scalars().all()}

    # Check reservations
    reservations = await db.execute(
        select(SlotReservation).where(SlotReservation.expires_at > datetime.now(timezone.utc))
    )
    reserved_keys = {r.slot_key for r in reservations.scalars().all()}

    slots = []
    for avail in availabilities:
        current_time = avail.start_time
        end_time = avail.end_time
        while current_time < end_time:
            slot_key = f"{specialist_id}_{date_str}_{current_time}"
            if current_time not in booked_times and slot_key not in reserved_keys:
                slots.append({"time": current_time, "slot_key": slot_key})
            # Move forward by slot duration
            hour, _ = map(int, current_time.split(":"))
            from config.settings import settings
            next_hour = hour + settings.slot_duration_minutes // 60
            current_time = f"{next_hour:02d}:00"

    return slots


async def get_bookings_for_date_range(
    db: AsyncSession,
    specialist_id: int,
    start_date: str,
    end_date: str,
) -> list[Booking]:
    result = await db.execute(
        select(Booking).where(
            Booking.specialist_id == specialist_id,
            Booking.consultation_date >= start_date,
            Booking.consultation_date <= end_date,
            Booking.status != "Отменена",
        ).order_by(Booking.consultation_date, Booking.consultation_time)
    )
    return list(result.scalars().all())
