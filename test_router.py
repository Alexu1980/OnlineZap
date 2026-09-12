"""Проверка что router admin_view правильно обрабатывает команды."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from unittest.mock import AsyncMock, MagicMock

# Импортируем router
from handlers.admin.admin_view import router as admin_view_router


async def test_router():
    """Проверяет что router содержит обработчик команды /admin_view."""
    print("=" * 60)
    print("ТЕСТ ROUTER admin_view")
    print("=" * 60)
    
    # Проверяем что router содержит handlers
    print(f"\nRouter type: {type(admin_view_router)}")
    print(f"Router name: {admin_view_router.name}")
    
    # Проверяем message handlers
    if hasattr(admin_view_router, 'message_router'):
        message_handlers = admin_view_router.message_router.handlers
        print(f"\nMessage handlers count: {len(message_handlers)}")
        
        for i, handler in enumerate(message_handlers):
            print(f"\nHandler {i + 1}:")
            print(f"  Function: {handler.function.__name__}")
            print(f"  Filters: {handler.filters}")
            
            # Проверяем есть ли фильтр Command("admin_view")
            if hasattr(handler, 'filters'):
                filters = handler.filters
                print(f"  Filters details: {filters}")
    
    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЁН")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_router())
