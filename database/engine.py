from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Создание всех таблиц в базе данных."""
    import database.models  # noqa: F401 — модели должны быть импортированы для создания таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_db_session() -> AsyncSession:
    """Получение сессии базы данных."""
    return AsyncSessionLocal()
