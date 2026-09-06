from collections.abc import Callable, Awaitable
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram import BaseMiddleware
from database.engine import get_db_session


class DatabaseSessionMiddleware(BaseMiddleware):
    """Middleware для автоматического открытия/закрытия сессии БД."""

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        async with get_db_session() as db_session:
            data["db_session"] = db_session
            return await handler(event, data)
