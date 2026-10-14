# Site V1 — Plano A: Backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deixar o backend FastAPI pronto para o site V1: fundação (testes em Postgres, transações unificadas, CI), segurança (sessões de refresh em cookie com rotação, `role` no JWT, correções), e a API que o site consome (`public_id`, respostas tipadas, paginação, matrículas, dashboard, CEP).

**Architecture:** Os *services* continuam trabalhando com IDs inteiros — o bot do Telegram não muda. Toda conversão `public_id` (UUID) ↔ `id` acontece na camada de rotas, via dependencies. Schemas novos de API (`schemas/*_api.py`) expõem `id = public_id`. A unidade de trabalho passa a ser do service: `@transactional` só commita na chamada mais externa; repositórios recusam escrita fora de uma unidade de trabalho.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 async + psycopg 3, Alembic, Pydantic v2, PyJWT, pwdlib (Argon2), pytest + pytest-asyncio + httpx, PostgreSQL 17, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-13-web-frontend-v1-design.md` (seções 4, 6.1, 6.2, 6.4, 7.1, 7.3). O frontend é o **Plano B**, escrito depois deste.

## Global Constraints

- Python `>=3.13,<4.0`; ruff com `line-length = 79`, `quote-style = 'single'`, regras `I F E W PL PT` — `poetry run ruff check .` deve passar ao fim de cada task.
- Código (nomes, classes, tabelas) em inglês. Mensagens de erro da API em inglês no `detail`; o frontend traduz pelo `code`.
- Todo identificador exposto pela API é o `public_id` (UUID). Nenhuma rota do site recebe ou devolve `id` inteiro.
- Os *services* recebem e devolvem `int` — não alterar assinaturas usadas pelo bot, exceto onde a task diz.
- `due_day` válido: **1 a 28** (mesma regra do bot).
- Cookie de refresh: nome `dojoflow_refresh`, `httpOnly`, `SameSite=Lax`, `Path=/api/v1/auth`, `Secure` em todo ambiente exceto `dev`.
- `ENVIRONMENT` aceita `dev` | `prod`. Fora de `dev`, a aplicação não inicia com `JWT_SECRET == 'change-me-in-production'`.
- Formato de erro: `{"detail": str, "code": str}` para exceções de domínio; 422 do Pydantic mantém o formato padrão do FastAPI.
- Testes rodam em Postgres (`TEST_DATABASE_URL`, padrão `postgresql+psycopg://postgres:postgres@localhost:5433/dojoflow_test`). Antes de rodar: `docker compose up -d postgres`.
- Antes de usar qualquer action do GitHub ou lib nova, conferir a versão atual na documentação oficial.
- Commits pequenos, mensagem em inglês no padrão `tipo: descrição`, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- **Duas abas fazendo refresh ao mesmo tempo:** a segunda apresenta o token que a primeira acabou de rotacionar. Esperado: as duas continuam logadas (janela de tolerância de 30 s), não "roubo detectado". → teste em Task 8.
- **Senha atual errada em "trocar senha" (site logado):** esperado 403 com `code = CURRENT_PASSWORD_INVALID`, **não** 401 — um 401 faria o frontend tentar refresh e deslogar. → teste em Task 9.
- **`due_day` 29, 30 ou 31 enviado pelo site:** esperado 422 (o bot já recusa; o REST hoje aceita até 31). → teste em Task 12.
- **Busca com `%` ou `_` no nome:** esperado busca literal, não "casar tudo". → teste em Task 13.
- **Página além do fim ou filtro por modalidade inexistente:** esperado página vazia com `total` correto, não erro. → teste em Task 13.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `tests/conftest.py` (modificar) | Fixtures em Postgres; cria o banco de teste se faltar |
| `tests/helpers/auth.py` (criar) | `auth_headers()`, `create_modality()` para testes de API |
| `src/dojoflow/database/transaction.py` (reescrever) | `unit_of_work()`, `transactional`, `in_unit_of_work()` |
| `src/dojoflow/repositories/base.py` (modificar) | Remove `@transactional`; escrita exige unidade de trabalho |
| `.github/workflows/backend.yml` (criar) | CI: ruff, typos, pytest com Postgres |
| `src/dojoflow/core/settings.py` (modificar) | `ENVIRONMENT`, `WEB_APP_URL`, trava do `JWT_SECRET`, `cookie_secure` |
| `.env.example` (criar) | Variáveis documentadas |
| `src/dojoflow/shared/exceptions.py` (modificar) | `code` nas exceções de domínio |
| `src/dojoflow/api/exception_handlers.py` (modificar) | Inclui `code` na resposta |
| `src/dojoflow/services/security.py` (modificar) | `role` no access token; remove refresh JWT |
| `src/dojoflow/models/refresh_session.py` (criar) | Model `RefreshSession` |
| `migrations/versions/f9a0b1c2d3e4_create_refresh_session_table.py` (criar) | Migration |
| `src/dojoflow/repositories/refresh_session.py` (criar) | Busca por hash, revogação em massa |
| `src/dojoflow/services/auth.py` (modificar) | Sessões, rotação, reuso, logout, senha atual |
| `src/dojoflow/api/routes/auth.py` (modificar) | Cookie de refresh, `/logout` |
| `src/dojoflow/schemas/auth.py` (modificar) | `AuthTokenResponse` sem refresh; `AuthResult`; `current_password` |
| `src/dojoflow/api/dependencies/public_ids.py` (criar) | Resolução `public_id` → `id` |
| `src/dojoflow/schemas/modality_api.py` (criar) | Schemas de modalidade para o site |
| `src/dojoflow/schemas/student_api.py` (criar) | Schemas de aluno/matrícula/ficha/página para o site |
| `src/dojoflow/api/routes/students.py` (reescrever) | Rotas de aluno com UUID |
| `src/dojoflow/services/student.py` (modificar) | Matrículas por id, página com filtros, ids públicos nos detalhes |
| `src/dojoflow/services/dashboard.py` (criar) | Resumo do dashboard |
| `src/dojoflow/schemas/dashboard.py` (criar) | Schemas do dashboard |
| `src/dojoflow/api/routes/dashboard.py` (criar) | `GET /dashboard/summary` |
| `src/dojoflow/api/routes/cep.py` (criar) | `GET /cep/{zip_code}` |
| `src/dojoflow/services/telegram_webhook.py` (modificar) | `/web` envia link |
| `tests/api/test_openapi_contract.py` (criar) | Toda rota do site com schema de resposta |

---

### Task 1: Testes rodando em Postgres

**Files:**
- Modify: `tests/conftest.py`
- Modify: `pyproject.toml` (seção `[tool.pytest.ini_options]`)

**Interfaces:**
- Produces: fixture `db_session: AsyncSession` (agora Postgres, `NullPool`, tabelas recriadas a cada teste); fixture `client: AsyncClient`. Constante `TEST_DATABASE_URL` em `tests/conftest.py`.

- [ ] **Step 1: Subir o Postgres local**

Run: `docker compose up -d postgres`
Expected: container `dojoflow_postgres` rodando na porta 5433.

- [ ] **Step 2: Reescrever as fixtures de banco em `tests/conftest.py`**

Substituir o arquivo inteiro por:

```python
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
    'postgresql+psycopg://postgres:postgres@localhost:5433/dojoflow_test',
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
```

O `drop_all` antes do `create_all` limpa sobras de uma execução interrompida.

- [ ] **Step 3: Remover a dependência de SQLite**

Run: `poetry remove --group dev aiosqlite`
Expected: `aiosqlite` sai do `pyproject.toml` e do `poetry.lock`.

- [ ] **Step 4: Rodar a suíte inteira**

Run: `poetry run pytest -q`
Expected: os 164 testes rodam contra Postgres. Se algum falhar, a causa é diferença real entre SQLite e Postgres. Para cada falha:
1. Ler o erro e identificar a categoria: ordem de resultados sem `ORDER BY` (corrigir o **código**, adicionando `order_by`), comparação de tipos (`Decimal` vs `str`, `datetime` com/sem fuso), ou sintaxe específica.
2. Corrigir o código de produção quando o bug for real; corrigir o teste só quando ele dependia de comportamento do SQLite.
3. Nunca apagar um teste nem afrouxar uma asserção para passar.

Expected final: `164 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py pyproject.toml poetry.lock src
git commit -m "test: run test suite against PostgreSQL"
```

---

### Task 2: Unidade de trabalho unificada

**Files:**
- Rewrite: `src/dojoflow/database/transaction.py`
- Modify: `src/dojoflow/repositories/base.py`
- Modify: `src/dojoflow/repositories/master.py:54` (remover `@transactional`)
- Modify: `src/dojoflow/services/telegram_conversation_state.py:128-228`
- Modify: `devtools/seeds/onboarding.py`
- Modify: services que escrevem sem `@transactional` (descobertos no Step 7)
- Test: `tests/database/__init__.py`, `tests/database/test_transaction.py`

**Interfaces:**
- Produces: `unit_of_work(db_session: AsyncSession) -> AsyncContextManager[None]`; decorator `transactional` (mesmo nome e uso de hoje); `in_unit_of_work(db_session: AsyncSession) -> bool`. Regra: só a unidade **mais externa** faz `commit` (ou `rollback` em exceção). Repositórios lançam `RuntimeError` ao escrever (`create`, `update_by_id`, `delete_by_id`) fora de uma unidade de trabalho.

**Por quê:** hoje `@transactional` só commita se a sessão não estiver em transação. Qualquer leitura feita fora de um método decorado (ex.: `StudentService.get_details` usa `db_session.execute` direto) abre uma transação implícita, e o `update` decorado seguinte **não commita**. Os `commit()` manuais em `telegram_conversation_state.py` são o remendo desse bug.

- [ ] **Step 1: Escrever os testes**

Criar `tests/database/__init__.py` vazio e `tests/database/test_transaction.py`:

```python
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import in_unit_of_work, unit_of_work
from dojoflow.models.modality import Modality
from dojoflow.repositories.modality import ModalityRepository


async def _committed_modality_count(db_session: AsyncSession) -> int:
    async with AsyncSession(bind=db_session.bind) as other_session:
        return await other_session.scalar(
            select(func.count()).select_from(Modality)
        )


def _modality_data(name: str) -> dict[str, object]:
    return {'name': name, 'emoji': '🥋', 'is_active': True}


@pytest.mark.asyncio
async def test_write_outside_unit_of_work_raises(
    db_session: AsyncSession,
) -> None:
    repository = ModalityRepository(db_session=db_session)

    with pytest.raises(RuntimeError, match='unit of work'):
        await repository.create(_modality_data('Judô'))


@pytest.mark.asyncio
async def test_outermost_unit_of_work_commits(
    db_session: AsyncSession,
) -> None:
    repository = ModalityRepository(db_session=db_session)

    async with unit_of_work(db_session):
        await repository.create(_modality_data('Judô'))

    assert await _committed_modality_count(db_session) == 1
    assert in_unit_of_work(db_session) is False


@pytest.mark.asyncio
async def test_nested_unit_of_work_commits_only_at_outermost(
    db_session: AsyncSession,
) -> None:
    repository = ModalityRepository(db_session=db_session)

    async with unit_of_work(db_session):
        async with unit_of_work(db_session):
            await repository.create(_modality_data('Judô'))

        assert await _committed_modality_count(db_session) == 0

    assert await _committed_modality_count(db_session) == 1


@pytest.mark.asyncio
async def test_exception_rolls_back_outermost_unit_of_work(
    db_session: AsyncSession,
) -> None:
    repository = ModalityRepository(db_session=db_session)

    with pytest.raises(ValueError, match='boom'):
        async with unit_of_work(db_session):
            await repository.create(_modality_data('Judô'))
            raise ValueError('boom')

    assert await _committed_modality_count(db_session) == 0
    assert in_unit_of_work(db_session) is False


@pytest.mark.asyncio
async def test_commits_even_after_implicit_read_transaction(
    db_session: AsyncSession,
) -> None:
    repository = ModalityRepository(db_session=db_session)

    await db_session.execute(select(Modality))
    assert db_session.in_transaction() is True

    async with unit_of_work(db_session):
        await repository.create(_modality_data('Judô'))

    assert await _committed_modality_count(db_session) == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/database/test_transaction.py -v`
Expected: FAIL — `ImportError: cannot import name 'in_unit_of_work'`.

- [ ] **Step 3: Reescrever `src/dojoflow/database/transaction.py`**

```python
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

UNIT_OF_WORK_DEPTH_KEY = 'unit_of_work_depth'


def in_unit_of_work(db_session: AsyncSession) -> bool:
    return db_session.info.get(UNIT_OF_WORK_DEPTH_KEY, 0) > 0


@asynccontextmanager
async def unit_of_work(
    db_session: AsyncSession,
) -> AsyncGenerator[None, None]:
    depth = db_session.info.get(UNIT_OF_WORK_DEPTH_KEY, 0)
    db_session.info[UNIT_OF_WORK_DEPTH_KEY] = depth + 1

    try:
        yield
    except BaseException:
        db_session.info[UNIT_OF_WORK_DEPTH_KEY] = depth

        if depth == 0:
            await db_session.rollback()

        raise

    db_session.info[UNIT_OF_WORK_DEPTH_KEY] = depth

    if depth == 0:
        await db_session.commit()


def transactional(method: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(method)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        async with unit_of_work(self.db_session):
            return await method(self, *args, **kwargs)

    return wrapper
```

- [ ] **Step 4: Ajustar `src/dojoflow/repositories/base.py`**

1. Trocar o import `from dojoflow.database.transaction import transactional` por `from dojoflow.database.transaction import in_unit_of_work`.
2. Remover **todas** as linhas `@transactional` do arquivo.
3. Adicionar o método abaixo logo após `_raise_not_found`:

```python
    def _ensure_unit_of_work(self) -> None:
        if not in_unit_of_work(self.db_session):
            raise RuntimeError(
                f'{self.model.__name__} write outside a unit of work. '
                'Decorate the calling service method with @transactional.'
            )
```

4. Chamar `self._ensure_unit_of_work()` como **primeira linha** de `create`, `update_by_id` e `delete_by_id`.

Em `src/dojoflow/repositories/master.py`, remover o `@transactional` da linha 54 e o import, se ficar sem uso.

- [ ] **Step 5: Remover commits manuais de `src/dojoflow/services/telegram_conversation_state.py`**

Nos três métodos `update_student_creation_context`, `update_student_search_context` e `update_student_edit_context`, substituir o bloco `try/except` por chamada direta e garantir `@transactional` em todos os três. Exemplo para `update_student_search_context` (repetir o mesmo formato nos outros dois, cada um com seu `TelegramFlow`):

