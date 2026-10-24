"""Cliente HTTP da InfinitePay.

A chave de API vai só no header ``X-Api-Key``: nunca em mensagem de erro
nem em log.
"""

from decimal import Decimal
from http import HTTPStatus
from typing import Any

import httpx

from dojoflow.integrations.infinitepay.schemas import (
    CheckoutCustomer,
    CheckoutItem,
    PaymentCheck,
)

BASE_URL = 'https://api.checkout.infinitepay.io'
TIMEOUT_SECONDS = 5.0
CENTS = Decimal(100)


class InfinitePayError(Exception):
    """Falha ao falar com a InfinitePay."""


class InfinitePayKeyRejected(InfinitePayError):
    """HTTP 403: a chave de API não foi aceita."""


class InfinitePayCheckoutDisabled(InfinitePayError):
    """HTTP 404 external_checkout_not_enabled (também para tag inexistente)."""


class InfinitePayUnavailable(InfinitePayError):
    """Rede, tempo esgotado ou resposta inesperada: tentar de novo depois."""


def _to_cents(value: Decimal) -> int:
    return int((value * CENTS).to_integral_value())


def _to_reais(value: Any) -> Decimal | None:
    if value is None:
        return None
    return (Decimal(value) / CENTS).quantize(Decimal('0.01'))


class InfinitePayClient:
    def __init__(
        self, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._transport = transport

    async def _post(
        self, path: str, body: dict[str, Any], headers: dict[str, str]
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                return await client.post(path, json=body, headers=headers)
        except httpx.HTTPError as error:
            # Só o tipo do erro: a mensagem do httpx pode trazer a requisição
            raise InfinitePayUnavailable(
                f'InfinitePay unreachable ({type(error).__name__}).'
            ) from None

    async def create_link(  # noqa: PLR0913
        self,
        api_key: str,
        *,
        order_nsu: str,
        items: list[CheckoutItem],
        customer: CheckoutCustomer | None,
        redirect_url: str | None,
        webhook_url: str | None,
        handle: str | None = None,
    ) -> str:
        """Cria o link de checkout e devolve a URL dele.

        handle: a InfiniteTag; vai junto para a InfinitePay recusar uma tag
        que não é da conta (o payment_check depois usa essa tag).
        """
        body: dict[str, Any] = {
            'order_nsu': order_nsu,
            'items': [
                {
                    'description': item.description,
                    'quantity': item.quantity,
                    'price': _to_cents(item.price),
                }
                for item in items
            ],
        }
        if handle:
            body['handle'] = handle
        if customer is not None:
            body['customer'] = customer.model_dump(exclude_none=True)
        if redirect_url:
            body['redirect_url'] = redirect_url
        if webhook_url:
            body['webhook_url'] = webhook_url

        response = await self._post(
            '/links', body, headers={'X-Api-Key': api_key}
        )

        # Só o 403 da própria InfinitePay ({"message": "Forbidden"}) é chave
        # recusada; outro 403 (firewall, CDN) é falha passageira
        if (
            response.status_code == HTTPStatus.FORBIDDEN
            and _json(response).get('message') == 'Forbidden'
        ):
            raise InfinitePayKeyRejected('InfinitePay rejected the API key.')
        if response.status_code == HTTPStatus.NOT_FOUND and (
            _json(response).get('error') == 'external_checkout_not_enabled'
        ):
            raise InfinitePayCheckoutDisabled(
                'InfinitePay checkout is not enabled for this account.'
            )

        url = _json(response).get('url') if response.is_success else None
        if not isinstance(url, str) or not url:
            raise InfinitePayUnavailable(
                f'InfinitePay link not created (HTTP {response.status_code}).'
            )

        return url

    async def payment_check(
        self, *, handle: str, order_nsu: str, transaction_nsu: str, slug: str
    ) -> PaymentCheck:
        """Confere com a InfinitePay se o pagamento existe e foi pago."""
        response = await self._post(
            '/payment_check',
            {
                'handle': handle,
                'order_nsu': order_nsu,
                'transaction_nsu': transaction_nsu,
                'slug': slug,
            },
            headers={},
        )
        data = _json(response)

        if not response.is_success and 'success' not in data:
            raise InfinitePayUnavailable(
                f'InfinitePay payment_check failed '
                f'(HTTP {response.status_code}).'
            )

        return PaymentCheck(
            success=data.get('success') is True,
            paid=data.get('paid') is True,
            amount=_to_reais(data.get('amount')),
            paid_amount=_to_reais(data.get('paid_amount')),
            capture_method=data.get('capture_method'),
            installments=data.get('installments'),
        )


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}
