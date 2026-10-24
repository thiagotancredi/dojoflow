"""Regras da baixa automática pela InfinitePay."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.crypto import decrypt_secret, encrypt_secret
from dojoflow.database.transaction import transactional
from dojoflow.integrations.infinitepay.client import (
    InfinitePayCheckoutDisabled,
    InfinitePayClient,
    InfinitePayKeyRejected,
    InfinitePayUnavailable,
)
from dojoflow.integrations.infinitepay.schemas import CheckoutItem
from dojoflow.models.academy_billing_settings import AcademyBillingSettings
from dojoflow.schemas.infinitepay_api import InfinitePayStatusApi
from dojoflow.shared.exceptions import ConflictError

KEY_REJECTED_MESSAGE = (
    'A chave de API não foi aceita. Crie uma chave nova no app da '
    'InfinitePay (Checkout → Configurações → API Keys) e cole aqui.'
)
CHECKOUT_DISABLED_MESSAGE = (
    'A InfinitePay ainda não liberou o checkout para essa tag. Confira se '
    'a tag está certa e, no app da InfinitePay, desligue e ligue de novo '
    "'Habilitar Checkout Integrado'."
)
UNAVAILABLE_MESSAGE = (
    'Não foi possível falar com a InfinitePay agora. Tente de novo.'
)

TEST_LINK_DESCRIPTION = 'Teste de conexão Katsuflow'
TEST_LINK_PRICE = Decimal('1.00')


def infinitepay_error(error: Exception) -> ConflictError:
    """Erro do cliente → resposta 409 com o texto para o mestre."""
    if isinstance(error, InfinitePayKeyRejected):
        return ConflictError(
            KEY_REJECTED_MESSAGE, code='INFINITEPAY_KEY_REJECTED'
        )
    if isinstance(error, InfinitePayCheckoutDisabled):
        return ConflictError(
            CHECKOUT_DISABLED_MESSAGE, code='INFINITEPAY_CHECKOUT_DISABLED'
        )
    return ConflictError(UNAVAILABLE_MESSAGE, code='INFINITEPAY_UNAVAILABLE')


class InfinitePayService:
    def __init__(
        self, db_session: AsyncSession, client: InfinitePayClient
    ) -> None:
        self.db_session = db_session
        self.client = client

    async def _settings(
        self, academy_id: int
    ) -> AcademyBillingSettings | None:
        return await self.db_session.scalar(
            select(AcademyBillingSettings).where(
                AcademyBillingSettings.academy_id == academy_id
            )
        )

    async def status(self, academy_id: int) -> InfinitePayStatusApi:
        settings = await self._settings(academy_id)
        if settings is None:
            return InfinitePayStatusApi(
                enabled=False, handle=None, tested_at=None, key_last4=None
            )

        key = settings.infinitepay_api_key
        return InfinitePayStatusApi(
            enabled=settings.infinitepay_enabled,
            handle=settings.infinitepay_handle,
            tested_at=settings.infinitepay_tested_at,
            key_last4=decrypt_secret(key)[-4:] if key else None,
        )

    async def connect(
        self, academy_id: int, handle: str, api_key: str
    ) -> InfinitePayStatusApi:
        """Testar e ligar: cria um link de teste com a chave; deu certo,
        guarda a tag e a chave (cifrada) e liga. Falhou, nada muda."""
        try:
            await self.client.create_link(
                api_key,
                order_nsu=f'kftest-{uuid.uuid4().hex}',
                items=[
                    CheckoutItem(
                        description=TEST_LINK_DESCRIPTION,
                        quantity=1,
                        price=TEST_LINK_PRICE,
                    )
                ],
                customer=None,
                redirect_url=None,
                webhook_url=None,
            )
        except (
            InfinitePayKeyRejected,
            InfinitePayCheckoutDisabled,
            InfinitePayUnavailable,
        ) as error:
            raise infinitepay_error(error) from None

        await self._save(
            academy_id,
            infinitepay_handle=handle,
            infinitepay_api_key=encrypt_secret(api_key),
            infinitepay_enabled=True,
            infinitepay_tested_at=datetime.now(UTC),
        )
        return await self.status(academy_id)

    async def disconnect(self, academy_id: int) -> InfinitePayStatusApi:
        """Desliga; a tag e a chave ficam guardadas para religar."""
        if await self._settings(academy_id) is not None:
            await self._save(academy_id, infinitepay_enabled=False)
        return await self.status(academy_id)

    @transactional
    async def _save(self, academy_id: int, **values: object) -> None:
        await self.db_session.execute(
            insert(AcademyBillingSettings)
            .values(academy_id=academy_id, **values)
            .on_conflict_do_update(
                index_elements=[AcademyBillingSettings.academy_id],
                set_={**values, 'updated_at': func.now()},
            )
        )
