"""InfinitePay simulada nos testes: nenhum teste chama a API real."""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.api.dependencies.infinitepay import get_infinitepay_client
from dojoflow.core.crypto import encrypt_secret
from dojoflow.integrations.infinitepay.client import InfinitePayClient
from dojoflow.main import app
from dojoflow.models.academy_billing_settings import AcademyBillingSettings
from tests.helpers.auth import SEED

Handler = Callable[[httpx.Request], httpx.Response]


class FakeInfinitePay:
    """Guarda as requisições e responde com o que o teste pedir."""

    def __init__(self, handler: Handler | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.handler = handler or link_created()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.handler(request)

    def client(self) -> InfinitePayClient:
        return InfinitePayClient(transport=httpx.MockTransport(self))

    def bodies(self, path: str) -> list[dict]:
        return [
            json.loads(r.content) for r in self.requests if r.url.path == path
        ]


def link_created(
    url: str = 'https://checkout.infinitepay.io/katsuflow/link',
) -> Handler:
    return lambda request: httpx.Response(200, json={'url': url})


def key_rejected() -> Handler:
    return lambda request: httpx.Response(403, json={'message': 'Forbidden'})


def checkout_disabled() -> Handler:
    return lambda request: httpx.Response(
        404,
        json={
            'error': 'external_checkout_not_enabled',
            'message': 'External checkout is not enabled',
        },
    )


def unreachable() -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout('timeout', request=request)

    return handler


@contextmanager
def fake_infinitepay(
    handler: Handler | None = None,
) -> Iterator[FakeInfinitePay]:
    """A API passa a falar com a InfinitePay simulada."""
    fake = FakeInfinitePay(handler)
    app.dependency_overrides[get_infinitepay_client] = fake.client
    try:
        yield fake
    finally:
        app.dependency_overrides.pop(get_infinitepay_client, None)


API_KEY = 'inchk_live_SUPERSECRETkey9876'


async def enable_infinitepay(
    session: AsyncSession,
    academy_id: int | None = None,
    handle: str = 'katsuflow',
    enabled: bool = True,
) -> None:
    """Academia com a baixa automática ligada (direto no banco)."""
    await session.execute(
        insert(AcademyBillingSettings)
        .values(
            academy_id=academy_id or SEED.academy_id,
            infinitepay_handle=handle,
            infinitepay_api_key=encrypt_secret(API_KEY),
            infinitepay_enabled=enabled,
            infinitepay_tested_at=datetime.now(UTC),
        )
        .on_conflict_do_update(
            index_elements=[AcademyBillingSettings.academy_id],
            set_={
                'infinitepay_handle': handle,
                'infinitepay_api_key': encrypt_secret(API_KEY),
                'infinitepay_enabled': enabled,
            },
        )
    )
    await session.commit()


def payment_paid(
    amount_cents: int = 20000,
    method: str = 'pix',
    paid_cents: int | None = None,
) -> Handler:
    """payment_check confirma o pagamento."""
    return lambda request: httpx.Response(
        200,
        json={
            'success': True,
            'paid': True,
            'amount': amount_cents,
            'paid_amount': paid_cents
            if paid_cents is not None
            else amount_cents,
            'capture_method': method,
            'installments': 1,
        },
    )


def payment_not_found() -> Handler:
    return lambda request: httpx.Response(200, json={'success': False})
