import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config.settings import settings
from database.engine import init_db, AsyncSessionLocal
from database.repositories import add_default_availability, get_active_specialists
from middlewares.database import DatabaseSessionMiddleware
from services.scheduler_service import SchedulerService
from services.sheet_service import SheetService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Global bot reference for notifications
_bot_ref = None


# Import routers
from handlers.user import start as user_start
from handlers.user import specialist as user_specialist
from handlers.user import scheduling as user_scheduling
from handlers.user import contacts as user_contacts
from handlers.user import additional as user_additional
from handlers.user import review as user_review
from handlers.user import reschedule as user_reschedule
from handlers.user import cancel as user_cancel
from handlers.admin import bookings as admin_bookings
from handlers.admin import sheets as admin_sheets


async def cleanup_expired_reservations_task():
    """Периодическая очистка истёкших резервов слотов (каждую минуту)."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                from database.repositories import cleanup_expired_reservations
                count = await cleanup_expired_reservations(db)
                if count > 0:
                    logger.info(f"Очищены истёкшие резервы: {count}")
        except Exception as e:
            logger.error(f"Ошибка очистки резервов: {e}")
        await asyncio.sleep(60)


async def on_startup(**kwargs):
    """Обработчик запуска бота."""
    global _bot_ref
    _bot_ref = kwargs.get("bot")

    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    await init_db()

    # Добавление специалистов по умолчанию (если нет)
    async def _add_specs():
        async with AsyncSessionLocal() as db:
            specs = await get_active_specialists(db)
            if not specs:
                from database.models import Specialist
                default_specs = [
                    Specialist(name="Анна Петрова", specialization="Когнитивно-поведенческая терапия"),
                    Specialist(name="Михаил Иванов", specialization="Гуманистический подход"),
                    Specialist(name="Елена Сидорова", specialization="Семейная терапия"),
                ]
                db.add_all(default_specs)
                await db.commit()
                logger.info("Добавлены специалисты по умолчанию.")

    await _add_specs()

    # Добавление расписания по умолчанию
    async def _add_availability():
        async with AsyncSessionLocal() as db:
            await add_default_availability(db)
            logger.info("Расписание по умолчанию добавлено.")

    await _add_availability()

    # Инициализация Google Sheets
    logger.info("Инициализация Google Sheets...")
    sheet_service = SheetService()

    # Инициализация планировщика
    logger.info("Инициализация планировщика напоминаний...")
    scheduler = SchedulerService()
    if _bot_ref:
        scheduler.set_bot(_bot_ref)
    scheduler.start()
    logger.info("Планировщик запущен.")

    # Запуск периодической очистки
    cleanup_task = asyncio.create_task(cleanup_expired_reservations_task())
    return {"cleanup_task": cleanup_task}


def register_all_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков."""
    # Middleware
    dp.message.middleware(DatabaseSessionMiddleware())
    dp.callback_query.middleware(DatabaseSessionMiddleware())

    # User routers
    dp.include_router(user_start.router)
    dp.include_router(user_specialist.router)
    dp.include_router(user_scheduling.router)
    dp.include_router(user_contacts.router)
    dp.include_router(user_additional.router)
    dp.include_router(user_review.router)
    dp.include_router(user_reschedule.router)
    dp.include_router(user_cancel.router)

    # Admin routers
    dp.include_router(admin_bookings.router)
    dp.include_router(admin_sheets.router)


async def on_shutdown(**kwargs):
    """Обработчик остановки бота."""
    logger.info("Остановка планировщика...")
    scheduler = SchedulerService()
    scheduler.stop()

    workflow_data = kwargs.get("workflow_data", {})
    cleanup_task = workflow_data.get("cleanup_task")
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

    logger.info("Бот остановлен.")


def main():
    # Create bot and dispatcher
    bot_instance = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Register handlers
    register_all_handlers(dp)

    # Start polling
    logger.info("Бот запущен...")
    try:
        dp.run_polling(bot_instance, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("Остановлен пользователем.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
