import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import (
    create_booking,
    delete_reservation_by_slot_key,
    get_booking_by_id,
    update_booking_status,
    update_booking_field,
    get_bookings_by_user,
    get_active_bookings,
    get_available_slots,
    get_specialist_by_id,
    has_booking_at,
)
from exceptions.booking import (
    SlotAlreadyReserved,
    SlotAlreadyBooked,
    BookingNotFound,
    BookingAlreadyCancelled,
    BookingAlreadyCompleted,
)
from services.sheet_service import SheetService
from services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)


class BookingService:
    """Сервис для управления бронированиями."""

    @staticmethod
    async def create_booking(
        db: AsyncSession,
        user_id: int,
        telegram_username: str | None,
        specialist_id: int,
        date_str: str,
        time_str: str,
        slot_key: str,
        name: str,
        phone: str,
        additional_info: str | None = None,
    ) -> dict:
        logger.info(f"[BOOKING_CREATE] Creating booking: user={user_id}, spec={specialist_id}, date={date_str}, time={time_str}")

        specialist = await get_specialist_by_id(db, specialist_id)
        if not specialist:
            logger.error(f"[BOOKING_CREATE] Specialist {specialist_id} not found")
            raise BookingNotFound("Специалист не найден.")

        consultation_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        consultation_utc = datetime(
            consultation_dt.year, consultation_dt.month, consultation_dt.day,
            consultation_dt.hour, consultation_dt.minute,
            tzinfo=timezone.utc,
        )

        booking = await create_booking(
            db,
            user_telegram_id=user_id,
            user_username=telegram_username or "",
            user_name=name,
            user_phone=phone,
            specialist_id=specialist_id,
            specialist_name=specialist.name,
            consultation_date=date_str,
            consultation_time=time_str,
            consultation_datetime=consultation_utc,
            additional_info=additional_info,
            status="Подтверждена",
        )
        
        # Записываем в Google Sheets (не критично, не коммитим)
        sheet_service = SheetService()
        sheet_id = await sheet_service.append_booking({
            "id": booking.id,
            "created_at": booking.created_at.strftime("%Y-%m-%d %H:%M") if booking.created_at else "",
            "user_name": name,
            "user_phone": phone,
            "user_username": telegram_username or "",
            "user_telegram_id": user_id,
            "specialist_name": specialist.name,
            "consultation_date": date_str,
            "consultation_time": time_str,
            "status": "Подтверждена",
            "manager_comment": additional_info or "",
        })
        if sheet_id > 0:
            logger.info(f"[BOOKING_CREATE] Booking #{booking.id} saved to Google Sheets (row {sheet_id})")
            booking.google_sheet_row = sheet_id
        else:
            logger.warning(f"[BOOKING_CREATE] Google Sheets write failed for booking #{booking.id}, but booking will be saved")
        
        # Теперь сохраняем всё в БД (booking + google_sheet_row)
        await db.commit()
        await db.refresh(booking)
        logger.info(f"[BOOKING_CREATE] Booking #{booking.id} saved to database")

        scheduler = SchedulerService.get_instance()
        if scheduler:
            scheduler.schedule_reminders(booking)
            logger.info(f"[BOOKING_CREATE] Reminders scheduled for booking #{booking.id}")

        await BookingService._notify_manager(db, booking)
        logger.info(f"[BOOKING_CREATE] Booking #{booking.id} completed successfully")

        return {
            "id": booking.id,
            "specialist_name": specialist.name,
            "consultation_date": date_str,
            "consultation_time": time_str,
            "status": "Подтверждена",
        }

    @staticmethod
    async def reschedule_booking(
        db: AsyncSession,
        booking_id: int,
        new_date_str: str,
        new_time_str: str,
        user_id: int,
    ) -> dict:
        logger.info(f"[BOOKING_RESCHEDULE] Rescheduling booking #{booking_id} to {new_date_str} {new_time_str}")

        booking = await get_booking_by_id(db, booking_id)
        if not booking:
            raise BookingNotFound()

        if booking.status == "Отменена":
            raise BookingAlreadyCancelled()

        if booking.consultation_datetime < datetime.now(timezone.utc):
            raise BookingAlreadyCompleted()

        specialist = await get_specialist_by_id(db, booking.specialist_id)
        if not specialist:
            raise BookingNotFound("Специалист не найден.")

        if await has_booking_at(db, booking.specialist_id,
                                datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M")):
            raise SlotAlreadyBooked("Новое время уже занято.")

        old_date = booking.consultation_date
        old_time = booking.consultation_time

        new_datetime = datetime(
            datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M").year,
            datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M").month,
            datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M").day,
            datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M").hour,
            datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M").minute,
            tzinfo=timezone.utc,
        )

        await update_booking_field(db, booking_id, "consultation_date", new_date_str)
        await update_booking_field(db, booking_id, "consultation_time", new_time_str)
        await update_booking_field(db, booking_id, "consultation_datetime", new_datetime)
        await update_booking_field(db, booking_id, "status", "Перенесена")

        sheet_service = SheetService()
        if booking.google_sheet_row:
            sheet_service.update_booking_status(booking.google_sheet_row, "Перенесена")
            await sheet_service.append_booking({
                "id": booking.id,
                "created_at": booking.created_at.strftime("%Y-%m-%d %H:%M") if booking.created_at else "",
                "user_name": booking.user_name,
                "user_phone": booking.user_phone,
                "user_username": booking.user_username or "",
                "user_telegram_id": booking.user_telegram_id,
                "specialist_name": specialist.name,
                "consultation_date": new_date_str,
                "consultation_time": new_time_str,
                "status": "Перенесена",
                "manager_comment": f"Перенесено с {old_date} {old_time}",
            })

        scheduler = SchedulerService.get_instance()
        if scheduler:
            scheduler.reschedule_reminders(booking_id, new_datetime)

        await BookingService._notify_manager(db, booking,
                                             f"Перенесена с {old_date} {old_time} на {new_date_str} {new_time_str}")

        logger.info(f"[BOOKING_RESCHEDULE] Booking #{booking_id} rescheduled to {new_date_str} {new_time_str}")

        return {
            "id": booking.id,
            "old_datetime": f"{old_date} {old_time}",
            "new_datetime": f"{new_date_str} {new_time_str}",
            "status": "Перенесена",
        }

    @staticmethod
    async def cancel_booking(
        db: AsyncSession,
        booking_id: int,
        user_id: int,
    ) -> dict:
        logger.info(f"[BOOKING_CANCEL] Cancelling booking #{booking_id} by user {user_id}")

        booking = await get_booking_by_id(db, booking_id)
        if not booking:
            raise BookingNotFound()

        if booking.status == "Отменена":
            raise BookingAlreadyCancelled()

        if booking.consultation_datetime < datetime.now(timezone.utc):
            raise BookingAlreadyCompleted()

        await update_booking_status(db, booking_id, "Отменена")

        sheet_service = SheetService()
        if booking.google_sheet_row:
            sheet_service.update_booking_status(booking.google_sheet_row, "Отменена")

        await BookingService._notify_manager(db, booking, "Отменена")

        logger.info(f"[BOOKING_CANCEL] Booking #{booking_id} cancelled")

        return {
            "id": booking.id,
            "status": "Отменена",
        }

    @staticmethod
    async def _notify_manager(db: AsyncSession, booking, reason: str = "") -> None:
        from config.settings import settings
        from main import _bot_ref as main_bot

        msg = (
            f"📋 <b>Заявка #{booking.id}</b>\n\n"
            f"👤 Имя: {booking.user_name}\n"
            f"📱 Телефон: {booking.user_phone}\n"
            f"🔗 Telegram: @{booking.user_username or 'не указан'}\n"
            f"🆔 ID: {booking.user_telegram_id}\n\n"
            f"👨‍⚕️ Специалист: {booking.specialist_name}\n"
            f"📅 Дата: {booking.consultation_date}\n"
            f"🕐 Время: {booking.consultation_time}\n"
            f"📊 Статус: {booking.status}"
        )
        if booking.additional_info:
            msg += f"\n\n💬 Комментарий: {booking.additional_info}"
        if reason:
            msg += f"\n\n📝 {reason}"

        try:
            if main_bot:
                await main_bot.send_message(
                    chat_id=settings.admin_chat_id,
                    text=msg,
                    parse_mode="HTML",
                )
                logger.info(f"[NOTIFY] Manager notification sent for booking #{booking.id}")
        except Exception as e:
            logger.error(f"[NOTIFY] Error sending manager notification: {e}")

    @staticmethod
    def format_booking_notification(booking, reason: str = "") -> str:
        msg = (
            f"📋 <b>Новая заявка #{booking.id}</b>\n\n"
            f"👤 Имя: {booking.user_name}\n"
            f"📱 Телефон: {booking.user_phone}\n"
            f"🔗 Telegram: @{booking.user_username or 'не указан'}\n"
            f"🆔 ID: {booking.user_telegram_id}\n\n"
            f"👨‍⚕️ Специалист: {booking.specialist_name}\n"
            f"📅 Дата: {booking.consultation_date}\n"
            f"🕐 Время: {booking.consultation_time}\n"
            f"📊 Статус: {booking.status}"
        )
        if booking.additional_info:
            msg += f"\n\n💬 Комментарий: {booking.additional_info}"
        if reason:
            msg += f"\n\n📝 {reason}"
        return msg
