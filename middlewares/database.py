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
        session: AsyncSession = get_db_session()
        try:
            data["db_session"] = session
            return await handler(event, data)
        finally:
            await session.close()
