import os
from collections.abc import AsyncGenerator

import psycopg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import dojoflow.models  # noqa: F401
from dojoflow.core.settings import settings
from dojoflow.database.base import Base
from dojoflow.database.session import get_session
from dojoflow.main import app

TEST_DATABASE_URL = os.environ.get(
    'TEST_DATABASE_URL',
    'postgresql+psycopg://postgres:postgres@localhost:5434/dojoflow_test',
)


@pytest.fixture(scope='session', autouse=True)
def _ensure_test_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    admin_url = url.set(drivername='postgresql', database='postgres')

    with psycopg.connect(
        admin_url.render_as_string(hide_password=False),
        autocommit=True,
    ) as connection:
        exists = connection.execute(
            'SELECT 1 FROM pg_database WHERE datname = %s',
            (url.database,),
        ).fetchone()

        if exists is None:
            connection.execute(
                sql.SQL('CREATE DATABASE {}').format(
                    sql.Identifier(url.database)
                )
            )


@pytest_asyncio.fixture(autouse=True)
def _configure_test_settings() -> None:
    settings.INTERNAL_API_KEY = 'test-internal-key'
    settings.JWT_SECRET = 'test-jwt-secret-with-enough-length-32b'
    settings.TELEGRAM_BOT_USERNAME = 'dojoflow_test_bot'
    settings.CORS_ORIGINS = 'http://localhost:5173'


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(url=TEST_DATABASE_URL, poolclass=NullPool)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    testing_session_local = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with testing_session_local() as session:
        yield session

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()