```python
    @transactional
    async def update_student_search_context(
        self,
        state_id: int,
        next_step: TelegramStep,
        context_data: dict[str, Any],
    ) -> None:
        await self.telegram_conversation_state_repository.update_by_id(
            record_id=state_id,
            data={
                'current_flow': TelegramFlow.STUDENT_SEARCH,
                'current_step': next_step,
                'context_data': self._serialize_context_data(context_data),
            },
        )
```

Run: `grep -rn "\.commit()\|\.rollback()" src/dojoflow`
Expected: só ocorrências em `src/dojoflow/database/transaction.py`.

- [ ] **Step 6: Ajustar o seed**

Em `devtools/seeds/onboarding.py`, envolver as escritas feitas com repositórios em `async with unit_of_work(session):` (import `from dojoflow.database.transaction import unit_of_work`).

- [ ] **Step 7: Rodar os testes novos e a suíte inteira**

Run: `poetry run pytest tests/database/test_transaction.py -v`
Expected: 5 passed.

Run: `poetry run pytest -q`
Expected: pode haver falhas `RuntimeError: <Model> write outside a unit of work`. Cada uma aponta um método de *service* que escreve sem `@transactional`. Para cada falha, abrir o traceback, achar o método **público** do service mais próximo da escrita e adicionar `@transactional` nele (ex.: `AddressService.create`, `MasterService.create`, `MasterService.link_telegram_user`). Não decorar handlers do bot nem rotas. Repetir até: todos os testes passando.

- [ ] **Step 8: Lint e commit**

Run: `poetry run ruff check . && poetry run ruff format --check .`
Expected: sem apontamentos.

```bash
git add src devtools tests/database
git commit -m "refactor: unify transactions under service-owned unit of work"
```

---

### Task 3: CI do backend

**Files:**
- Create: `.github/workflows/backend.yml`

**Interfaces:**
- Consumes: `TEST_DATABASE_URL` (Task 1).

- [ ] **Step 1: Conferir versões atuais**

Conferir no GitHub a major atual de `actions/checkout` e `actions/setup-python` e usar essas. (Em out/2026 as referências conhecidas eram `actions/checkout@v5` e `actions/setup-python@v6`.)

- [ ] **Step 2: Criar `.github/workflows/backend.yml`**

```yaml
name: backend

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: dojoflow
        ports:
          - 5433:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      TEST_DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5433/dojoflow_test
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: '3.13'
      - run: pipx install poetry
      - run: poetry install --no-interaction
      - run: poetry run ruff check .
      - run: poetry run ruff format --check .
      - run: poetry run typos .
      - run: poetry run pytest -q
```

- [ ] **Step 3: Validar localmente o que o CI roda**

Run: `poetry run ruff check . && poetry run ruff format --check . && poetry run typos . && poetry run pytest -q`
Expected: tudo passa. Se `typos` apontar falsos positivos em palavras em português, adicionar um `_typos.toml` na raiz com `[default.extend-words]` listando cada palavra (ex.: `matricula = "matricula"`).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/backend.yml
git add _typos.toml   # só se foi criado no Step 3
git commit -m "ci: add backend workflow with PostgreSQL"
```

---

### Task 4: Configuração segura, rota aberta removida e webhook com comparação constante

**Files:**
- Modify: `src/dojoflow/core/settings.py`
- Create: `.env.example`
- Modify: `src/dojoflow/api/routes/telegram.py:45`
- Delete: `src/dojoflow/api/routes/master.py`
- Modify: `src/dojoflow/main.py` (remover `master_router`)
- Delete: `tests/api/test_master_context.py`
- Test: `tests/core/__init__.py`, `tests/core/test_settings.py`, `tests/api/test_security_routes.py`

**Interfaces:**
- Produces: `settings.ENVIRONMENT: Literal['dev', 'prod']`, `settings.WEB_APP_URL: str`, `settings.cookie_secure: bool` (property), constante `DEFAULT_JWT_SECRET = 'change-me-in-production'` em `core/settings.py`.

- [ ] **Step 1: Escrever os testes**

`tests/core/__init__.py` vazio. `tests/core/test_settings.py`:

```python
import pytest
from pydantic import ValidationError

from dojoflow.core.settings import DEFAULT_JWT_SECRET, Settings


def test_prod_refuses_default_jwt_secret() -> None:
    with pytest.raises(ValidationError, match='JWT_SECRET'):
        Settings(
            _env_file=None,
            ENVIRONMENT='prod',
            JWT_SECRET=DEFAULT_JWT_SECRET,
        )


def test_prod_accepts_custom_jwt_secret() -> None:
    settings = Settings(
        _env_file=None,
        ENVIRONMENT='prod',
        JWT_SECRET='a-real-secret-with-enough-length-32',
    )

    assert settings.cookie_secure is True


def test_dev_allows_default_secret_and_insecure_cookie() -> None:
    settings = Settings(
        _env_file=None,
        ENVIRONMENT='dev',
        JWT_SECRET=DEFAULT_JWT_SECRET,
    )

    assert settings.cookie_secure is False
```

`tests/api/test_security_routes.py`:

```python
from http import HTTPStatus

import pytest
from httpx import AsyncClient

from dojoflow.core.settings import settings


