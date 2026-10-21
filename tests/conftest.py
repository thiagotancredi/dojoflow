import os
from collections.abc import AsyncGenerator, Iterator

import psycopg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import create_engine, insert, make_url, text
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
from dojoflow.integrations.telegram.service import TelegramService
from dojoflow.main import app
from dojoflow.models.academy import Academy
from dojoflow.models.master import Master
from dojoflow.services import security
from tests.helpers.auth import SEED

TEST_DATABASE_URL = os.environ.get(
    'TEST_DATABASE_URL',
    'postgresql+psycopg://postgres:postgres@localhost:5434/dojoflow_test',
)

# Academia e mestre fixos: criados uma vez e preservados entre os testes
PRESERVED_TABLES = {Academy.__tablename__, Master.__tablename__}
TABLES_TO_EMPTY = ', '.join(
    f'"{table.name}"'
    for table in Base.metadata.sorted_tables
    if table.name not in PRESERVED_TABLES
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


@pytest.fixture(scope='session', autouse=True)
def _fast_password_hashing() -> Iterator[None]:
    # O Argon2 de produção leva ~130 ms por hash de propósito; nos testes
    # de cadastro e login, o custo mínimo do algoritmo basta
    original = security.password_hash
    security.password_hash = PasswordHash((
        Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),
    ))
    yield
    security.password_hash = original


@pytest.fixture(scope='session')
def _test_schema(
    _ensure_test_database: None,
    _fast_password_hashing: None,
) -> Iterator[None]:
    # Tabelas criadas uma vez por execução (antes: a cada teste)
    engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    SEED.password_hash = security.hash_password(SEED.password)

    with engine.begin() as connection:
        SEED.academy_id = connection.execute(
            insert(Academy)
            .values(name=SEED.academy_name)
            .returning(Academy.id)
        ).scalar_one()
        SEED.master_id = connection.execute(
            insert(Master).values(**_seed_master_values()).returning(Master.id)
        ).scalar_one()

    yield

    Base.metadata.drop_all(engine)
    engine.dispose()


def _seed_master_values() -> dict[str, object]:
    return {
        'academy_id': SEED.academy_id,
        'name': SEED.master_name,
        'email': SEED.email,
        'phone': SEED.phone,
        'password_hash': SEED.password_hash,
        'telegram_user_id': None,
    }


async def _no_telegram_call(*args: object, **kwargs: object) -> None:
    return None


@pytest.fixture(autouse=True)
def _block_telegram_api(monkeypatch: pytest.MonkeyPatch) -> None:
    # Nenhum teste fala com api.telegram.org de verdade (antes: cada clique
    # de botão no bot ia até a internet). Testes que conferem as mensagens
    # continuam trocando send_message pela versão deles.
    monkeypatch.setattr(TelegramService, 'send_message', _no_telegram_call)
    monkeypatch.setattr(
        TelegramService, 'answer_callback_query', _no_telegram_call
    )


@pytest_asyncio.fixture(autouse=True)
def _configure_test_settings() -> None:
    settings.INTERNAL_API_KEY = 'test-internal-key'
    settings.JWT_SECRET = 'test-jwt-secret-with-enough-length-32b'
    settings.TELEGRAM_BOT_USERNAME = 'dojoflow_test_bot'
    settings.CORS_ORIGINS = 'http://localhost:5173'


async def _reset_data(session: AsyncSession) -> None:
    # Esvazia tudo, menos a academia e o mestre fixos (e volta os dois ao
    # estado original, caso um teste tenha alterado algum dado deles)
    await session.execute(
        text(f'TRUNCATE {TABLES_TO_EMPTY} RESTART IDENTITY CASCADE')
    )
    await session.execute(
        text('DELETE FROM master WHERE id <> :id'), {'id': SEED.master_id}
    )
    await session.execute(
        text('DELETE FROM academy WHERE id <> :id'), {'id': SEED.academy_id}
    )
    await session.execute(
        text(
            "UPDATE academy SET name = :name, status = 'active' WHERE id = :id"
        ),
        {'name': SEED.academy_name, 'id': SEED.academy_id},
    )
    await session.execute(
        text(
            'UPDATE master SET name = :name, email = :email, phone = :phone, '
            'password_hash = :password_hash, telegram_user_id = NULL '
            'WHERE id = :id'
        ),
        {
            'name': SEED.master_name,
            'email': SEED.email,
            'phone': SEED.phone,
            'password_hash': SEED.password_hash,
            'id': SEED.master_id,
        },
    )
    await session.commit()


@pytest_asyncio.fixture
async def db_session(
    _test_schema: None,
) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(url=TEST_DATABASE_URL, poolclass=NullPool)

    testing_session_local = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with testing_session_local() as session:
        await _reset_data(session)
        yield session

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
