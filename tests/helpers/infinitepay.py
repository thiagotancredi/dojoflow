"""InfinitePay simulada nos testes: nenhum teste chama a API real."""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import httpx

from dojoflow.api.dependencies.infinitepay import get_infinitepay_client
from dojoflow.integrations.infinitepay.client import InfinitePayClient
from dojoflow.main import app

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
