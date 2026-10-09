import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from config.settings import settings
from database.engine import AsyncSessionLocal
from database.repositories import get_all_bookings
from utils.helpers import get_datetime_display

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("test_base"))
async def cmd_test_base(message: Message):
    """Тестовая команда для проверки базы данных."""
    logger.info(f"[TEST_BASE] === COMMAND RECEIVED === User {message.from_user.id}")
    
    # Проверка что сообщение от админа
    admin_ids = [int(admin_id) for admin_id in settings.admin_ids_csv.split(',')]
    logger.info(f"[TEST_BASE] Admin IDs from settings: {admin_ids}")
    logger.info(f"[TEST_BASE] User ID: {message.from_user.id}")
    logger.info(f"[TEST_BASE] Is admin: {message.from_user.id in admin_ids}")
    
    if message.from_user.id not in admin_ids:
        logger.warning(f"[TEST_BASE] User {message.from_user.id} tried to access test command")
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        async with AsyncSessionLocal() as db:
            bookings = await get_all_bookings(db)
        
        logger.info(f"[TEST_BASE] Found {len(bookings)} bookings")
        
        if not bookings:
            await message.answer("📋 В базе данных нет записей.")
            return
        
        msg = f"📋 <b>Тест базы данных ({len(bookings)} записей):</b>\n\n"
        
        for b in bookings:
            msg += (
                f"🔹 <b>#{b.id}</b> | Статус: {b.status}\n"
                f"   👤 Имя: {b.user_name}\n"
                f"   📱 Телефон: {b.user_phone}\n"
                f"   🔗 Telegram: @{b.user_username or 'не указан'}\n"
                f"   👨‍⚕️ Специалист: {b.specialist_name}\n"
                f"   📅 Дата: {get_datetime_display(b.consultation_date, b.consultation_time)}\n"
            )
            
            if b.additional_info:
                msg += f"   💬 Комментарий: {b.additional_info}\n"
            
            if b.manager_comment:
                msg += f"   📝 Комментарий менеджера: {b.manager_comment}\n"
            
            msg += f"   🆔 Google Sheet: {b.google_sheet_row or 'не записано'}\n\n"
        
        await message.answer(msg, parse_mode="HTML")
        logger.info(f"[TEST_BASE] Sent {len(bookings)} bookings to admin {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"[TEST_BASE] Error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при проверке базы данных: {str(e)}")
