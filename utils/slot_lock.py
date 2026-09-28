from datetime import datetime, timedelta, timezone

from database.repositories import (
    get_active_reservation,
    delete_reservation_by_slot_key,
    has_booking_at,
    create_booking,
    get_available_slots,
)
from exceptions.booking import SlotAlreadyReserved, SlotAlreadyBooked


class SlotLock:
    """Механизм блокировки слотов для защиты от двойной записи."""

    @staticmethod
    async def is_slot_available(db, specialist_id: int, slot_key: str, date_str: str, time_str: str) -> bool:
        """Проверка доступности слота."""
        # Check existing bookings
        try:
            consultation_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            return False

        if await has_booking_at(db, specialist_id, consultation_dt):
            return False

        # Check active reservations
        reservation = await get_active_reservation(db, slot_key)
        if reservation:
            return False

        return True

    @staticmethod
    async def reserve_slot(db, slot_key: str, user_id: int, specialist_id: int,
                           date_str: str, time_str: str) -> dict:
        """
        Резервирование слота.
        Возвращает dict с данными резерва или выбрасывает исключение.
        """
        from database.repositories import create_reservation
        from config.settings import settings

        # Double-check availability
        if not await SlotLock.is_slot_available(db, specialist_id, slot_key, date_str, time_str):
            raise SlotAlreadyReserved("Этот слот уже зарезервирован или занят.")

        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.reservation_timeout_seconds
        )

        reservation = await create_reservation(db, slot_key, user_id, expires_at)

        return {
            "reservation_id": reservation.id,
            "slot_key": slot_key,
            "expires_at": expires_at,
        }

    @staticmethod
    async def release_reservation(db, slot_key: str) -> None:
        """Освобождение резерва слота."""
        await delete_reservation_by_slot_key(db, slot_key)

    @staticmethod
    async def cleanup_expired(db) -> int:
        """Удаление истёкших резервов."""
        from database.repositories import cleanup_expired_reservations
        return await cleanup_expired_reservations(db)

    @staticmethod
    def format_reservation_message(reservation: dict) -> str:
        """Форматирование сообщения о резерве."""
        timeout_seconds = reservation.get("expires_at", 300)
        from config.settings import settings
        timeout = settings.reservation_timeout_seconds
        minutes = timeout // 60
        seconds_left = timeout
        return (
            f"⏳ Слот зарезервирован!\n\n"
            f"У вас есть {minutes} минут на завершение записи.\n"
            f"Пожалуйста, заполните контактные данные."
        )
