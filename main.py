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

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
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
            logger.error(f"Ошибка очистки резервов: {e}", exc_info=True)
        await asyncio.sleep(60)


async def on_startup(**kwargs):
    """Обработчик запуска бота."""
    global _bot_ref
    _bot_ref = kwargs.get("bot")

    logger.info("=" * 60)
    logger.info("ЗАПУСК БОТА")
    logger.info("=" * 60)
    logger.info(f"Bot token: {settings.bot_token[:10]}...")
    logger.info(f"Admin IDs: {settings.admin_ids}")
    logger.info(f"Admin chat: {settings.admin_chat_id}")
    logger.info(f"Google Sheets: {settings.google_sheet_id}")

    # Инициализация базы данных
    logger.info("Шаг 1/4: Инициализация базы данных...")
    await init_db()
    logger.info("Шаг 1/4: База данных инициализирована")

    # Добавление специалистов по умолчанию (если нет)
    logger.info("Шаг 2/4: Проверка специалистов...")
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
                logger.info(f"Добавлено {len(default_specs)} специалистов по умолчанию")
            else:
                logger.info(f"Найдено {len(specs)} специалистов")

    await _add_specs()

    # Добавление расписания по умолчанию
    logger.info("Шаг 3/4: Проверка расписания...")
    async def _add_availability():
        async with AsyncSessionLocal() as db:
            await add_default_availability(db)
            logger.info("Расписание проверено/добавлено")

    await _add_availability()

    # Инициализация Google Sheets
    logger.info("Шаг 4/4: Инициализация Google Sheets...")
    sheet_service = SheetService()
    logger.info("Google Sheets сервис инициализирован")

    # Инициализация планировщика
    logger.info("Инициализация планировщика напоминаний...")
    scheduler = SchedulerService()
    if _bot_ref:
        scheduler.set_bot(_bot_ref)
    scheduler.start()
    logger.info("Планировщик запущен")

    # Запуск периодической очистки
    cleanup_task = asyncio.create_task(cleanup_expired_reservations_task())
    logger.info("Периодическая очистка резервов запущена")
    logger.info("=" * 60)
    logger.info("БОТ ГОТОВ К РАБОТЕ")
    logger.info("=" * 60)
    return {"cleanup_task": cleanup_task}


def register_all_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков."""
    logger.info("Регистрация middleware и обработчиков...")

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

    logger.info("Все обработчики зарегистрированы")


async def on_shutdown(**kwargs):
    """Обработчик остановки бота."""
    logger.info("=" * 60)
    logger.info("ОСТАНОВКА БОТА")
    logger.info("=" * 60)

    scheduler = SchedulerService()
    scheduler.stop()
    logger.info("Планировщик остановлен")

    workflow_data = kwargs.get("workflow_data", {})
    cleanup_task = workflow_data.get("cleanup_task")
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("Очистка резервов остановлена")

    logger.info("БОТ ОСТАНОВЛЕН")


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
    logger.info("Запуск polling...")
    try:
        dp.run_polling(bot_instance, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
