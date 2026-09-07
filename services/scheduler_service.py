import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)


class SchedulerService:
    """Сервис для управления напоминаниями через APScheduler."""

    _instance = None
    _scheduler = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._bot = None
        self._scheduler = None

    def set_bot(self, bot):
        """Установка бота для отправки сообщений."""
        self._bot = bot
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler()

    def start(self):
        """Запуск планировщика."""
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler()
            self._scheduler.start()
        elif not self._scheduler.running:
            self._scheduler.start()

    def stop(self):
        """Остановка планировщика."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def schedule_reminders(self, booking=None, booking_id=None):
        """Планирование напоминаний для записи."""
        if booking_id is not None and booking is None:
            # Загрузим booking из БД
            from database.engine import AsyncSessionLocal
            from database.repositories import get_booking_by_id

            async def _load():
                async with AsyncSessionLocal() as db:
                    return await get_booking_by_id(db, booking_id)

            import asyncio
            try:
                loop = asyncio.get_running_loop()
                booking = loop.run_until_complete(_load())
            except RuntimeError:
                pass  # No running loop, skip

        if not booking:
            return

        if hasattr(booking, "id"):
            booking_id = booking.id
            consultation_dt = booking.consultation_datetime
            user_id = booking.user_telegram_id
        else:
            return

        if not consultation_dt or not user_id:
            return

        reminder_24h_sent = getattr(booking, "reminder_24h_sent", False)
        reminder_2h_sent = getattr(booking, "reminder_2h_sent", False)

        # Schedule 24h reminder
        if not reminder_24h_sent:
            trigger_24h = DateTrigger(
                run_date=consultation_dt - timedelta(hours=24),
                timezone=timezone.utc,
            )
            if trigger_24h.run_date > datetime.now(timezone.utc):
                self._scheduler.add_job(
                    self._send_reminder,
                    trigger=trigger_24h,
                    args=[booking_id, "24h"],
                    id=f"reminder_24h_{booking_id}",
                    replace_existing=True,
                )

        # Schedule 2h reminder
        if not reminder_2h_sent:
            trigger_2h = DateTrigger(
                run_date=consultation_dt - timedelta(hours=2),
                timezone=timezone.utc,
            )
            if trigger_2h.run_date > datetime.now(timezone.utc):
                self._scheduler.add_job(
                    self._send_reminder,
                    trigger=trigger_2h,
                    args=[booking_id, "2h"],
                    id=f"reminder_2h_{booking_id}",
                    replace_existing=True,
                )

    def reschedule_reminders(self, booking_id: int, new_datetime: datetime):
        """Обновление напоминаний при переносе."""
        for job_id in [f"reminder_24h_{booking_id}", f"reminder_2h_{booking_id}"]:
            try:
                self._scheduler.remove_job(job_id)
            except Exception:
                pass
        self.schedule_reminders(booking_id=booking_id)

    async def _send_reminder(self, booking_id: int, reminder_type: str):
        """Отправка напоминания."""
        if self._bot is None:
            logger.warning("Бот не установлен в планировщике.")
            return

        from database.engine import AsyncSessionLocal
        from database.repositories import get_booking_by_id, update_booking_field

        async with AsyncSessionLocal() as db:
            booking = await get_booking_by_id(db, booking_id)
            if not booking or booking.status == "Отменена":
                return

            hours = 24 if reminder_type == "24h" else 2
            message = (
                f"⏰ Напоминание!\n\n"
                f"Через {hours} часов ваша консультация с "
                f"{booking.specialist_name}.\n\n"
                f"📅 Дата: {booking.consultation_date}\n"
                f"🕐 Время: {booking.consultation_time}\n\n"
                f"Будем ждать вас!"
            )

            try:
                await self._bot.send_message(
                    chat_id=booking.user_telegram_id,
                    text=message,
                )
                field = "reminder_24h_sent" if reminder_type == "24h" else "reminder_2h_sent"
                await update_booking_field(db, booking_id, field, True)
                logger.info("Напоминание %s отправлено для booking #%d", reminder_type, booking_id)
            except Exception as e:
                logger.error("Ошибка отправки напоминания: %s", e)

    @classmethod
    def get_instance(cls):
        """Получение синглтона."""
        return cls._instance
