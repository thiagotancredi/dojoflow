import json
from decimal import Decimal

import httpx
import pytest

from dojoflow.integrations.infinitepay.client import (
    InfinitePayCheckoutDisabled,
    InfinitePayClient,
    InfinitePayKeyRejected,
    InfinitePayUnavailable,
)
from dojoflow.integrations.infinitepay.schemas import (
    CheckoutCustomer,
    CheckoutItem,
)

API_KEY = 'inchk_live_SUPERSECRET'
LINK_URL = 'https://checkout.infinitepay.io/katsuflow/abc'


def _client(handler) -> InfinitePayClient:
    return InfinitePayClient(transport=httpx.MockTransport(handler))


async def _create(client: InfinitePayClient, **overrides) -> str:
    kwargs = {
        'order_nsu': 'pedido-1',
        'items': [
            CheckoutItem(
                description='Mensalidade março/2027',
                quantity=1,
                price=Decimal('150.00'),
            )
        ],
        'customer': None,
        'redirect_url': 'https://katsuflow.com.br/pagar/tok',
        'webhook_url': 'https://katsuflow.com.br/api/v1/public/webhooks/infinitepay',
    }
    kwargs.update(overrides)
    return await client.create_link(API_KEY, **kwargs)


@pytest.mark.asyncio
async def test_create_link_sends_key_and_cents():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={'url': LINK_URL})

    url = await _create(_client(handler))

    assert url == LINK_URL
    request = seen[0]
    assert str(request.url) == 'https://api.checkout.infinitepay.io/links'
    assert request.method == 'POST'
    assert request.headers['X-Api-Key'] == API_KEY
    body = json.loads(request.content)
    assert body['order_nsu'] == 'pedido-1'
    assert body['items'] == [
        {
            'description': 'Mensalidade março/2027',
            'quantity': 1,
            'price': 15000,
        }
    ]
    assert 'customer' not in body
    assert body['redirect_url'] == 'https://katsuflow.com.br/pagar/tok'
    assert body['webhook_url'].endswith('/public/webhooks/infinitepay')


@pytest.mark.asyncio
async def test_create_link_sends_customer_without_empty_fields():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={'url': LINK_URL})

    await _create(
        _client(handler),
        customer=CheckoutCustomer(
            name='Ana Lima', phone_number='+5562999990000'
        ),
        webhook_url=None,
        redirect_url=None,
    )

    body = json.loads(seen[0].content)
    assert body['customer'] == {
        'name': 'Ana Lima',
        'phone_number': '+5562999990000',
    }
    assert 'webhook_url' not in body
    assert 'redirect_url' not in body


@pytest.mark.asyncio
async def test_create_link_forbidden_raises_key_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={'message': 'Forbidden'})

    with pytest.raises(InfinitePayKeyRejected) as error:
        await _create(_client(handler))

    assert API_KEY not in str(error.value)


@pytest.mark.asyncio
async def test_create_link_not_enabled_raises_checkout_disabled():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                'error': 'external_checkout_not_enabled',
                'message': 'External checkout is not enabled',
            },
        )

    with pytest.raises(InfinitePayCheckoutDisabled):
        await _create(_client(handler))


@pytest.mark.asyncio
async def test_create_link_timeout_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout('timeout', request=request)

    with pytest.raises(InfinitePayUnavailable) as error:
        await _create(_client(handler))

    assert API_KEY not in str(error.value)


@pytest.mark.asyncio
async def test_create_link_server_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text='Bad gateway')

    with pytest.raises(InfinitePayUnavailable):
        await _create(_client(handler))


@pytest.mark.asyncio
async def test_payment_check_paid():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                'success': True,
                'paid': True,
                'amount': 15000,
                'paid_amount': 15000,
                'capture_method': 'pix',
                'installments': 1,
            },
        )

    check = await _client(handler).payment_check(
        handle='katsuflow',
        order_nsu='pedido-1',
        transaction_nsu='tx-1',
        slug='b6JwL3ZmAt',
    )

    assert str(seen[0].url) == (
        'https://api.checkout.infinitepay.io/payment_check'
    )
    assert json.loads(seen[0].content) == {
        'handle': 'katsuflow',
        'order_nsu': 'pedido-1',
        'transaction_nsu': 'tx-1',
        'slug': 'b6JwL3ZmAt',
    }
    assert check.success is True
    assert check.paid is True
    # A InfinitePay fala em centavos; o Katsuflow, em reais
    assert check.amount == Decimal('150.00')
    assert check.paid_amount == Decimal('150.00')
    assert check.capture_method == 'pix'
    assert check.installments == 1


@pytest.mark.asyncio
async def test_payment_check_unknown_returns_not_paid():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'success': False})

    check = await _client(handler).payment_check(
        handle='katsuflow',
        order_nsu='pedido-1',
        transaction_nsu='inventada',
        slug='x',
    )

    assert check.success is False
    assert check.paid is False
    assert check.amount is None


@pytest.mark.asyncio
async def test_payment_check_network_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError('down', request=request)

    with pytest.raises(InfinitePayUnavailable):
        await _client(handler).payment_check(
            handle='katsuflow', order_nsu='p', transaction_nsu='t', slug='s'
        )


@pytest.mark.asyncio
async def test_create_link_other_403_is_unavailable_not_key_rejected():
    # Um 403 de firewall/CDN não pode desligar a academia como chave recusada
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text='<html>Access denied</html>')

    with pytest.raises(InfinitePayUnavailable):
        await _create(_client(handler))
