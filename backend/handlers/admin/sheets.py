from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from services.sheet_service import SheetService

router = Router()


@router.message(Command("sync"))
async def cmd_sync_sheets(message: Message):
    """Синхронизация с Google Sheets (для отладки)."""
    sheet_service = SheetService()
    try:
        sheet_service._initialize_sheet()
        await message.answer("✅ Google Sheets инициализирована.")
    except Exception as e:
        await message.answer(f"❌ Ошибка синхронизации: {str(e)}")


@router.callback_query(lambda c: c.data == "debug_sheets")
async def cb_debug_sheets(callback: CallbackQuery):
    """Отладка Google Sheets."""
    sheet_service = SheetService()
    try:
        sheet_service._initialize_sheet()
        await callback.message.answer("✅ Sheets проинициализирована.")
        await callback.answer()
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {str(e)}")
        await callback.answer()
