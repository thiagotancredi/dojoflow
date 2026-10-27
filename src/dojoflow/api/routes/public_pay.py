from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from dojoflow.api.dependencies.billing import BillingServiceDep
from dojoflow.api.dependencies.infinitepay import InfinitePayServiceDep
from dojoflow.api.dependencies.rate_limit import (
    public_pay_limiter,
    webhook_limiter,
)
from dojoflow.schemas.infinitepay_api import (
    InfinitePayWebhookApi,
    PayConfirmApi,
    PayConfirmRead,
    WebhookAckRead,
)
from dojoflow.schemas.public_pay import PublicCheckoutRead, PublicPaymentRead
from dojoflow.shared.exceptions import NotFoundError
from dojoflow.worker import tasks

# Rotas sem login: quem tem o link abre (o código é o segredo)
router = APIRouter(prefix='/public', tags=['Public'])


@router.get(
    path='/pay/{token}',
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(public_pay_limiter)],
)
async def read_public_payment(
    token: Annotated[str, Path(max_length=64)],
    billing_service_dep: BillingServiceDep,
) -> PublicPaymentRead:
    payment = await billing_service_dep.public_payment(token)

    if payment is None:
        raise NotFoundError('Payment link not found.', code='PAY_LINK_INVALID')

    return payment


@router.post(
    path='/pay/{token}/checkout',
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(public_pay_limiter)],
)
async def create_public_checkout(
    token: Annotated[str, Path(max_length=64)],
    infinitepay_service_dep: InfinitePayServiceDep,
) -> PublicCheckoutRead:
    """ "Pagar mensalidade": devolve o checkout da InfinitePay."""
    return PublicCheckoutRead(
        url=await infinitepay_service_dep.checkout_for_token(token)
    )


@router.post(
    path='/pay/{token}/confirm',
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(public_pay_limiter)],
)
async def confirm_public_payment(
    token: Annotated[str, Path(max_length=64)],
    data: PayConfirmApi,
    billing_service_dep: BillingServiceDep,
) -> PayConfirmRead:
    """O aluno voltou do checkout: o worker confere e dá a baixa (cobre o
    aviso que se perdeu). A página acompanha pelo GET /pay/{token}."""
    owner = await billing_service_dep.pay_token_owner(token)
    if owner is None:
        raise NotFoundError('Payment link not found.', code='PAY_LINK_INVALID')

    tasks.settle_infinitepay_payment.delay(
        order_nsu=data.order_nsu,
        transaction_nsu=data.transaction_nsu,
        slug=data.slug,
        receipt_url=data.receipt_url,
        student_id=owner[1],
    )
    return PayConfirmRead(status='processing')


@router.post(
    path='/webhooks/infinitepay',
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(webhook_limiter)],
)
async def infinitepay_webhook(data: InfinitePayWebhookApi) -> WebhookAckRead:
    """Aviso da InfinitePay: só enfileira e responde na hora (o aviso não
    tem assinatura; o worker confere no payment_check antes da baixa)."""
    tasks.settle_infinitepay_payment.delay(
        order_nsu=data.order_nsu,
        transaction_nsu=data.transaction_nsu,
        slug=data.invoice_slug,
        receipt_url=data.receipt_url,
    )
    return WebhookAckRead()
