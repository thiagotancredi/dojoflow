import pytest
import pytest_asyncio
from httpx import AsyncClient

from dojoflow.core.settings import settings
from tests.helpers.auth import SEED, auth_headers


@pytest.fixture
def _admin_is_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    """O mestre fixo (SEED) é o administrador da plataforma."""
    monkeypatch.setattr(settings, 'ADMIN_EMAIL', SEED.email)


@pytest_asyncio.fixture
async def admin_headers(
    client: AsyncClient,
    _admin_is_seed: None,
) -> dict[str, str]:
    return await auth_headers(client)
