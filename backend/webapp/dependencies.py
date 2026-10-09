"""FastAPI зависимости для работы с базой данных."""
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import AsyncSessionLocal


async def get_db_session() -> AsyncSession:
    """Получение сессии базы данных."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
