from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from dojoflow.api.dependencies.billing import BillingServiceDep
from dojoflow.api.dependencies.rate_limit import public_pay_limiter
from dojoflow.schemas.public_pay import PublicPaymentRead
from dojoflow.shared.exceptions import NotFoundError

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