@pytest.mark.asyncio
async def test_master_context_route_was_removed(
    client: AsyncClient,
) -> None:
    response = await client.get('/api/v1/masters/context/123456')

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_webhook_rejects_wrong_secret(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', 'right')

    response = await client.post(
        '/api/v1/telegram/webhook',
        json={'update_id': 1},
        headers={'X-Telegram-Bot-Api-Secret-Token': 'wrong'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/core tests/api/test_security_routes.py -v`
Expected: FAIL — `ImportError: cannot import name 'DEFAULT_JWT_SECRET'` e a rota de contexto responde 200 ou 404 por outro motivo (o teste de rota passa a valer depois do Step 4).

- [ ] **Step 3: Atualizar `src/dojoflow/core/settings.py`**

```python
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = 'change-me-in-production'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8'
    )

    PROJECT_NAME: str = 'DojoFlow'
    API_V1_PREFIX: str = '/api/v1'
    ENVIRONMENT: Literal['dev', 'prod'] = 'dev'
    WEB_APP_URL: str = 'http://localhost:5173'

    TELEGRAM_BOT_TOKEN: str = ''
    TELEGRAM_WEBHOOK_BASE_URL: str = ''
    TELEGRAM_WEBHOOK_SECRET: str = ''
    TELEGRAM_BOT_USERNAME: str = ''

    DATABASE_URL: str = (
        'postgresql+psycopg://postgres:password@localhost:5432/dojoflow'
    )

    JWT_SECRET: str = DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = 'HS256'
    JWT_ACCESS_TTL_MINUTES: int = 30
    JWT_REFRESH_TTL_DAYS: int = 14
    JWT_TELEGRAM_LINK_TTL_MINUTES: int = 15
    JWT_TELEGRAM_SETUP_TTL_MINUTES: int = 15

    CORS_ORIGINS: str = 'http://localhost:5173,http://127.0.0.1:5173'

    # When set, POST /onboarding requires X-Internal-Api-Key header.
    INTERNAL_API_KEY: str = ''

    @model_validator(mode='after')
    def _refuse_default_secret_outside_dev(self) -> Self:
        if self.ENVIRONMENT != 'dev' and self.JWT_SECRET == DEFAULT_JWT_SECRET:
            raise ValueError(
                'JWT_SECRET must be set when ENVIRONMENT is not dev.'
            )

        return self

    @property
    def cookie_secure(self) -> bool:
        return self.ENVIRONMENT != 'dev'

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(',')
            if origin.strip()
        ]


settings = Settings()
```

- [ ] **Step 4: Remover a rota aberta e usar `compare_digest`**

1. Apagar `src/dojoflow/api/routes/master.py` e `tests/api/test_master_context.py`.
2. Em `src/dojoflow/main.py`, remover o import e o `app.include_router(master_router, ...)`.
3. Em `src/dojoflow/api/routes/telegram.py`, adicionar `import secrets` e trocar a condição por:

```python
    if telegram_secret_token is None or not secrets.compare_digest(
        telegram_secret_token,
        settings.TELEGRAM_WEBHOOK_SECRET,
    ):
```

Run: `grep -rn "get_context_by_telegram_user_id" src`
Expected: ainda usado pelo bot — **não** remover o método do service.

- [ ] **Step 5: Criar `.env.example`**

```dotenv
ENVIRONMENT=dev
WEB_APP_URL=http://localhost:5173
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/dojoflow
JWT_SECRET=change-me-in-production
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=
TELEGRAM_WEBHOOK_BASE_URL=
TELEGRAM_WEBHOOK_SECRET=
INTERNAL_API_KEY=
```

- [ ] **Step 6: Rodar os testes**

Run: `poetry run pytest tests/core tests/api/test_security_routes.py -v && poetry run pytest -q`
Expected: tudo passando.

- [ ] **Step 7: Commit**

```bash
git add -A src tests .env.example
git commit -m "fix: lock down settings, remove open master context route"
```

---

### Task 5: Códigos de erro nas respostas

**Files:**
- Modify: `src/dojoflow/shared/exceptions.py`
- Modify: `src/dojoflow/api/exception_handlers.py`
- Test: `tests/api/test_error_format.py`

**Interfaces:**
- Produces: `AppError(message: str = '', *, code: str | None = None)` com atributo `code: str`. Códigos padrão: `NotFoundError → 'NOT_FOUND'`, `ConflictError → 'CONFLICT'`, `UnauthorizedError → 'UNAUTHORIZED'`, `ForbiddenError → 'FORBIDDEN'`. Corpo de erro: `{'detail': str, 'code': str}`.

- [ ] **Step 1: Escrever o teste**

`tests/api/test_error_format.py`:

```python
from http import HTTPStatus

import pytest
from httpx import AsyncClient

from dojoflow.shared.exceptions import NotFoundError


def test_custom_code_overrides_default() -> None:
    error = NotFoundError('missing', code='STUDENT_NOT_FOUND')

    assert error.code == 'STUDENT_NOT_FOUND'
    assert str(error) == 'missing'


def test_default_code_per_class() -> None:
    assert NotFoundError('x').code == 'NOT_FOUND'


@pytest.mark.asyncio
async def test_unauthorized_response_has_code(client: AsyncClient) -> None:
    response = await client.get('/api/v1/auth/me')

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {
        'detail': 'Authentication required.',
        'code': 'UNAUTHORIZED',
    }
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_error_format.py -v`
Expected: FAIL — `TypeError: NotFoundError() got an unexpected keyword argument 'code'`.

- [ ] **Step 3: Implementar `src/dojoflow/shared/exceptions.py`**

```python
class AppError(Exception):
    """Base exception for application errors."""

    default_code = 'APP_ERROR'

    def __init__(self, message: str = '', *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code or self.default_code


class NotFoundError(AppError):
    """Raised when a requested record is not found."""

    default_code = 'NOT_FOUND'


class ConflictError(AppError):
    """Raised when an operation finds conflicting data."""

    default_code = 'CONFLICT'


class UnauthorizedError(AppError):
    """Raised when authentication fails or is missing."""

    default_code = 'UNAUTHORIZED'


class ForbiddenError(AppError):
    """Raised when the caller is not allowed to perform an action."""

    default_code = 'FORBIDDEN'
```

- [ ] **Step 4: Incluir `code` nos handlers**

Em `src/dojoflow/api/exception_handlers.py`, em cada um dos quatro handlers trocar `content={'detail': str(exc)}` por:

```python
        content={'detail': str(exc), 'code': exc.code},
```

- [ ] **Step 5: Rodar os testes**

Run: `poetry run pytest -q`
Expected: tudo passando. Se algum teste antigo comparava o corpo inteiro só com `detail`, atualizar a asserção para incluir `code`.

- [ ] **Step 6: Commit**

```bash
git add src tests
git commit -m "feat: add machine-readable error codes to API errors"
```

---

### Task 6: `role` no access token

**Files:**
- Modify: `src/dojoflow/services/security.py`
- Modify: `src/dojoflow/api/dependencies/auth.py:51-95`
- Test: `tests/services/test_security.py`

**Interfaces:**
- Produces: `create_access_token(master_id: int) -> str` agora inclui `'role': 'master'`. `decode_token(token, *, expected_purpose, expected_role: str | None = None)`; `get_master_id_from_token(token, *, expected_purpose, expected_role: str | None = None) -> int`. Constante `MASTER_ROLE = 'master'`.

- [ ] **Step 1: Escrever os testes**

`tests/services/test_security.py`:

```python
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from dojoflow.core.settings import settings
from dojoflow.services.security import (
    MASTER_ROLE,
    create_access_token,
    get_master_id_from_token,
)
from dojoflow.shared.exceptions import UnauthorizedError


def test_access_token_carries_master_role() -> None:
    token = create_access_token(42)

    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )

    assert payload['role'] == MASTER_ROLE
    assert get_master_id_from_token(
        token,
        expected_purpose='access',
        expected_role=MASTER_ROLE,
    ) == 42


def test_token_without_role_is_rejected() -> None:
    token = jwt.encode(
        {
            'sub': '42',
            'purpose': 'access',
            'exp': datetime.now(UTC) + timedelta(minutes=5),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(UnauthorizedError):
        get_master_id_from_token(
            token,
            expected_purpose='access',
            expected_role=MASTER_ROLE,
        )
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/services/test_security.py -v`
Expected: FAIL — `ImportError: cannot import name 'MASTER_ROLE'`.

- [ ] **Step 3: Implementar em `src/dojoflow/services/security.py`**

1. Adicionar `MASTER_ROLE = 'master'` abaixo de `TokenPurpose`.
2. `create_access_token` passa `extra_claims={'role': MASTER_ROLE}` para `_create_token`.
3. `decode_token` ganha o parâmetro `expected_role: str | None = None` e, depois da checagem de `purpose`:

```python
    if expected_role is not None and payload.get('role') != expected_role:
        raise UnauthorizedError('Invalid token role.')
```

4. `get_master_id_from_token` ganha `expected_role: str | None = None` e repassa para `decode_token`.

- [ ] **Step 4: Exigir o papel nas dependencies**

Em `src/dojoflow/api/dependencies/auth.py`, nas duas chamadas de `get_master_id_from_token` (`_get_current_master` e `_get_optional_current_master`), adicionar `expected_role=MASTER_ROLE` (import de `dojoflow.services.security`).

- [ ] **Step 5: Rodar os testes**

Run: `poetry run pytest -q`
Expected: tudo passando.

- [ ] **Step 6: Commit**

```bash
git add src tests
git commit -m "feat: add master role claim to access tokens"
```

---

### Task 7: Tabela `refresh_session`

**Files:**
- Create: `src/dojoflow/models/refresh_session.py`
- Modify: `src/dojoflow/models/__init__.py`
- Create: `migrations/versions/f9a0b1c2d3e4_create_refresh_session_table.py`
- Create: `src/dojoflow/repositories/refresh_session.py`
- Modify: `src/dojoflow/repositories/__init__.py`
- Test: `tests/repositories/__init__.py`, `tests/repositories/test_refresh_session_repository.py`

**Interfaces:**
- Produces: model `RefreshSession` (`master_id`, `token_hash`, `expires_at`, `revoked_at`, `replaced_by_id`). `RefreshSessionRepository` com `get_by_token_hash(token_hash: str) -> dict[str, Any] | None` e `revoke_all_for_master(master_id: int, revoked_at: datetime) -> None`.

- [ ] **Step 1: Escrever o teste**

`tests/repositories/__init__.py` vazio. `tests/repositories/test_refresh_session_repository.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import unit_of_work
from dojoflow.repositories.refresh_session import RefreshSessionRepository
from tests.helpers.onboarding import register_web


@pytest.mark.asyncio
async def test_revoke_all_for_master(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    response, _ = await register_web(client)
    master_id = response.json()['master']['master_id']
    repository = RefreshSessionRepository(db_session=db_session)
    expires_at = datetime.now(UTC) + timedelta(days=1)

    async with unit_of_work(db_session):
        for token_hash in ('a' * 64, 'b' * 64):
            await repository.create({
                'master_id': master_id,
                'token_hash': token_hash,
                'expires_at': expires_at,
            })

    async with unit_of_work(db_session):
        await repository.revoke_all_for_master(
            master_id=master_id,
            revoked_at=datetime.now(UTC),
        )

    record = await repository.get_by_token_hash('a' * 64)

    assert record is not None
    assert record['revoked_at'] is not None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/repositories -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dojoflow.repositories.refresh_session'`.

- [ ] **Step 3: Criar o model `src/dojoflow/models/refresh_session.py`**

```python
from datetime import datetime

from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    datetime_column,
    int_fk,
    str_column,
)
from dojoflow.models.base_model import BaseModel


class RefreshSession(BaseModel):
    __tablename__ = 'refresh_session'

    master_id: Mapped[int] = int_fk('master.id')
    token_hash: Mapped[str] = str_column(length=64, unique=True, index=True)
    expires_at: Mapped[datetime] = datetime_column()
    revoked_at: Mapped[datetime | None] = datetime_column(nullable=True)
    replaced_by_id: Mapped[int | None] = int_fk(
        'refresh_session.id',
        nullable=True,
    )
```

Registrar em `src/dojoflow/models/__init__.py` (import + `'RefreshSession'` no `__all__`, em ordem alfabética).

- [ ] **Step 4: Criar a migration `migrations/versions/f9a0b1c2d3e4_create_refresh_session_table.py`**

```python
"""refresh session table

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-10-13 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f9a0b1c2d3e4'
down_revision: Union[str, Sequence[str], None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'refresh_session',
        sa.Column('master_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replaced_by_id', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('public_id', sa.Uuid(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['master_id'],
            ['master.id'],
            name=op.f('fk_refresh_session_master_id_master'),
        ),
        sa.ForeignKeyConstraint(
            ['replaced_by_id'],
            ['refresh_session.id'],
            name=op.f('fk_refresh_session_replaced_by_id_refresh_session'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_session')),
    )
    op.create_index(
        op.f('ix_refresh_session_master_id'),
        'refresh_session',
        ['master_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_refresh_session_public_id'),
        'refresh_session',
        ['public_id'],
        unique=True,
    )
    op.create_index(
        op.f('ix_refresh_session_replaced_by_id'),
        'refresh_session',
        ['replaced_by_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_refresh_session_token_hash'),
        'refresh_session',
        ['token_hash'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_refresh_session_token_hash'),
        table_name='refresh_session',
    )
    op.drop_index(
        op.f('ix_refresh_session_replaced_by_id'),
        table_name='refresh_session',
    )
    op.drop_index(
        op.f('ix_refresh_session_public_id'),
        table_name='refresh_session',
    )
    op.drop_index(
        op.f('ix_refresh_session_master_id'),
        table_name='refresh_session',
    )
    op.drop_table('refresh_session')
```

- [ ] **Step 5: Criar o repositório `src/dojoflow/repositories/refresh_session.py`**

```python
from datetime import datetime
from typing import Any

from sqlalchemy import update

from dojoflow.models.refresh_session import RefreshSession
from dojoflow.repositories.base import BaseRepository


class RefreshSessionRepository(BaseRepository[RefreshSession]):
    async def get_by_token_hash(
        self,
        token_hash: str,
    ) -> dict[str, Any] | None:
        return await self.get_one(
            filters=[RefreshSession.token_hash == token_hash],
        )

    async def revoke_all_for_master(
        self,
        master_id: int,
        revoked_at: datetime,
    ) -> None:
        self._ensure_unit_of_work()

        await self.db_session.execute(
            update(RefreshSession)
            .where(
                RefreshSession.master_id == master_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
```

Registrar em `src/dojoflow/repositories/__init__.py`.

- [ ] **Step 6: Rodar o teste e conferir a migration**

Run: `poetry run pytest tests/repositories -v`
Expected: PASS.

Run: `poetry run alembic upgrade head && poetry run alembic downgrade -1 && poetry run alembic upgrade head`
Expected: sem erros (usa o `DATABASE_URL` do `.env`, banco de desenvolvimento).

Run: `poetry run alembic check`
Expected: `No new upgrade operations detected.`

- [ ] **Step 7: Commit**

```bash
git add src migrations tests
git commit -m "feat: add refresh_session table and repository"
```

---

### Task 8: Sessões de refresh com cookie, rotação, reuso e logout

**Files:**
- Modify: `src/dojoflow/services/security.py` (remover `create_refresh_token`; adicionar `generate_refresh_token`, `hash_refresh_token`)
- Modify: `src/dojoflow/schemas/auth.py`
- Modify: `src/dojoflow/services/auth.py`
- Modify: `src/dojoflow/api/dependencies/auth.py` (injetar `RefreshSessionRepository`)
- Modify: `src/dojoflow/api/routes/auth.py`
- Modify: `tests/api/test_auth.py` (asserções sobre `refresh_token` no corpo)
- Test: `tests/api/test_auth_sessions.py`

**Interfaces:**
- Consumes: `RefreshSessionRepository` (Task 7), `settings.cookie_secure` (Task 4).
- Produces:
  - `AuthTokenResponse(access_token: str, token_type: str = 'bearer', master: MasterContextRead)` — **sem** `refresh_token`.
  - `AuthResult(NamedTuple)`: `response: AuthTokenResponse`, `refresh_token: str`.
  - `AuthService.register/login/refresh/set_credentials` retornam `AuthResult`. `AuthService.refresh(refresh_token: str) -> AuthResult`. `AuthService.logout(refresh_token: str | None) -> None`. `AuthService.revoke_all_sessions(master_id: int) -> None`.
  - Constantes em `routes/auth.py`: `REFRESH_COOKIE_NAME = 'dojoflow_refresh'`, `REFRESH_COOKIE_PATH = '/api/v1/auth'`.
  - Constante em `services/auth.py`: `REFRESH_REUSE_GRACE_SECONDS = 30`.

**Regras:**
1. Login/register/set-credentials criam uma `refresh_session` (token aleatório; no banco só o SHA-256) e gravam o cookie.
2. Refresh com sessão ativa: revoga a atual, cria a nova (`replaced_by_id`), devolve novo access token e novo cookie.
3. Sessão expirada, inexistente ou revogada **sem** ter sido rotacionada (`replaced_by_id` nulo — logout ou "revogar todas"): 401 `REFRESH_TOKEN_INVALID`.
4. Sessão **rotacionada há até 30 s** (duas abas) e cuja sucessora não foi revogada por "revogar todas": cria uma sessão nova sem derrubar as outras.
5. Sessão rotacionada há mais de 30 s (token reapresentado = provável roubo): **revoga todas** as sessões do mestre e responde 401 `REFRESH_TOKEN_REUSED`. A revogação é commitada antes do erro.
6. Logout revoga a sessão do cookie (se houver) e apaga o cookie; é idempotente (204 sempre).

- [ ] **Step 1: Escrever os testes**

`tests/api/test_auth_sessions.py`:

```python
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.refresh_session import RefreshSession
from dojoflow.services.security import hash_refresh_token
from tests.helpers.onboarding import register_web

COOKIE = 'dojoflow_refresh'
REFRESH_URL = '/api/v1/auth/refresh'


def _use_cookie(client: AsyncClient, token: str) -> None:
    client.cookies.clear()
    client.cookies.set(COOKIE, token)


@pytest.mark.asyncio
async def test_register_sets_httponly_cookie_and_hides_token(
    client: AsyncClient,
) -> None:
    response, _ = await register_web(client)

    assert 'refresh_token' not in response.json()
    set_cookie = response.headers['set-cookie']
    assert f'{COOKIE}=' in set_cookie
    assert 'HttpOnly' in set_cookie
    assert 'Path=/api/v1/auth' in set_cookie
    assert 'samesite=lax' in set_cookie.lower()


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient) -> None:
    register_response, _ = await register_web(client)
    first_token = register_response.cookies[COOKIE]

    _use_cookie(client, first_token)
    response = await client.post(REFRESH_URL)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['access_token']
    assert response.cookies[COOKIE] != first_token


@pytest.mark.asyncio
async def test_refresh_without_cookie_is_unauthorized(
    client: AsyncClient,
) -> None:
    client.cookies.clear()

    response = await client.post(REFRESH_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['code'] == 'REFRESH_TOKEN_INVALID'


@pytest.mark.asyncio
async def test_concurrent_tab_reuse_within_grace_keeps_session(
    client: AsyncClient,
) -> None:
    register_response, _ = await register_web(client)
    old_token = register_response.cookies[COOKIE]

    _use_cookie(client, old_token)
    first = await client.post(REFRESH_URL)
    _use_cookie(client, old_token)
    second = await client.post(REFRESH_URL)

    assert first.status_code == HTTPStatus.OK
    assert second.status_code == HTTPStatus.OK

    _use_cookie(client, first.cookies[COOKIE])
    still_valid = await client.post(REFRESH_URL)

    assert still_valid.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_reuse_after_grace_revokes_every_session(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    register_response, _ = await register_web(client)
    old_token = register_response.cookies[COOKIE]

    _use_cookie(client, old_token)
    rotated = await client.post(REFRESH_URL)
    new_token = rotated.cookies[COOKIE]

    await db_session.execute(
        update(RefreshSession)
        .where(RefreshSession.token_hash == hash_refresh_token(old_token))
        .values(revoked_at=datetime.now(UTC) - timedelta(minutes=5))
    )
    await db_session.commit()

    _use_cookie(client, old_token)
    reused = await client.post(REFRESH_URL)

    assert reused.status_code == HTTPStatus.UNAUTHORIZED
    assert reused.json()['code'] == 'REFRESH_TOKEN_REUSED'

    _use_cookie(client, new_token)
    after = await client.post(REFRESH_URL)

    assert after.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookie(
    client: AsyncClient,
) -> None:
    register_response, _ = await register_web(client)
    token = register_response.cookies[COOKIE]

    _use_cookie(client, token)
    logout = await client.post('/api/v1/auth/logout')

    assert logout.status_code == HTTPStatus.NO_CONTENT
    assert f'{COOKIE}=""' in logout.headers['set-cookie']

    _use_cookie(client, token)
    response = await client.post(REFRESH_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_logout_without_cookie_is_noop(client: AsyncClient) -> None:
    client.cookies.clear()

    response = await client.post('/api/v1/auth/logout')

    assert response.status_code == HTTPStatus.NO_CONTENT
```

Em `tests/api/test_auth.py`:
- em `test_register_web_should_create_academy_and_master_without_telegram`, trocar `assert body['refresh_token']` por `assert response.cookies['dojoflow_refresh']`;
- apagar `test_refresh_token` (coberto por `test_refresh_rotates_token`).

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_auth_sessions.py -v`
Expected: FAIL — `ImportError: cannot import name 'hash_refresh_token'`.

- [ ] **Step 3: Funções de token em `src/dojoflow/services/security.py`**

Remover `create_refresh_token` e `'refresh'` de `TokenPurpose`. Adicionar (com `import hashlib` e `import secrets` no topo):

```python
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode()).hexdigest()
```

- [ ] **Step 4: Schemas em `src/dojoflow/schemas/auth.py`**

Remover `AuthRefreshRequest`. Trocar `AuthTokenResponse` e adicionar `AuthResult` (import `from typing import NamedTuple`):

```python
class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    master: MasterContextRead


class AuthResult(NamedTuple):
    response: AuthTokenResponse
    refresh_token: str
```

- [ ] **Step 5: Sessões em `src/dojoflow/services/auth.py`**

1. O construtor recebe também `refresh_session_repository: RefreshSessionRepository`.
2. Imports: `generate_refresh_token`, `hash_refresh_token` (em vez de `create_refresh_token`), `AuthResult`, `RefreshSessionRepository`.
3. Constante no topo: `REFRESH_REUSE_GRACE_SECONDS = 30`.
4. `register`, `login` e `set_credentials` passam a terminar com `return await self._start_session(context)` (tipo de retorno `AuthResult`).
5. Substituir `refresh`, `_build_token_response` e adicionar os métodos abaixo:

```python
    async def refresh(self, refresh_token: str) -> AuthResult:
        session = await self.refresh_session_repository.get_by_token_hash(
            hash_refresh_token(refresh_token)
        )
        now = datetime.now(UTC)

        if session is None or session['expires_at'] <= now:
            raise UnauthorizedError(
                'Invalid or expired token.',
                code='REFRESH_TOKEN_INVALID',
            )

        if session['revoked_at'] is None:
            return await self._rotate_session(session)

        if session['replaced_by_id'] is None:
            raise UnauthorizedError(
                'Invalid or expired token.',
                code='REFRESH_TOKEN_INVALID',
            )

        master_id = int(session['master_id'])
        grace = timedelta(seconds=REFRESH_REUSE_GRACE_SECONDS)

        if now - session['revoked_at'] > grace:
            await self.revoke_all_sessions(master_id)
            raise UnauthorizedError(
                'Refresh token was already used.',
                code='REFRESH_TOKEN_REUSED',
            )

        successor = await self.refresh_session_repository.get_by_id(
            int(session['replaced_by_id'])
        )

        if (
            successor is None
            or successor['revoked_at'] is not None
            and successor['replaced_by_id'] is None
        ):
            raise UnauthorizedError(
                'Invalid or expired token.',
                code='REFRESH_TOKEN_INVALID',
            )

        return await self._start_session_for_master(master_id)

    @transactional
    async def logout(self, refresh_token: str | None) -> None:
        if refresh_token is None:
            return

        session = await self.refresh_session_repository.get_by_token_hash(
            hash_refresh_token(refresh_token)
        )

        if session is None or session['revoked_at'] is not None:
            return

        await self.refresh_session_repository.update_by_id(
            record_id=int(session['id']),
            data={'revoked_at': datetime.now(UTC)},
        )

    @transactional
    async def revoke_all_sessions(self, master_id: int) -> None:
        await self.refresh_session_repository.revoke_all_for_master(
            master_id=master_id,
            revoked_at=datetime.now(UTC),
        )

    @transactional
    async def _rotate_session(self, session: dict[str, Any]) -> AuthResult:
        result, new_session_id = await self._create_session(
            int(session['master_id'])
        )

        await self.refresh_session_repository.update_by_id(
            record_id=int(session['id']),
            data={
                'revoked_at': datetime.now(UTC),
                'replaced_by_id': new_session_id,
            },
        )

        return result

    @transactional
    async def _start_session_for_master(self, master_id: int) -> AuthResult:
        result, _ = await self._create_session(master_id)

        return result

    async def _start_session(self, context: MasterContextRead) -> AuthResult:
        return await self._start_session_for_master(context.master_id)

    async def _create_session(self, master_id: int) -> tuple[AuthResult, int]:
        context = await self.master_service.get_context_by_id(master_id)

        if context is None:
            raise UnauthorizedError(
                'Invalid or expired token.',
                code='REFRESH_TOKEN_INVALID',
            )

        refresh_token = generate_refresh_token()
        session_id = await self.refresh_session_repository.create({
            'master_id': master_id,
            'token_hash': hash_refresh_token(refresh_token),
            'expires_at': datetime.now(UTC)
            + timedelta(days=settings.JWT_REFRESH_TTL_DAYS),
        })

        response = AuthTokenResponse(
            access_token=create_access_token(master_id),
            master=context,
        )

        return AuthResult(response, refresh_token), session_id
```

`refresh` **não** é decorado: assim `revoke_all_sessions` commita sozinho antes do `raise` (regra 5). A checagem da sucessora (regra 4) impede que um token rotacionado há segundos "fure" um "revogar todas" feito logo depois (ex.: troca de senha). `register` e `login` também não precisam de `@transactional` — `_start_session_for_master` já é.

Adicionar `from typing import Any` e `AuthTokenResponse` aos imports, se faltarem.

- [ ] **Step 6: Injetar o repositório em `src/dojoflow/api/dependencies/auth.py`**

Seguindo o padrão de `_get_one_time_token_repository`, criar `_get_refresh_session_repository` + `RefreshSessionRepositoryDep` e passar `refresh_session_repository=refresh_session_repository_dep` em `_get_auth_service`.

Run: `grep -rn "AuthService(" src tests`
Expected: atualizar também a construção manual em `tests/api/test_auth.py` (`test_set_credentials_with_setup_token`), passando `refresh_session_repository=RefreshSessionRepository(db_session=db_session)`.

- [ ] **Step 7: Rotas com cookie em `src/dojoflow/api/routes/auth.py`**

Adicionar no topo (imports `from typing import Annotated` e `from fastapi import Cookie, Response`):

```python
REFRESH_COOKIE_NAME = 'dojoflow_refresh'
REFRESH_COOKIE_PATH = f'{settings.API_V1_PREFIX}/auth'

RefreshCookie = Annotated[
    str | None,
    Cookie(alias=REFRESH_COOKIE_NAME),
]


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.JWT_REFRESH_TTL_DAYS * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite='lax',
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite='lax',
    )
```

Cada rota que autentica recebe `response: Response`, chama o service, grava o cookie e devolve só o corpo. Exemplo (`login`; repetir o mesmo formato em `register` e `set_credentials`):

```python
@router.post(
    path='/login',
    status_code=status.HTTP_200_OK,
)
async def login(
    data: AuthLoginRequest,
    response: Response,
    auth_service_dep: AuthServiceDep,
) -> AuthTokenResponse:
    result = await auth_service_dep.login(data)
    _set_refresh_cookie(response, result.refresh_token)

    return result.response
```

Substituir a rota `refresh` e adicionar `logout`:

```python
@router.post(
    path='/refresh',
    status_code=status.HTTP_200_OK,
)
async def refresh(
    response: Response,
    auth_service_dep: AuthServiceDep,
    refresh_token: RefreshCookie = None,
) -> AuthTokenResponse:
    if refresh_token is None:
        raise UnauthorizedError(
            'Refresh token is missing.',
            code='REFRESH_TOKEN_INVALID',
        )

    result = await auth_service_dep.refresh(refresh_token)
    _set_refresh_cookie(response, result.refresh_token)

    return result.response


@router.post(
    path='/logout',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    response: Response,
    auth_service_dep: AuthServiceDep,
    refresh_token: RefreshCookie = None,
) -> None:
    await auth_service_dep.logout(refresh_token)
    _clear_refresh_cookie(response)
```

Imports: `from dojoflow.core.settings import settings`, `from dojoflow.shared.exceptions import UnauthorizedError`; remover `AuthRefreshRequest`.

- [ ] **Step 8: Rodar os testes**

Run: `poetry run pytest tests/api/test_auth_sessions.py tests/api/test_auth.py -v`
Expected: PASS. Se `test_logout_revokes_session_and_clears_cookie` falhar só no formato do `set-cookie` (o Starlette pode emitir `dojoflow_refresh=""` ou `dojoflow_refresh=;`), ajustar a asserção para `'Max-Age=0' in logout.headers['set-cookie']`.

Run: `poetry run pytest -q`
Expected: tudo passando.

- [ ] **Step 9: Commit**

```bash
git add src tests
git commit -m "feat: rotate refresh tokens in httpOnly cookie with reuse detection"
```

---

### Task 9: `set-credentials` exige a senha atual quando logado

**Files:**
- Modify: `src/dojoflow/schemas/auth.py` (`SetCredentialsRequest`)
- Modify: `src/dojoflow/services/auth.py` (`set_credentials`)
- Test: `tests/api/test_set_credentials.py`

**Interfaces:**
- Consumes: `AuthService.revoke_all_sessions`, `AuthService._start_session` (Task 8), `verify_password` (`services/security.py`), `MasterService.get_by_id(master_id) -> dict | None`.
- Produces: `SetCredentialsRequest.current_password: str | None`. Logado sem senha atual válida → `ForbiddenError(code='CURRENT_PASSWORD_INVALID')` (403). Sucesso → revoga todas as sessões e abre uma nova.

- [ ] **Step 1: Escrever os testes**

`tests/api/test_set_credentials.py`:

```python
from http import HTTPStatus

import pytest
from httpx import AsyncClient

from tests.helpers.onboarding import register_web

URL = '/api/v1/auth/set-credentials'
COOKIE = 'dojoflow_refresh'


async def _login(client: AsyncClient) -> tuple[dict[str, str], str]:
    response, _ = await register_web(client)
    token = response.json()['access_token']

    return {'Authorization': f'Bearer {token}'}, response.cookies[COOKIE]


@pytest.mark.asyncio
async def test_authenticated_without_current_password_is_forbidden(
    client: AsyncClient,
) -> None:
    headers, _ = await _login(client)

    response = await client.post(
        URL,
        headers=headers,
        json={'email': 'novo@dojoflow.test', 'password': 'nova-senha-123'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()['code'] == 'CURRENT_PASSWORD_INVALID'


@pytest.mark.asyncio
async def test_authenticated_with_wrong_current_password_is_forbidden(
    client: AsyncClient,
) -> None:
    headers, _ = await _login(client)

    response = await client.post(
        URL,
        headers=headers,
        json={
            'email': 'novo@dojoflow.test',
            'password': 'nova-senha-123',
            'current_password': 'senha-errada',
        },
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_password_change_revokes_old_sessions(
    client: AsyncClient,
) -> None:
    headers, old_refresh = await _login(client)

    response = await client.post(
        URL,
        headers=headers,
        json={
            'email': 'mestre@dojoflow.test',
            'password': 'nova-senha-123',
            'current_password': 'senha-segura',
        },
    )

    assert response.status_code == HTTPStatus.OK
    new_refresh = response.cookies[COOKIE]

    client.cookies.clear()
    client.cookies.set(COOKIE, old_refresh)
    old_attempt = await client.post('/api/v1/auth/refresh')

    client.cookies.clear()
    client.cookies.set(COOKIE, new_refresh)
    new_attempt = await client.post('/api/v1/auth/refresh')

    assert old_attempt.status_code == HTTPStatus.UNAUTHORIZED
    assert new_attempt.status_code == HTTPStatus.OK
```

(`register_web` usa `mestre@dojoflow.test` / `senha-segura` por padrão.)

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_set_credentials.py -v`
Expected: FAIL — os dois primeiros recebem 200.

- [ ] **Step 3: Implementar**

Em `SetCredentialsRequest`, adicionar:

```python
    current_password: str | None = Field(default=None, max_length=128)
```

Em `AuthService.set_credentials`, no ramo `if authenticated_master_id is not None:`, antes de `master_id = authenticated_master_id`:

```python
            master = await self.master_service.get_by_id(
                authenticated_master_id
            )
            password_hash = master.get('password_hash') if master else None

            if (
                password_hash is not None
                and (
                    data.current_password is None
                    or not verify_password(
                        data.current_password,
                        str(password_hash),
                    )
                )
            ):
                raise ForbiddenError(
                    'Current password is invalid.',
                    code='CURRENT_PASSWORD_INVALID',
                )
```

E no fim do método, entre o `master_service.set_credentials(...)` e o retorno:

```python
        await self.revoke_all_sessions(master_id)

        return await self._start_session(context)
```

Import `ForbiddenError`. (Mestre sem senha cadastrada — só Telegram — não tem senha atual para informar; por isso a checagem só vale quando `password_hash` existe.)

- [ ] **Step 4: Rodar os testes**

Run: `poetry run pytest tests/api/test_set_credentials.py tests/api/test_auth.py -v && poetry run pytest -q`
Expected: tudo passando.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "fix: require current password to change credentials when logged in"
```

---

### Task 10: Resolução de `public_id` e helpers de teste

**Files:**
- Create: `src/dojoflow/api/dependencies/public_ids.py`
- Create: `tests/helpers/auth.py`
- Test: `tests/api/test_public_ids.py`

**Interfaces:**
- Produces:
  - `resolve_public_id(db_session: AsyncSession, model: type[BaseModel], public_id: UUID, *, code: str, extra_filters: list[ColumnElement[bool]] | None = None) -> int` — lança `NotFoundError(code=code)`.
  - `StudentIdDep = Annotated[int, Depends(_resolve_student_id)]` — lê o path param `student_id: UUID` e filtra pela academia do mestre logado; código `STUDENT_NOT_FOUND`.
  - `resolve_modality_id(db_session, public_id: UUID) -> int` — código `MODALITY_NOT_FOUND` (catálogo global).
  - `tests/helpers/auth.py`: `auth_headers(client, **overrides) -> dict[str, str]` e `create_modality(db_session, name: str, emoji: str = '🥋') -> Modality`.

- [ ] **Step 1: Criar `tests/helpers/auth.py`**

```python
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.modality import Modality
from tests.helpers.onboarding import register_web


async def auth_headers(
    client: AsyncClient,
    **overrides: Any,
) -> dict[str, str]:
    response, _ = await register_web(client, **overrides)
    token = response.json()['access_token']

    return {'Authorization': f'Bearer {token}'}


async def create_modality(
    db_session: AsyncSession,
    name: str,
    emoji: str = '🥋',
) -> Modality:
    modality = Modality(name=name, emoji=emoji, is_active=True)
    db_session.add(modality)
    await db_session.commit()
    await db_session.refresh(modality)

    return modality
```

- [ ] **Step 2: Escrever o teste**

`tests/api/test_public_ids.py`:

```python
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.public_ids import resolve_public_id
from dojoflow.models.modality import Modality
from dojoflow.shared.exceptions import NotFoundError
from tests.helpers.auth import create_modality


@pytest.mark.asyncio
async def test_resolves_existing_public_id(db_session: AsyncSession) -> None:
    modality = await create_modality(db_session, 'Judô')

    resolved = await resolve_public_id(
        db_session,
        Modality,
        modality.public_id,
        code='MODALITY_NOT_FOUND',
    )

    assert resolved == modality.id


@pytest.mark.asyncio
async def test_unknown_public_id_raises_with_code(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(NotFoundError) as error:
        await resolve_public_id(
            db_session,
            Modality,
            uuid.uuid4(),
            code='MODALITY_NOT_FOUND',
        )

    assert error.value.code == 'MODALITY_NOT_FOUND'
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_public_ids.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Implementar `src/dojoflow/api/dependencies/public_ids.py`**

```python
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.models.base_model import BaseModel
from dojoflow.models.modality import Modality
from dojoflow.models.student import Student
from dojoflow.shared.exceptions import NotFoundError


async def resolve_public_id(
    db_session: AsyncSession,
    model: type[BaseModel],
    public_id: UUID,
    *,
    code: str,
    extra_filters: list[ColumnElement[bool]] | None = None,
) -> int:
    stmt = select(model.id).where(model.public_id == public_id)

    for condition in extra_filters or []:
        stmt = stmt.where(condition)

    internal_id = await db_session.scalar(stmt)

    if internal_id is None:
        raise NotFoundError(
            f'Could not find {model.__name__}.',
            code=code,
        )

    return internal_id


async def resolve_modality_id(
    db_session: AsyncSession,
    public_id: UUID,
) -> int:
    return await resolve_public_id(
        db_session,
        Modality,
        public_id,
        code='MODALITY_NOT_FOUND',
    )


async def _resolve_student_id(
    student_id: UUID,
    current_master: CurrentMasterDep,
    db_session_dep: DbSessionDep,
) -> int:
    return await resolve_public_id(
        db_session_dep,
        Student,
        student_id,
        code='STUDENT_NOT_FOUND',
        extra_filters=[Student.academy_id == current_master.academy_id],
    )


StudentIdDep = Annotated[int, Depends(_resolve_student_id)]
```

- [ ] **Step 5: Rodar os testes**

Run: `poetry run pytest tests/api/test_public_ids.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src tests
git commit -m "feat: add public_id resolution dependencies"
```

---

### Task 11: Modalidades com `public_id`

**Files:**
- Modify: `src/dojoflow/schemas/modality.py` (adicionar `public_id`)
- Modify: `src/dojoflow/services/modality.py` (`list_selected_by_academy`, `list_academy_options`)
- Create: `src/dojoflow/schemas/modality_api.py`
- Rewrite: `src/dojoflow/api/routes/modalities.py`
- Delete: `tests/api/test_students_modalities.py` (o teste de aluno vai para a Task 12)
- Test: `tests/api/test_modalities_api.py`

**Interfaces:**
- Consumes: `resolve_modality_id` (Task 10), `auth_headers`, `create_modality` (Task 10).
- Produces: `ModalityRead.public_id: UUID`, `ModalityOptionRead.public_id: UUID` (internos, usados pelo bot com `id` int como antes). Schemas de API: `ModalityApiRead(id: UUID, name: str, emoji: str)`, `ModalityOptionApiRead(id: UUID, name: str, emoji: str, is_selected: bool)`, `ModalityToggleRead(is_selected: bool)`. Rota `PUT /academy/modalities/{modality_id}/toggle` com `modality_id: UUID`.

- [ ] **Step 1: Escrever os testes**

`tests/api/test_modalities_api.py`:

```python
import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality


@pytest.mark.asyncio
async def test_catalog_and_toggle_use_public_ids(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    modality = await create_modality(db_session, 'Jiu-Jitsu')
    public_id = str(modality.public_id)

    catalog = await client.get('/api/v1/modalities/catalog', headers=headers)

    assert catalog.status_code == HTTPStatus.OK
    assert catalog.json() == [
        {'id': public_id, 'name': 'Jiu-Jitsu', 'emoji': '🥋'}
    ]

    toggle = await client.put(
        f'/api/v1/academy/modalities/{public_id}/toggle',
        headers=headers,
    )

    assert toggle.status_code == HTTPStatus.OK
    assert toggle.json() == {'is_selected': True}

    options = await client.get('/api/v1/academy/modalities', headers=headers)

    assert options.json() == [
        {
            'id': public_id,
            'name': 'Jiu-Jitsu',
            'emoji': '🥋',
            'is_selected': True,
        }
    ]


@pytest.mark.asyncio
async def test_toggle_unknown_modality_is_not_found(
    client: AsyncClient,
) -> None:
    headers = await auth_headers(client)

    response = await client.put(
        f'/api/v1/academy/modalities/{uuid.uuid4()}/toggle',
        headers=headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'MODALITY_NOT_FOUND'


@pytest.mark.asyncio
async def test_toggle_with_integer_id_is_rejected(
    client: AsyncClient,
) -> None:
    headers = await auth_headers(client)

    response = await client.put(
        '/api/v1/academy/modalities/1/toggle',
        headers=headers,
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_modalities_api.py -v`
Expected: FAIL — o catálogo devolve `id` inteiro.

- [ ] **Step 3: `public_id` nos schemas internos e no service**

Em `src/dojoflow/schemas/modality.py`: adicionar `from uuid import UUID` e o campo `public_id: UUID` em `ModalityRead` e `ModalityOptionRead` (logo após `id`).

Em `src/dojoflow/services/modality.py`:
- em `list_selected_by_academy`, incluir `Modality.public_id` no `select(...)`;
- em `list_academy_options`, passar `public_id=modality.public_id` ao montar `ModalityOptionRead`.

Run: `grep -rn "ModalityOptionRead(\|ModalityRead(" src tests`
Expected: todo ponto que constrói esses schemas passa `public_id` (ajustar os que faltarem).

- [ ] **Step 4: Criar `src/dojoflow/schemas/modality_api.py`**

```python
from uuid import UUID

from pydantic import BaseModel

from dojoflow.schemas.modality import ModalityOptionRead, ModalityRead


class ModalityApiRead(BaseModel):
    id: UUID
    name: str
    emoji: str

    @classmethod
    def from_internal(cls, modality: ModalityRead) -> 'ModalityApiRead':
        return cls(
            id=modality.public_id,
            name=modality.name,
            emoji=modality.emoji,
        )


class ModalityOptionApiRead(BaseModel):
    id: UUID
    name: str
    emoji: str
    is_selected: bool

    @classmethod
    def from_internal(
        cls,
        option: ModalityOptionRead,
    ) -> 'ModalityOptionApiRead':
        return cls(
            id=option.public_id,
            name=option.name,
            emoji=option.emoji,
            is_selected=option.is_selected,
        )


class ModalityToggleRead(BaseModel):
    is_selected: bool
```

- [ ] **Step 5: Reescrever `src/dojoflow/api/routes/modalities.py`**

```python
from uuid import UUID

from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.modality import ModalityServiceDep
from dojoflow.api.dependencies.public_ids import resolve_modality_id
from dojoflow.schemas.modality_api import (
    ModalityApiRead,
    ModalityOptionApiRead,
    ModalityToggleRead,
)

router = APIRouter(tags=['Modalities'])


@router.get(
    path='/modalities/catalog',
    status_code=status.HTTP_200_OK,
)
async def list_modality_catalog(
    current_master: CurrentMasterDep,
    modality_service_dep: ModalityServiceDep,
) -> list[ModalityApiRead]:
    modalities = await modality_service_dep.list_catalog()

    return [ModalityApiRead.from_internal(item) for item in modalities]


@router.get(
    path='/academy/modalities',
    status_code=status.HTTP_200_OK,
)
async def list_academy_modalities(
    current_master: CurrentMasterDep,
    modality_service_dep: ModalityServiceDep,
) -> list[ModalityOptionApiRead]:
    options = await modality_service_dep.list_academy_options(
        current_master.academy_id
    )

    return [ModalityOptionApiRead.from_internal(item) for item in options]


@router.put(
    path='/academy/modalities/{modality_id}/toggle',
    status_code=status.HTTP_200_OK,
)
async def toggle_academy_modality(
    modality_id: UUID,
    current_master: CurrentMasterDep,
    modality_service_dep: ModalityServiceDep,
    db_session_dep: DbSessionDep,
) -> ModalityToggleRead:
    internal_id = await resolve_modality_id(db_session_dep, modality_id)
    is_selected = await modality_service_dep.toggle_academy_modality(
        academy_id=current_master.academy_id,
        modality_id=internal_id,
    )

    return ModalityToggleRead(is_selected=is_selected)
```

- [ ] **Step 6: Apagar o teste antigo e rodar**

Apagar `tests/api/test_students_modalities.py` (o fluxo de alunos é reescrito na Task 12).

Run: `poetry run pytest tests/api/test_modalities_api.py -v && poetry run pytest -q`
Expected: tudo passando.

- [ ] **Step 7: Commit**

```bash
git add -A src tests
git commit -m "feat: expose modalities by public_id"
```

---

### Task 12: Alunos e matrículas com `public_id` e ficha tipada

**Files:**
- Modify: `src/dojoflow/schemas/student.py` (`due_day` até 28)
- Modify: `src/dojoflow/schemas/enrollment.py` (`due_day` até 28)
- Create: `src/dojoflow/schemas/student_api.py`
- Modify: `src/dojoflow/services/student.py` (ids públicos nos detalhes; `add_enrollment`; `update_enrollment_by_id`; `_get_student_or_fail` com código)
- Rewrite: `src/dojoflow/api/routes/students.py`
- Test: `tests/api/test_students_api.py`

**Interfaces:**
- Consumes: `StudentIdDep`, `resolve_public_id`, `resolve_modality_id` (Task 10); `auth_headers`, `create_modality` (Task 10).
- Produces:
  - Schemas: `StudentApiRead`, `AddressApiRead`, `EnrollmentApiRead`, `ResponsibleLinkApiRead`, `StudentDetailRead`, `EnrollmentApiPayload`, `StudentCreateApiRequest`, `EnrollmentApiUpdateRequest` (definidos no Step 3).
  - `StudentService.add_enrollment(academy_id: int, student_id: int, data: StudentEnrollmentPayload) -> None` — `ConflictError(code='ENROLLMENT_ALREADY_EXISTS')` se já houver matrícula na modalidade.
  - `StudentService.update_enrollment_by_id(academy_id: int, student_id: int, enrollment_id: int, data: dict[str, Any]) -> None`.
  - Rotas: `POST /students`, `GET /students/{student_id}`, `PATCH /students/{student_id}`, `PUT|DELETE /students/{student_id}/address`, `POST /students/{student_id}/responsibles`, `POST /students/{student_id}/enrollments`, `PATCH /students/{student_id}/enrollments/{enrollment_id}`. As rotas antigas `PATCH /students/{id}/modality` e `PATCH /students/{id}/enrollment` (que editavam "a primeira matrícula") são **removidas** — trocar de modalidade passa a ser: inativar uma matrícula e adicionar outra, o que preserva o histórico para as cobranças da V2. A listagem `GET /students` é reescrita na Task 13.

- [ ] **Step 1: Escrever os testes**

`tests/api/test_students_api.py`:

```python
import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality


async def _enable_modality(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict[str, str],
    name: str,
) -> str:
    modality = await create_modality(db_session, name)
    public_id = str(modality.public_id)
    await client.put(
        f'/api/v1/academy/modalities/{public_id}/toggle',
        headers=headers,
    )

    return public_id


def _create_payload(modality_id: str, **enrollment: object) -> dict:
    return {
        'name': 'Ana Lima',
        'phone': '62999990001',
        'phone_is_whatsapp': True,
        'sex': 'female',
        'enrollment': {
            'modality_id': modality_id,
            'monthly_fee': '150.00',
            'due_day': 10,
            **enrollment,
        },
        'address': {
            'zip_code': '74000000',
            'street': 'Rua A',
            'city': 'Goiânia',
            'state': 'GO',
            'number': '10',
        },
        'responsibles': [
            {
                'name': 'Maria Lima',
                'phone': '62999990002',
                'phone_is_whatsapp': True,
                'relationship': 'mother',
            }
        ],
    }


@pytest.mark.asyncio
async def test_create_and_read_student_detail_with_public_ids(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    jiu_jitsu = await _enable_modality(client, db_session, headers, 'Jiu')

    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json=_create_payload(jiu_jitsu),
    )

    assert created.status_code == HTTPStatus.CREATED
    student_id = created.json()['id']
    uuid.UUID(student_id)

    detail = await client.get(
        f'/api/v1/students/{student_id}',
        headers=headers,
    )

    assert detail.status_code == HTTPStatus.OK
    body = detail.json()
    assert body['student']['id'] == student_id
    assert body['address']['city'] == 'Goiânia'
    assert body['responsibles'][0]['relationship'] == 'mother'
    uuid.UUID(body['responsibles'][0]['id'])
    enrollment = body['enrollments'][0]
    assert enrollment['modality_id'] == jiu_jitsu
    assert enrollment['modality_name'] == 'Jiu'
    assert enrollment['monthly_fee'] == '150.00'
    uuid.UUID(enrollment['id'])


@pytest.mark.asyncio
async def test_due_day_above_28_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    modality_id = await _enable_modality(client, db_session, headers, 'Judô')

    response = await client.post(
        '/api/v1/students',
        headers=headers,
        json=_create_payload(modality_id, due_day=31),
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_add_and_update_specific_enrollment(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    jiu_jitsu = await _enable_modality(client, db_session, headers, 'Jiu')
    judo = await _enable_modality(client, db_session, headers, 'Judô')
    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json=_create_payload(jiu_jitsu),
    )
    student_id = created.json()['id']

    added = await client.post(
        f'/api/v1/students/{student_id}/enrollments',
        headers=headers,
        json={'modality_id': judo, 'is_exempt': True},
    )
    duplicate = await client.post(
        f'/api/v1/students/{student_id}/enrollments',
        headers=headers,
        json={'modality_id': judo},
    )

    assert added.status_code == HTTPStatus.NO_CONTENT
    assert duplicate.status_code == HTTPStatus.CONFLICT
    assert duplicate.json()['code'] == 'ENROLLMENT_ALREADY_EXISTS'

    detail = await client.get(
        f'/api/v1/students/{student_id}',
        headers=headers,
    )
    judo_enrollment = next(
        item
        for item in detail.json()['enrollments']
        if item['modality_id'] == judo
    )

    updated = await client.patch(
        f'/api/v1/students/{student_id}/enrollments/{judo_enrollment["id"]}',
        headers=headers,
        json={'status': 'inactive'},
    )

    assert updated.status_code == HTTPStatus.NO_CONTENT

    after = await client.get(
        f'/api/v1/students/{student_id}',
        headers=headers,
    )
    statuses = {
        item['modality_id']: item['status']
        for item in after.json()['enrollments']
    }
    assert statuses == {jiu_jitsu: 'active', judo: 'inactive'}


@pytest.mark.asyncio
async def test_student_from_other_academy_is_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await auth_headers(client)
    modality_id = await _enable_modality(
        client, db_session, owner_headers, 'Jiu'
    )
    created = await client.post(
        '/api/v1/students',
        headers=owner_headers,
        json=_create_payload(modality_id),
    )
    other_headers = await auth_headers(
        client,
        email='outro@dojoflow.test',
        academy_name='Outra Academia',
    )

    response = await client.get(
        f'/api/v1/students/{created.json()["id"]}',
        headers=other_headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'STUDENT_NOT_FOUND'


@pytest.mark.asyncio
async def test_update_basic_data(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    modality_id = await _enable_modality(client, db_session, headers, 'Jiu')
    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json=_create_payload(modality_id),
    )
    student_id = created.json()['id']

    patched = await client.patch(
        f'/api/v1/students/{student_id}',
        headers=headers,
        json={'name': 'Ana Atualizada'},
    )
    detail = await client.get(
        f'/api/v1/students/{student_id}',
        headers=headers,
    )

    assert patched.status_code == HTTPStatus.NO_CONTENT
    assert detail.json()['student']['name'] == 'Ana Atualizada'


@pytest.mark.asyncio
async def test_students_require_auth(client: AsyncClient) -> None:
    response = await client.get(f'/api/v1/students/{uuid.uuid4()}')

    assert response.status_code == HTTPStatus.UNAUTHORIZED
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_students_api.py -v`
Expected: FAIL — a criação devolve `id` inteiro e `modality_id` UUID é recusado.

- [ ] **Step 3: Criar `src/dojoflow/schemas/student_api.py`**

```python
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from dojoflow.schemas.student import (
    StudentAddressPayload,
    StudentResponsiblePayload,
)
from dojoflow.shared.enums import (
    EnrollmentStatus,
    StudentResponsibleRelationship,
    StudentSex,
)

MIN_DUE_DAY = 1
MAX_DUE_DAY = 28


class StudentApiRead(BaseModel):
    id: UUID
    name: str
    phone: str | None
    phone_is_whatsapp: bool | None
    cpf: str | None
    instagram: str | None
    email: str | None
    birth_date: date | None
    sex: StudentSex | None
    created_at: datetime

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> 'StudentApiRead':
        fields = {
            name: record[name] for name in cls.model_fields if name != 'id'
        }

        return cls(id=record['public_id'], **fields)


class AddressApiRead(BaseModel):
    zip_code: str | None
    street: str | None
    neighborhood: str | None
    city: str | None
    state: str | None
    number: str | None
    complement: str | None


class EnrollmentApiRead(BaseModel):
    id: UUID
    modality_id: UUID
    modality_name: str
    status: EnrollmentStatus
    monthly_fee: Decimal | None
    due_day: int | None
    is_exempt: bool


class ResponsibleLinkApiRead(BaseModel):
    id: UUID
    responsible_id: UUID
    name: str
    phone: str | None
    phone_is_whatsapp: bool | None
    email: str | None
    relationship: StudentResponsibleRelationship


class StudentDetailRead(BaseModel):
    student: StudentApiRead
    address: AddressApiRead | None
    responsibles: list[ResponsibleLinkApiRead]
    enrollments: list[EnrollmentApiRead]

    @classmethod
    def from_details(cls, details: Mapping[str, Any]) -> 'StudentDetailRead':
        address = details['address']

        return cls(
            student=StudentApiRead.from_record(details['student']),
            address=AddressApiRead(**address) if address else None,
            responsibles=[
                ResponsibleLinkApiRead(
                    id=item['link_public_id'],
                    responsible_id=item['responsible_public_id'],
                    name=item['name'],
                    phone=item['phone'],
                    phone_is_whatsapp=item['phone_is_whatsapp'],
                    email=item['email'],
                    relationship=item['relationship'],
                )
                for item in details['responsibles']
            ],
            enrollments=[
                EnrollmentApiRead(
                    id=item['enrollment_public_id'],
                    modality_id=item['modality_public_id'],
                    modality_name=item['modality_name'],
                    status=item['status'],
                    monthly_fee=item['monthly_fee'],
                    due_day=item['due_day'],
                    is_exempt=item['is_exempt'],
                )
                for item in details['enrollments']
            ],
        )


class EnrollmentApiPayload(BaseModel):
    modality_id: UUID
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    due_day: int | None = Field(default=None, ge=MIN_DUE_DAY, le=MAX_DUE_DAY)
    is_exempt: bool = False
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class StudentCreateApiRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    phone_is_whatsapp: bool | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=11)
    instagram: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=255)
    birth_date: date | None = None
    sex: StudentSex | None = None
    enrollment: EnrollmentApiPayload
    address: StudentAddressPayload | None = None
    responsibles: list[StudentResponsiblePayload] = Field(
        default_factory=list
    )


class EnrollmentApiUpdateRequest(BaseModel):
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    due_day: int | None = Field(default=None, ge=MIN_DUE_DAY, le=MAX_DUE_DAY)
    is_exempt: bool | None = None
    status: EnrollmentStatus | None = None
```

`AddressApiRead(**address)` recebe o dict do repositório com colunas extras (`id`, `academy_id`…); o Pydantic ignora campos extras por padrão.

- [ ] **Step 4: Ajustar `due_day` interno para 1–28**

Em `src/dojoflow/schemas/student.py` (`StudentEnrollmentPayload`, `StudentEnrollmentUpdateRequest`) e `src/dojoflow/schemas/enrollment.py` (`EnrollmentCreate`), trocar `le=31` por `le=28`. Em `StudentEnrollmentPayload`, tornar `monthly_fee` e `due_day` opcionais, para aceitar matrícula isenta ou ainda sem configuração (gera "pendência de cadastro" no dashboard):

```python
class StudentEnrollmentPayload(BaseModel):
    modality_id: int = Field(gt=0)
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    due_day: int | None = Field(default=None, ge=1, le=28)
    is_exempt: bool = False
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
```

Run: `grep -rn "enrollment.monthly_fee\|enrollment.due_day" src/dojoflow`
Expected: conferir que nenhum ponto assume valor não nulo (o `EnrollmentCreate` já aceita `None`).

- [ ] **Step 5: Ids públicos e matrículas no `StudentService`**

Em `src/dojoflow/services/student.py`:

1. Em `_get_student_enrollments`, adicionar ao `select(...)`:

```python
                Enrollment.public_id.label('enrollment_public_id'),
                Modality.public_id.label('modality_public_id'),
```

2. Em `_get_student_responsibles`, adicionar ao `select(...)`:

```python
                StudentResponsible.public_id.label('link_public_id'),
                Responsible.public_id.label('responsible_public_id'),
```

3. Em `get_details` e `_get_student_or_fail`, passar `code='STUDENT_NOT_FOUND'` no `NotFoundError`. Em `_ensure_modality_belongs_to_academy`, passar `code='MODALITY_NOT_ENABLED'`.

4. Adicionar os métodos (após `update_enrollment`):

```python
    @transactional
    async def add_enrollment(
        self,
        academy_id: int,
        student_id: int,
        data: StudentEnrollmentPayload,
    ) -> None:
        await self._ensure_modality_belongs_to_academy(
            academy_id=academy_id,
            modality_id=data.modality_id,
        )

        already_enrolled = await self.enrollment_repository.exists(
            filters=[
                Enrollment.academy_id == academy_id,
                Enrollment.student_id == student_id,
                Enrollment.modality_id == data.modality_id,
            ],
        )

        if already_enrolled:
            raise ConflictError(
                'Student is already enrolled in this modality.',
                code='ENROLLMENT_ALREADY_EXISTS',
            )

        await self.enrollment_repository.create(
            EnrollmentCreate(
                academy_id=academy_id,
                student_id=student_id,
                modality_id=data.modality_id,
                monthly_fee=data.monthly_fee,
                due_day=data.due_day,
                is_exempt=data.is_exempt,
                status=data.status,
            )
        )

    @transactional
    async def update_enrollment_by_id(
        self,
        academy_id: int,
        student_id: int,
        enrollment_id: int,
        data: dict[str, Any],
    ) -> None:
        await self.enrollment_repository.get_one_or_fail(
            filters=[
                Enrollment.id == enrollment_id,
                Enrollment.academy_id == academy_id,
                Enrollment.student_id == student_id,
            ],
        )

        await self.enrollment_repository.update_by_id(
            record_id=enrollment_id,
            data=data,
        )
```

Import `ConflictError` de `dojoflow.shared.exceptions`.

- [ ] **Step 6: Reescrever `src/dojoflow/api/routes/students.py`**

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.public_ids import (
    StudentIdDep,
    resolve_modality_id,
    resolve_public_id,
)
from dojoflow.api.dependencies.student import StudentServiceDep
from dojoflow.models.enrollment import Enrollment
from dojoflow.schemas.student import (
    StudentAddressPayload,
    StudentBasicUpdateRequest,
    StudentCreateRequest,
    StudentEnrollmentPayload,
    StudentResponsiblePayload,
)
from dojoflow.schemas.student_api import (
    EnrollmentApiPayload,
    EnrollmentApiUpdateRequest,
    StudentApiRead,
    StudentCreateApiRequest,
    StudentDetailRead,
)

router = APIRouter(prefix='/students', tags=['Students'])


async def _to_internal_enrollment(
    db_session: AsyncSession,
    payload: EnrollmentApiPayload,
) -> StudentEnrollmentPayload:
    modality_id = await resolve_modality_id(db_session, payload.modality_id)

    return StudentEnrollmentPayload(
        modality_id=modality_id,
        **payload.model_dump(exclude={'modality_id'}),
    )


async def _resolve_enrollment_id(
    enrollment_id: UUID,
    student_id: StudentIdDep,
    db_session_dep: DbSessionDep,
) -> int:
    return await resolve_public_id(
        db_session_dep,
        Enrollment,
        enrollment_id,
        code='ENROLLMENT_NOT_FOUND',
        extra_filters=[Enrollment.student_id == student_id],
    )


EnrollmentIdDep = Annotated[int, Depends(_resolve_enrollment_id)]


@router.post(
    path='',
    status_code=http_status.HTTP_201_CREATED,
)
async def create_student(
    data: StudentCreateApiRequest,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    db_session_dep: DbSessionDep,
) -> StudentApiRead:
    enrollment = await _to_internal_enrollment(db_session_dep, data.enrollment)
    internal_request = StudentCreateRequest(
        **data.model_dump(exclude={'enrollment'}),
        enrollment=enrollment,
    )

    student = await student_service_dep.create_student(
        academy_id=current_master.academy_id,
        data=internal_request,
    )

    return StudentApiRead.from_record(student.model_dump())


@router.get(
    path='/{student_id}',
    status_code=http_status.HTTP_200_OK,
)
async def get_student_details(
    student_id: StudentIdDep,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> StudentDetailRead:
    details = await student_service_dep.get_details(
        academy_id=current_master.academy_id,
        student_id=student_id,
    )

    return StudentDetailRead.from_details(details)


@router.patch(
    path='/{student_id}',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def update_student_basic_data(
    student_id: StudentIdDep,
    data: StudentBasicUpdateRequest,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    payload = data.model_dump(exclude_unset=True)

    if not payload:
        return

    await student_service_dep.update_basic_data(
        academy_id=current_master.academy_id,
        student_id=student_id,
        data=payload,
    )


@router.put(
    path='/{student_id}/address',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def update_student_address(
    student_id: StudentIdDep,
    data: StudentAddressPayload,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    await student_service_dep.update_address(
        academy_id=current_master.academy_id,
        student_id=student_id,
        address_data=data.model_dump(),
    )


@router.delete(
    path='/{student_id}/address',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def remove_student_address(
    student_id: StudentIdDep,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    await student_service_dep.remove_address(
        academy_id=current_master.academy_id,
        student_id=student_id,
    )


@router.post(
    path='/{student_id}/responsibles',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def add_student_responsible(
    student_id: StudentIdDep,
    data: StudentResponsiblePayload,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    await student_service_dep.add_responsible(
        academy_id=current_master.academy_id,
        student_id=student_id,
        responsible_data=data.model_dump(mode='json'),
    )


@router.post(
    path='/{student_id}/enrollments',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def add_student_enrollment(
    student_id: StudentIdDep,
    data: EnrollmentApiPayload,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    db_session_dep: DbSessionDep,
) -> None:
    enrollment = await _to_internal_enrollment(db_session_dep, data)

    await student_service_dep.add_enrollment(
        academy_id=current_master.academy_id,
        student_id=student_id,
        data=enrollment,
    )


@router.patch(
    path='/{student_id}/enrollments/{enrollment_id}',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def update_student_enrollment(
    student_id: StudentIdDep,
    enrollment_id: EnrollmentIdDep,
    data: EnrollmentApiUpdateRequest,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
) -> None:
    payload = data.model_dump(exclude_unset=True)

    if not payload:
        return

    await student_service_dep.update_enrollment_by_id(
        academy_id=current_master.academy_id,
        student_id=student_id,
        enrollment_id=enrollment_id,
        data=payload,
    )
```

`StudentIdDep` é avaliado uma única vez por request, mesmo usado por `_resolve_enrollment_id` e pela rota (cache de dependencies do FastAPI).

- [ ] **Step 7: Rodar os testes**

Run: `poetry run pytest tests/api/test_students_api.py -v`
Expected: PASS.

Run: `poetry run pytest -q`
Expected: tudo passando (os testes do bot continuam usando os services com `int`). Se algum teste do bot comparava o dict de `get_details` por igualdade exata, incluir as chaves novas (`enrollment_public_id`, `modality_public_id`, `link_public_id`, `responsible_public_id`) na asserção.

- [ ] **Step 8: Commit**

```bash
git add -A src tests
git commit -m "feat: expose students and enrollments by public_id with typed detail"
```

---

### Task 13: Lista de alunos paginada com filtros

**Files:**
- Modify: `src/dojoflow/services/student.py` (`list_page`, `get_active_modality_names`)
- Modify: `src/dojoflow/schemas/student_api.py` (`StudentListItemRead`, `StudentPageRead`)
- Modify: `src/dojoflow/api/routes/students.py` (rota `GET ''`)
- Test: `tests/api/test_students_list.py`

**Interfaces:**
- Consumes: `resolve_public_id` (Task 10), `StudentApiRead` (Task 12).
- Produces:
  - `StudentService.list_page(academy_id: int, *, search: str | None, modality_id: int | None, status: EnrollmentStatus | None, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]`.
  - `StudentService.get_active_modality_names(academy_id: int, student_ids: list[int]) -> dict[int, list[str]]`.
  - `StudentListItemRead(StudentApiRead)` + `modalities: list[str]`; `StudentPageRead(items, total, page, page_size)`.
  - `GET /students?search=&modality_id=&status=&page=1&page_size=20`.

**Semântica dos filtros:**
- `search`: trecho do nome, sem diferenciar maiúsculas; `%` e `_` são literais.
- `modality_id`: alunos com **qualquer** matrícula nessa modalidade. UUID inexistente → página vazia.
- `status=active`: alunos com ao menos uma matrícula **ativa** (na modalidade, se filtrada).
- `status=inactive`: alunos **sem** matrícula ativa (na modalidade, se filtrada).
- Ordem: nome, depois id. Página além do fim → `items: []` com `total` correto.

- [ ] **Step 1: Escrever os testes**

`tests/api/test_students_list.py`:

```python
import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality

URL = '/api/v1/students'


async def _setup(
    client: AsyncClient,
    db_session: AsyncSession,
) -> tuple[dict[str, str], str, str]:
    headers = await auth_headers(client)
    ids = []

    for name in ('Jiu', 'Judô'):
        modality = await create_modality(db_session, name)
        ids.append(str(modality.public_id))
        await client.put(
            f'/api/v1/academy/modalities/{ids[-1]}/toggle',
            headers=headers,
        )

    return headers, ids[0], ids[1]


async def _student(
    client: AsyncClient,
    headers: dict[str, str],
    name: str,
    modality_id: str,
    status: str = 'active',
) -> str:
    response = await client.post(
        URL,
        headers=headers,
        json={
            'name': name,
            'enrollment': {'modality_id': modality_id, 'status': status},
        },
    )

    return response.json()['id']


@pytest.mark.asyncio
async def test_page_shape_order_and_modalities(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, jiu, _ = await _setup(client, db_session)
    await _student(client, headers, 'Bruno', jiu)
    await _student(client, headers, 'Ana', jiu)

    response = await client.get(URL, headers=headers)

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['total'] == 2
    assert body['page'] == 1
    assert body['page_size'] == 20
    assert [item['name'] for item in body['items']] == ['Ana', 'Bruno']
    assert body['items'][0]['modalities'] == ['Jiu']


@pytest.mark.asyncio
async def test_status_and_modality_filters(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, jiu, judo = await _setup(client, db_session)
    await _student(client, headers, 'Ativo Jiu', jiu)
    await _student(client, headers, 'Inativo Judo', judo, status='inactive')

    active = await client.get(
        URL, headers=headers, params={'status': 'active'}
    )
    inactive = await client.get(
        URL, headers=headers, params={'status': 'inactive'}
    )
    by_judo = await client.get(
        URL, headers=headers, params={'modality_id': judo}
    )

    assert [i['name'] for i in active.json()['items']] == ['Ativo Jiu']
    assert [i['name'] for i in inactive.json()['items']] == ['Inativo Judo']
    assert [i['name'] for i in by_judo.json()['items']] == ['Inativo Judo']


@pytest.mark.asyncio
async def test_search_treats_wildcards_literally(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, jiu, _ = await _setup(client, db_session)
    await _student(client, headers, 'Ana Lima', jiu)
    await _student(client, headers, 'Carla 100%', jiu)

    percent = await client.get(URL, headers=headers, params={'search': '%'})
    partial = await client.get(URL, headers=headers, params={'search': 'lim'})

    assert [i['name'] for i in percent.json()['items']] == ['Carla 100%']
    assert [i['name'] for i in partial.json()['items']] == ['Ana Lima']


@pytest.mark.asyncio
async def test_page_beyond_end_and_unknown_modality_are_empty(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, jiu, _ = await _setup(client, db_session)
    await _student(client, headers, 'Ana', jiu)

    beyond = await client.get(
        URL, headers=headers, params={'page': 5, 'page_size': 10}
    )
    unknown = await client.get(
        URL, headers=headers, params={'modality_id': str(uuid.uuid4())}
    )

    assert beyond.status_code == HTTPStatus.OK
    assert beyond.json()['items'] == []
    assert beyond.json()['total'] == 1
    assert unknown.status_code == HTTPStatus.OK
    assert unknown.json() == {
        'items': [],
        'total': 0,
        'page': 1,
        'page_size': 20,
    }
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_students_list.py -v`
Expected: FAIL — `GET /students` responde 405 (a rota de listagem saiu na Task 12).

- [ ] **Step 3: Implementar no `StudentService`**

Imports: `from sqlalchemy import exists, not_`. Adicionar:

```python
    async def list_page(  # noqa: PLR0913
        self,
        academy_id: int,
        *,
        search: str | None,
        modality_id: int | None,
        status: EnrollmentStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = [Student.academy_id == academy_id]

        if search:
            normalized = ' '.join(search.strip().split())
            escaped = (
                normalized.replace('\\', '\\\\')
                .replace('%', '\\%')
                .replace('_', '\\_')
            )
            filters.append(Student.name.ilike(f'%{escaped}%', escape='\\'))

        enrollment_filters = [
            Enrollment.student_id == Student.id,
            Enrollment.academy_id == academy_id,
        ]

        if modality_id is not None:
            enrollment_filters.append(Enrollment.modality_id == modality_id)
            filters.append(exists().where(*enrollment_filters))

        if status is not None:
            has_active = exists().where(
                *enrollment_filters,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
            filters.append(
                has_active
                if status == EnrollmentStatus.ACTIVE
                else not_(has_active)
            )

        total = await self.student_repository.count(filters=filters)
        students = await self.student_repository.list(
            filters=filters,
            order_by=[Student.name, Student.id],
            offset=(page - 1) * page_size,
            limit=page_size,
        )

        return students, total

    async def get_active_modality_names(
        self,
        academy_id: int,
        student_ids: list[int],
    ) -> dict[int, list[str]]:
        if not student_ids:
            return {}

        stmt = (
            select(Enrollment.student_id, Modality.name)
            .join(Modality, Modality.id == Enrollment.modality_id)
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.student_id.in_(student_ids),
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
            .order_by(Modality.name)
        )
        result = await self.db_session.execute(stmt)
        names: dict[int, list[str]] = {}

        for student_id, modality_name in result.all():
            names.setdefault(student_id, []).append(modality_name)

        return names
```

- [ ] **Step 4: Schemas de página em `src/dojoflow/schemas/student_api.py`**

```python
class StudentListItemRead(StudentApiRead):
    modalities: list[str]


class StudentPageRead(BaseModel):
    items: list[StudentListItemRead]
    total: int
    page: int
    page_size: int
```

- [ ] **Step 5: Rota de listagem em `src/dojoflow/api/routes/students.py`**

Imports: `from fastapi import Query`, `from sqlalchemy import select`, `from dojoflow.models.modality import Modality`, `from dojoflow.shared.enums import EnrollmentStatus`, e `StudentListItemRead`, `StudentPageRead`. Adicionar antes de `create_student`:

```python
@router.get(
    path='',
    status_code=http_status.HTTP_200_OK,
)
async def list_students(  # noqa: PLR0913, PLR0917
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    db_session_dep: DbSessionDep,
    search: str | None = Query(default=None, min_length=1, max_length=120),
    modality_id: UUID | None = None,
    status: EnrollmentStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> StudentPageRead:
    internal_modality_id = None

    if modality_id is not None:
        internal_modality_id = await db_session_dep.scalar(
            select(Modality.id).where(Modality.public_id == modality_id)
        )

        if internal_modality_id is None:
            return StudentPageRead(
                items=[], total=0, page=page, page_size=page_size
            )

    students, total = await student_service_dep.list_page(
        current_master.academy_id,
        search=search,
        modality_id=internal_modality_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    modality_names = await student_service_dep.get_active_modality_names(
        current_master.academy_id,
        [student['id'] for student in students],
    )

    return StudentPageRead(
        items=[
            StudentListItemRead(
                **StudentApiRead.from_record(student).model_dump(),
                modalities=modality_names.get(student['id'], []),
            )
            for student in students
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
```

O arquivo já importa `status as http_status` (Task 12), então o parâmetro de query `status` não conflita com os decorators.

- [ ] **Step 6: Rodar os testes**

Run: `poetry run pytest tests/api/test_students_list.py tests/api/test_students_api.py -v && poetry run pytest -q`
Expected: tudo passando.

- [ ] **Step 7: Commit**

```bash
git add src tests
git commit -m "feat: paginate and filter student list"
```

---

### Task 14: Remover vínculo de responsável

**Files:**
- Modify: `src/dojoflow/api/routes/students.py`
- Test: `tests/api/test_students_responsibles.py`

**Interfaces:**
- Consumes: `StudentIdDep`, `resolve_public_id` (Task 10); `StudentService.remove_responsible_link(academy_id, student_id, student_responsible_id)` (já existe); `ResponsibleLinkApiRead.id` = `public_id` do `StudentResponsible` (Task 12).
- Produces: `DELETE /students/{student_id}/responsibles/{link_id}` → 204; `link_id` desconhecido → 404 `RESPONSIBLE_LINK_NOT_FOUND`.

- [ ] **Step 1: Escrever o teste**

`tests/api/test_students_responsibles.py`:

```python
import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality


@pytest.mark.asyncio
async def test_remove_responsible_link(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    modality = await create_modality(db_session, 'Jiu')
    await client.put(
        f'/api/v1/academy/modalities/{modality.public_id}/toggle',
        headers=headers,
    )
    created = await client.post(
        '/api/v1/students',
        headers=headers,
        json={
            'name': 'Davi Rocha',
            'enrollment': {'modality_id': str(modality.public_id)},
            'responsibles': [
                {
                    'name': 'Paula Rocha',
                    'phone': '62999990003',
                    'relationship': 'mother',
                }
            ],
        },
    )
    student_id = created.json()['id']
    detail = await client.get(
        f'/api/v1/students/{student_id}', headers=headers
    )
    link_id = detail.json()['responsibles'][0]['id']

    removed = await client.delete(
        f'/api/v1/students/{student_id}/responsibles/{link_id}',
        headers=headers,
    )
    missing = await client.delete(
        f'/api/v1/students/{student_id}/responsibles/{uuid.uuid4()}',
        headers=headers,
    )
    after = await client.get(
        f'/api/v1/students/{student_id}', headers=headers
    )

    assert removed.status_code == HTTPStatus.NO_CONTENT
    assert missing.status_code == HTTPStatus.NOT_FOUND
    assert missing.json()['code'] == 'RESPONSIBLE_LINK_NOT_FOUND'
    assert after.json()['responsibles'] == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_students_responsibles.py -v`
Expected: FAIL — 405 no `DELETE`.

- [ ] **Step 3: Implementar a rota**

Em `src/dojoflow/api/routes/students.py` (import `from dojoflow.models.student_responsible import StudentResponsible`):

```python
@router.delete(
    path='/{student_id}/responsibles/{link_id}',
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def remove_student_responsible(
    student_id: StudentIdDep,
    link_id: UUID,
    current_master: CurrentMasterDep,
    student_service_dep: StudentServiceDep,
    db_session_dep: DbSessionDep,
) -> None:
    internal_link_id = await resolve_public_id(
        db_session_dep,
        StudentResponsible,
        link_id,
        code='RESPONSIBLE_LINK_NOT_FOUND',
        extra_filters=[StudentResponsible.student_id == student_id],
    )

    await student_service_dep.remove_responsible_link(
        academy_id=current_master.academy_id,
        student_id=student_id,
        student_responsible_id=internal_link_id,
    )
```

- [ ] **Step 4: Rodar os testes**

Run: `poetry run pytest tests/api/test_students_responsibles.py -v && poetry run pytest -q`
Expected: tudo passando.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat: allow removing a student's responsible link"
```

---

### Task 15: Resumo do dashboard

**Files:**
- Create: `src/dojoflow/schemas/dashboard.py`
- Create: `src/dojoflow/services/dashboard.py`
- Create: `src/dojoflow/api/dependencies/dashboard.py`
- Create: `src/dojoflow/api/routes/dashboard.py`
- Modify: `src/dojoflow/main.py`
- Test: `tests/api/test_dashboard.py`

**Interfaces:**
- Produces: `GET /dashboard/summary` → `DashboardSummaryRead`:
  - `active_students: int` — alunos distintos com ao menos uma matrícula ativa;
  - `students_by_modality: list[ModalityCountRead(modality_id: UUID, modality_name: str, count: int)]` — só matrículas ativas, ordenado por `count` desc e nome;
  - `recent_enrollments: list[RecentEnrollmentRead(student_id: UUID, student_name: str, modality_name: str, created_at: datetime)]` — as 5 mais recentes, qualquer status;
  - `registration_pending: list[PendingEnrollmentRead(enrollment_id: UUID, student_id: UUID, student_name: str, modality_name: str)]` — matrículas ativas, não isentas, sem `monthly_fee` ou sem `due_day`.
  - `DashboardService(db_session).summary(academy_id: int) -> DashboardSummaryRead`.

- [ ] **Step 1: Escrever o teste**

`tests/api/test_dashboard.py`:

```python
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality


@pytest.mark.asyncio
async def test_dashboard_summary(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    jiu = await create_modality(db_session, 'Jiu')
    judo = await create_modality(db_session, 'Judô')

    for modality in (jiu, judo):
        await client.put(
            f'/api/v1/academy/modalities/{modality.public_id}/toggle',
            headers=headers,
        )

    async def student(name: str, modality_id: object, **enrollment: object):
        await client.post(
            '/api/v1/students',
            headers=headers,
            json={
                'name': name,
                'enrollment': {'modality_id': str(modality_id), **enrollment},
            },
        )

    await student('Ana', jiu.public_id, monthly_fee='150', due_day=10)
    await student('Bruno', jiu.public_id)
    await student('Carla', judo.public_id, is_exempt=True)
    await student('Davi', judo.public_id, status='inactive')

    response = await client.get(
        '/api/v1/dashboard/summary', headers=headers
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['active_students'] == 3
    assert [
        (item['modality_name'], item['count'])
        for item in body['students_by_modality']
    ] == [('Jiu', 2), ('Judô', 1)]
    assert [
        item['student_name'] for item in body['registration_pending']
    ] == ['Bruno']
    assert len(body['recent_enrollments']) == 4
    assert body['recent_enrollments'][0]['student_name'] == 'Davi'


@pytest.mark.asyncio
async def test_dashboard_isolated_per_academy(client: AsyncClient) -> None:
    headers = await auth_headers(client)

    response = await client.get(
        '/api/v1/dashboard/summary', headers=headers
    )

    assert response.json() == {
        'active_students': 0,
        'students_by_modality': [],
        'recent_enrollments': [],
        'registration_pending': [],
    }
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_dashboard.py -v`
Expected: FAIL — 404.

- [ ] **Step 3: Schemas `src/dojoflow/schemas/dashboard.py`**

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ModalityCountRead(BaseModel):
    modality_id: UUID
    modality_name: str
    count: int


class RecentEnrollmentRead(BaseModel):
    student_id: UUID
    student_name: str
    modality_name: str
    created_at: datetime


class PendingEnrollmentRead(BaseModel):
    enrollment_id: UUID
    student_id: UUID
    student_name: str
    modality_name: str


class DashboardSummaryRead(BaseModel):
    active_students: int
    students_by_modality: list[ModalityCountRead]
    recent_enrollments: list[RecentEnrollmentRead]
    registration_pending: list[PendingEnrollmentRead]
```

- [ ] **Step 4: Service `src/dojoflow/services/dashboard.py`**

```python
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.enrollment import Enrollment
from dojoflow.models.modality import Modality
from dojoflow.models.student import Student
from dojoflow.schemas.dashboard import (
    DashboardSummaryRead,
    ModalityCountRead,
    PendingEnrollmentRead,
    RecentEnrollmentRead,
)
from dojoflow.shared.enums import EnrollmentStatus

RECENT_ENROLLMENTS_LIMIT = 5


class DashboardService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def summary(self, academy_id: int) -> DashboardSummaryRead:
        return DashboardSummaryRead(
            active_students=await self._active_students(academy_id),
            students_by_modality=await self._by_modality(academy_id),
            recent_enrollments=await self._recent(academy_id),
            registration_pending=await self._pending(academy_id),
        )

    async def _active_students(self, academy_id: int) -> int:
        total = await self.db_session.scalar(
            select(func.count(distinct(Enrollment.student_id))).where(
                Enrollment.academy_id == academy_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )

        return int(total or 0)

    async def _by_modality(self, academy_id: int) -> list[ModalityCountRead]:
        count = func.count(distinct(Enrollment.student_id)).label('count')
        stmt = (
            select(
                Modality.public_id.label('modality_id'),
                Modality.name.label('modality_name'),
                count,
            )
            .join(Modality, Modality.id == Enrollment.modality_id)
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
            .group_by(Modality.public_id, Modality.name)
            .order_by(count.desc(), Modality.name)
        )
        result = await self.db_session.execute(stmt)

        return [ModalityCountRead(**row) for row in result.mappings()]

    async def _recent(self, academy_id: int) -> list[RecentEnrollmentRead]:
        stmt = (
            select(
                Student.public_id.label('student_id'),
                Student.name.label('student_name'),
                Modality.name.label('modality_name'),
                Enrollment.created_at,
            )
            .join(Student, Student.id == Enrollment.student_id)
            .join(Modality, Modality.id == Enrollment.modality_id)
            .where(Enrollment.academy_id == academy_id)
            .order_by(Enrollment.created_at.desc(), Enrollment.id.desc())
            .limit(RECENT_ENROLLMENTS_LIMIT)
        )
        result = await self.db_session.execute(stmt)

        return [RecentEnrollmentRead(**row) for row in result.mappings()]

    async def _pending(self, academy_id: int) -> list[PendingEnrollmentRead]:
        stmt = (
            select(
                Enrollment.public_id.label('enrollment_id'),
                Student.public_id.label('student_id'),
                Student.name.label('student_name'),
                Modality.name.label('modality_name'),
            )
            .join(Student, Student.id == Enrollment.student_id)
            .join(Modality, Modality.id == Enrollment.modality_id)
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Enrollment.is_exempt.is_(False),
                or_(
                    Enrollment.monthly_fee.is_(None),
                    Enrollment.due_day.is_(None),
                ),
            )
            .order_by(Student.name, Modality.name)
        )
        result = await self.db_session.execute(stmt)

        return [PendingEnrollmentRead(**row) for row in result.mappings()]
```

- [ ] **Step 5: Dependency e rota**

`src/dojoflow/api/dependencies/dashboard.py`:

```python
from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.services.dashboard import DashboardService


def _get_dashboard_service(db_session_dep: DbSessionDep) -> DashboardService:
    return DashboardService(db_session=db_session_dep)


DashboardServiceDep = Annotated[
    DashboardService,
    Depends(_get_dashboard_service),
]
```

`src/dojoflow/api/routes/dashboard.py`:

```python
from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.dashboard import DashboardServiceDep
from dojoflow.schemas.dashboard import DashboardSummaryRead

router = APIRouter(prefix='/dashboard', tags=['Dashboard'])


@router.get(
    path='/summary',
    status_code=status.HTTP_200_OK,
)
async def get_dashboard_summary(
    current_master: CurrentMasterDep,
    dashboard_service_dep: DashboardServiceDep,
) -> DashboardSummaryRead:
    return await dashboard_service_dep.summary(current_master.academy_id)
```

Em `src/dojoflow/main.py`: importar `router as dashboard_router` e `app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)`.

- [ ] **Step 6: Rodar os testes**

Run: `poetry run pytest tests/api/test_dashboard.py -v && poetry run pytest -q`
Expected: tudo passando. Se `recent_enrollments[0]` não for `Davi` porque os quatro `created_at` caíram no mesmo instante, o desempate por `Enrollment.id.desc()` resolve — conferir que ele está no `order_by`.

- [ ] **Step 7: Commit**

```bash
git add src tests
git commit -m "feat: add dashboard summary endpoint"
```

---

### Task 16: Consulta de CEP

**Files:**
- Create: `src/dojoflow/api/routes/cep.py`
- Modify: `src/dojoflow/main.py`
- Test: `tests/api/test_cep.py`

**Interfaces:**
- Consumes: `CepServiceDep` (já existe em `src/dojoflow/api/dependencies/telegram.py`), `CepAddress` (`integrations/cep/schemas.py`).
- Produces: `GET /cep/{zip_code}` (8 dígitos) → `CepAddress`; não encontrado → 404 `CEP_NOT_FOUND`; exige login.

- [ ] **Step 1: Escrever o teste**

`tests/api/test_cep.py`:

```python
from http import HTTPStatus

import pytest
from httpx import AsyncClient

from dojoflow.integrations.cep.client import CepClient
from dojoflow.integrations.cep.schemas import CepAddress
from tests.helpers.auth import auth_headers


@pytest.mark.asyncio
async def test_cep_found(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_search(self: CepClient, zip_code: str) -> CepAddress:
        return CepAddress(
            zip_code=zip_code,
            street='Rua A',
            neighborhood='Centro',
            city='Goiânia',
            state='GO',
            provider='fake',
        )

    monkeypatch.setattr(CepClient, 'search', fake_search)
    headers = await auth_headers(client)

    response = await client.get('/api/v1/cep/74000000', headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['city'] == 'Goiânia'


@pytest.mark.asyncio
async def test_cep_not_found(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_search(self: CepClient, zip_code: str) -> None:
        return None

    monkeypatch.setattr(CepClient, 'search', fake_search)
    headers = await auth_headers(client)

    response = await client.get('/api/v1/cep/74000000', headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'CEP_NOT_FOUND'


@pytest.mark.asyncio
async def test_cep_rejects_malformed_zip(client: AsyncClient) -> None:
    headers = await auth_headers(client)

    response = await client.get('/api/v1/cep/123', headers=headers)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/api/test_cep.py -v`
Expected: FAIL — 404 de rota inexistente sem `code`.

- [ ] **Step 3: Implementar `src/dojoflow/api/routes/cep.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Path, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.telegram import CepServiceDep
from dojoflow.integrations.cep.schemas import CepAddress
from dojoflow.shared.exceptions import NotFoundError

router = APIRouter(prefix='/cep', tags=['CEP'])


@router.get(
    path='/{zip_code}',
    status_code=status.HTTP_200_OK,
)
async def get_address_by_zip_code(
    zip_code: Annotated[str, Path(pattern=r'^\d{8}$')],
    current_master: CurrentMasterDep,
    cep_service_dep: CepServiceDep,
) -> CepAddress:
    address = await cep_service_dep.search(zip_code)

    if address is None:
        raise NotFoundError('Zip code not found.', code='CEP_NOT_FOUND')

    return address
```

Em `src/dojoflow/main.py`, incluir o router com o prefixo da API.

- [ ] **Step 4: Rodar os testes**

Run: `poetry run pytest tests/api/test_cep.py -v && poetry run pytest -q`
Expected: tudo passando.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat: add authenticated zip code lookup endpoint"
```

---

### Task 17: `/web` do bot envia link para definir acesso

**Files:**
- Modify: `src/dojoflow/services/telegram_webhook.py:177-197`
- Test: `tests/services/test_web_credentials_command.py`

**Interfaces:**
- Consumes: `settings.WEB_APP_URL` (Task 4); `AuthService.create_telegram_setup_token_for_master(master_id) -> TelegramSetupTokenResponse`.
- Produces: mensagem do bot contendo `{WEB_APP_URL}/definir-acesso?token={token}`; retorno `{'status': 'web_setup_token_sent'}` inalterado.

- [ ] **Step 1: Escrever o teste**

Seguir o padrão de envio de webhook e `fake_send_message` usado em `tests/api/test_auth.py::test_telegram_link_token_and_webhook_link`. Criar `tests/services/test_web_credentials_command.py`:

```python
from typing import Any

import pytest
from httpx import AsyncClient

from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.service import TelegramService
from tests.helpers.onboarding import register_onboarding


@pytest.mark.asyncio
async def test_web_command_sends_setup_link(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, 'TELEGRAM_WEBHOOK_SECRET', 'secret')
    monkeypatch.setattr(settings, 'WEB_APP_URL', 'https://app.dojoflow.test')
    sent: list[dict[str, Any]] = []

    async def fake_send_message(
        self: TelegramService,
        **kwargs: Any,
    ) -> dict[str, Any]:
        sent.append(kwargs)
        return {'ok': True}

    monkeypatch.setattr(TelegramService, 'send_message', fake_send_message)
    _, payload = await register_onboarding(client)
    telegram_user_id = payload['telegram_user_id']

    response = await client.post(
        '/api/v1/telegram/webhook',
        headers={'X-Telegram-Bot-Api-Secret-Token': 'secret'},
        json={
            'update_id': 1,
            'message': {
                'message_id': 1,
                'date': 0,
                'chat': {'id': telegram_user_id, 'type': 'private'},
                'from': {
                    'id': telegram_user_id,
                    'is_bot': False,
                    'first_name': 'Mestre',
                },
                'text': '/web',
            },
        },
    )

    assert response.json() == {'status': 'web_setup_token_sent'}
    text = sent[-1]['text']
    assert 'https://app.dojoflow.test/definir-acesso?token=' in text
    assert 'POST /api/v1/auth/set-credentials' not in text
```

Antes de rodar, conferir em `tests/api/test_auth.py` a assinatura real de `fake_send_message` e o formato do `TelegramUpdate` (`integrations/telegram/schemas.py`) e ajustar o payload/fake acima para o mesmo formato, se divergir.

- [ ] **Step 2: Rodar e ver falhar**

Run: `poetry run pytest tests/services/test_web_credentials_command.py -v`
Expected: FAIL — a mensagem não contém o link.

- [ ] **Step 3: Implementar**

Em `_process_web_credentials_command`, trocar o `text=` por:

```python
            text=(
                'Para criar ou redefinir seu acesso ao site, abra este link '
                f'(válido por {settings.JWT_TELEGRAM_SETUP_TTL_MINUTES} '
                'minutos):\n\n'
                f'{settings.WEB_APP_URL}/definir-acesso?token={setup.token}'
            ),
```

Import `from dojoflow.core.settings import settings`, se faltar. Se o `send_message` desse comando passa `parse_mode='Markdown'`, removê-lo nesta chamada (o `_` do token quebraria o Markdown).

- [ ] **Step 4: Rodar os testes**

Run: `poetry run pytest tests/services/test_web_credentials_command.py -v && poetry run pytest -q`
Expected: tudo passando.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "feat: send web access setup link from the /web bot command"
```

---

### Task 18: Contrato do OpenAPI

**Files:**
- Test: `tests/api/test_openapi_contract.py`
- Modify: rotas apontadas pelo teste (se houver)

**Interfaces:**
- Consumes: `app` (`dojoflow.main`).
- Produces: garantia de que toda rota usada pelo site (prefixo `/api/v1`, exceto `/api/v1/telegram/*` e `/api/v1/onboarding`) declara um schema de resposta com propriedades — nada de `dict[str, Any]`.

- [ ] **Step 1: Escrever o teste**

`tests/api/test_openapi_contract.py`:

```python
from dojoflow.main import app

EXCLUDED_PREFIXES = ('/api/v1/telegram', '/api/v1/onboarding')


def _is_untyped(schema: dict) -> bool:
    if not schema:
        return True

    if '$ref' in schema or schema.get('type') == 'array':
        return False

    return schema.get('type') == 'object' and 'properties' not in schema


def test_web_routes_declare_typed_responses() -> None:
    openapi = app.openapi()
    untyped = []

    for path, operations in openapi['paths'].items():
        if not path.startswith('/api/v1') or path.startswith(
            EXCLUDED_PREFIXES
        ):
            continue

        for method, operation in operations.items():
            for code, response in operation['responses'].items():
                if not code.startswith('2') or code == '204':
                    continue

                content = response.get('content', {})
                schema = content.get('application/json', {}).get('schema', {})

                if _is_untyped(schema):
                    untyped.append(f'{method.upper()} {path} -> {code}')

    assert untyped == []
```

- [ ] **Step 2: Rodar**

Run: `poetry run pytest tests/api/test_openapi_contract.py -v`
Expected: PASS. Se falhar, a mensagem lista as rotas sem tipo; para cada uma, criar um schema Pydantic de resposta e usá-lo como tipo de retorno da rota.

- [ ] **Step 3: Gerar e conferir o OpenAPI**

Run: `PYTHONPATH=src poetry run python -c "import json; from dojoflow.main import app; print(json.dumps(sorted(app.openapi()['paths'])))"`
Expected: a lista contém `/api/v1/auth/logout`, `/api/v1/dashboard/summary`, `/api/v1/cep/{zip_code}`, `/api/v1/students/{student_id}/enrollments/{enrollment_id}`, `/api/v1/students/{student_id}/responsibles/{link_id}` e **não** contém `/api/v1/masters/context/{telegram_user_id}`.

- [ ] **Step 4: Verificação final**

Run: `poetry run ruff check . && poetry run ruff format --check . && poetry run typos . && poetry run pytest -q`
Expected: tudo passando.

- [ ] **Step 5: Commit**

```bash
git add tests src
git commit -m "test: enforce typed responses on web API routes"
```

---

## Cobertura da spec

| Spec | Task |
|---|---|
| 4.1.1 `public_id` | 10, 11, 12, 13, 14 |
| 4.1.2 `role` no JWT | 6 |
| 4.1.3 `/portal/*` reservado | — (sem código) |
| 4.2.1 remover rota aberta | 4 |
| 4.2.2 refresh em cookie, rotação, reuso, logout | 7, 8 |
| 4.2.3 senha atual no `set-credentials` | 9 |
| 4.2.4 `ENVIRONMENT` + trava do segredo | 4 |
| 4.2.5 `compare_digest` | 4 |
| 4.3.1 respostas tipadas | 11, 12, 18 |
| 4.3.2 lista paginada | 13 |
| 4.3.3 remover responsável | 14 |
| 4.3.4 dashboard | 15 |
| 4.3.5 CEP | 16 |
| 4.3.6 códigos de erro | 5 |
| 4.3.7 `/web` envia link | 17 |
| 4.4.1 transações | 2 |
| 4.4.2 testes em Postgres | 1 |
| 7.1 testes do backend | todas |
| 7.3 CI do backend | 3 |
| Lacuna encontrada: várias matrículas por aluno | 12 (`POST`/`PATCH /enrollments`) |
