from collections.abc import ASyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from dojoflow.core.settings import settings

engine = create_async_engine(url=settings.DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> ASyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
