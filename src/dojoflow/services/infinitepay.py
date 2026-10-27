"""Regras da baixa automática pela InfinitePay."""

import logging
import secrets
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.core.crypto import decrypt_secret, encrypt_secret
from dojoflow.core.settings import settings as app_settings
from dojoflow.database.transaction import transactional
from dojoflow.integrations.infinitepay.client import (
    InfinitePayCheckoutDisabled,
    InfinitePayClient,
    InfinitePayKeyRejected,
    InfinitePayUnavailable,
)
from dojoflow.integrations.infinitepay.schemas import (
    CheckoutCustomer,
    CheckoutItem,
    PaymentCheck,
)
from dojoflow.models.academy_billing_settings import AcademyBillingSettings
from dojoflow.models.infinitepay_checkout import InfinitePayCheckout
from dojoflow.schemas.infinitepay_api import InfinitePayStatusApi
from dojoflow.services import billing as billing_module
from dojoflow.services.billing import BillingService, choose_recipient
from dojoflow.services.billing_rules import whatsapp_phone
from dojoflow.shared.enums import (
    CheckoutStatus,
    PaymentMethod,
    PaymentSource,
)
from dojoflow.shared.exceptions import ConflictError, NotFoundError

logger = logging.getLogger(__name__)

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
# Toques repetidos em "Pagar mensalidade" reaproveitam o mesmo link
# (o Pix do checkout vale 72 h; 24 h deixa folga)
LINK_REUSE_WINDOW = timedelta(hours=24)

CAPTURE_METHODS = {
    'pix': PaymentMethod.PIX,
    'credit_card': PaymentMethod.CREDIT_CARD,
}


def webhook_url() -> str:
    return (
        f'{app_settings.WEB_APP_URL}{app_settings.API_V1_PREFIX}'
        '/public/webhooks/infinitepay'
    )


def _customer(
    contact: billing_module.StudentContact, today: date
) -> CheckoutCustomer:
    """Quem paga: a mesma regra do WhatsApp (menor → responsável)."""
    recipient = choose_recipient(contact, today)
    person = (
        recipient[0]
        if recipient
        else billing_module.Contact(contact.name, None, contact.email)
    )
    phone = whatsapp_phone(person.phone)
    return CheckoutCustomer(
        name=' '.join(person.name.split()),
        phone_number=f'+{phone}' if phone else None,
        email=person.email or None,
    )


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
                handle=handle,
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

    async def checkout_for_token(
        self, token: str, today: date | None = None
    ) -> str:
        """URL do checkout com tudo o que o aluno deve hoje.

        Reaproveita o link aberto do aluno com o mesmo valor (criado há
        menos de 24 h); senão cria um novo na InfinitePay.
        """
        billing = BillingService(self.db_session)
        owner = await billing.pay_token_owner(token)
        if owner is None:
            raise NotFoundError(
                'Payment link not found.', code='PAY_LINK_INVALID'
            )
        academy_id, student_id = owner

        settings = await self._settings(academy_id)
        if not await billing.checkout_enabled(academy_id):
            raise ConflictError(
                'A baixa automática não está ligada nesta academia.',
                code='INFINITEPAY_DISABLED',
            )

        today = today or billing_module.local_today()
        page = await billing.public_payment(token, today)
        if page is None or page.status == 'clear':
            raise ConflictError(
                'Este aluno não tem nada em aberto.', code='NOTHING_TO_PAY'
            )

        reusable = await self.db_session.scalar(
            select(InfinitePayCheckout.url)
            .where(
                InfinitePayCheckout.academy_id == academy_id,
                InfinitePayCheckout.student_id == student_id,
                InfinitePayCheckout.status == CheckoutStatus.OPEN,
                InfinitePayCheckout.amount == page.total,
                InfinitePayCheckout.created_at
                > func.now() - LINK_REUSE_WINDOW,
            )
            .order_by(InfinitePayCheckout.id.desc())
            .limit(1)
        )
        if reusable:
            return reusable

        contacts = await billing.contacts(academy_id, {student_id})
        order_nsu = secrets.token_urlsafe(24)
        try:
            url = await self.client.create_link(
                decrypt_secret(settings.infinitepay_api_key),
                order_nsu=order_nsu,
                items=[
                    CheckoutItem(
                        description=item.label, quantity=1, price=item.amount
                    )
                    for item in page.items
                ],
                customer=_customer(contacts[student_id], today),
                redirect_url=f'{app_settings.WEB_APP_URL}/pagar/{token}',
                webhook_url=webhook_url(),
                handle=settings.infinitepay_handle,
            )
        except (
            InfinitePayKeyRejected,
            InfinitePayCheckoutDisabled,
            InfinitePayUnavailable,
        ) as error:
            # Para o aluno, qualquer falha é "tente de novo"; o motivo fica
            # no log (sem a chave) para o suporte
            logger.warning(
                'InfinitePay checkout failed for academy %s: %s',
                academy_id,
                type(error).__name__,
            )
            # Chave apagada ou checkout desligado lá: desliga aqui também,
            # para a página voltar ao Pix copia e cola (e o mestre ver na
            # tela de Configurações que precisa ligar de novo)
            if not isinstance(error, InfinitePayUnavailable):
                await self._save(academy_id, infinitepay_enabled=False)
            raise ConflictError(
                UNAVAILABLE_MESSAGE, code='INFINITEPAY_UNAVAILABLE'
            ) from None

        await self._add_checkout(
            InfinitePayCheckout(
                academy_id=academy_id,
                student_id=student_id,
                handle=settings.infinitepay_handle,
                order_nsu=order_nsu,
                amount=page.total,
                url=url,
                status=CheckoutStatus.OPEN,
            )
        )
        return url

    @transactional
    async def resolve_review(
        self, academy_id: int, student_id: int, review_public_id: uuid.UUID
    ) -> None:
        """O mestre conferiu o pagamento "a conferir": some da ficha."""
        resolved = await self.db_session.scalar(
            update(InfinitePayCheckout)
            .where(
                InfinitePayCheckout.academy_id == academy_id,
                InfinitePayCheckout.student_id == student_id,
                InfinitePayCheckout.public_id == review_public_id,
                InfinitePayCheckout.status == CheckoutStatus.REVIEW,
            )
            .values(status=CheckoutStatus.RESOLVED)
            .returning(InfinitePayCheckout.id)
        )
        if resolved is None:
            raise NotFoundError('Review not found.', code='REVIEW_NOT_FOUND')

    @transactional
    async def _add_checkout(self, checkout: InfinitePayCheckout) -> None:
        self.db_session.add(checkout)

    @transactional
    async def settle(  # noqa: PLR0913
        self,
        order_nsu: str,
        transaction_nsu: str,
        slug: str,
        *,
        receipt_url: str | None = None,
        student_id: int | None = None,
    ) -> CheckoutStatus | None:
        """Aviso (ou volta do aluno) → confere na InfinitePay → baixa.

        Roda no worker. Nada de baixa sem ``paid: true`` do payment_check.
        Uma vez só por pagamento: o link fica travado (FOR UPDATE) até o
        fim, e um segundo aviso igual só devolve a situação.
        student_id: dono do link /pagar de onde o aluno voltou; um pedido
        de outro aluno é ignorado. None = aviso da InfinitePay.
        """
        owner = (
            await self.db_session.execute(
                select(
                    InfinitePayCheckout.academy_id,
                    InfinitePayCheckout.student_id,
                ).where(InfinitePayCheckout.order_nsu == order_nsu)
            )
        ).one_or_none()
        if owner is None:
            logger.info('InfinitePay notice for unknown order ignored.')
            return None
        # Mesma ordem de travas da baixa manual (cobranças do aluno, depois
        # o link): sem deadlock, e dois links do mesmo aluno pagos juntos
        # são conferidos um de cada vez
        billing = BillingService(self.db_session)
        await billing.lock_student_charges(owner.academy_id, owner.student_id)
        checkout = await self._lock_checkout(order_nsu, student_id)
        if checkout is None:
            return None
        if checkout.transaction_nsu is not None:
            # Aviso repetido devolve a situação; outro pagamento do mesmo
            # link (não deveria acontecer) é ignorado
            same = checkout.transaction_nsu == transaction_nsu
            if not same:
                logger.warning(
                    'InfinitePay checkout %s already settled by another '
                    'transaction; new one ignored.',
                    checkout.id,
                )
            return checkout.status if same else None

        check = await self._confirmed_payment(checkout, transaction_nsu, slug)
        if check is None:
            return None

        today = billing_module.local_today()
        checkout.transaction_nsu = transaction_nsu
        checkout.invoice_slug = slug
        checkout.receipt_url = receipt_url
        checkout.capture_method = check.capture_method
        checkout.paid_amount = check.paid_amount or check.amount
        checkout.installments = check.installments
        checkout.paid_at = datetime.now(UTC)

        owed = sum(
            (
                charge.open_amount
                for charge in await billing.overdue_for_student(
                    checkout.academy_id, checkout.student_id, today
                )
            ),
            Decimal(0),
        )
        # Link cancelado (baixa manual no meio do caminho) ou valor que já
        # não é o devido: nada é lançado sozinho, o mestre confere
        if (
            checkout.status is not CheckoutStatus.OPEN
            or owed != checkout.amount
        ):
            checkout.status = CheckoutStatus.REVIEW
            await self.db_session.flush()
            return checkout.status

        payment = await billing.create_payment(
            checkout.academy_id,
            checkout.student_id,
            checkout.amount,
            today,
            CAPTURE_METHODS.get(
                check.capture_method or '', PaymentMethod.OTHER
            ),
            'InfinitePay',
            source=PaymentSource.INFINITEPAY,
        )
        checkout.payment_transaction_id = payment.id
        checkout.status = CheckoutStatus.PAID
        await self.db_session.flush()
        return checkout.status

    async def _lock_checkout(
        self, order_nsu: str, student_id: int | None
    ) -> InfinitePayCheckout | None:
        checkout = await self.db_session.scalar(
            select(InfinitePayCheckout)
            .where(InfinitePayCheckout.order_nsu == order_nsu)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if checkout is None:
            logger.info('InfinitePay notice for unknown order ignored.')
            return None
        if student_id is not None and checkout.student_id != student_id:
            logger.warning('InfinitePay confirm for another student ignored.')
            return None
        return checkout

    async def _confirmed_payment(
        self, checkout: InfinitePayCheckout, transaction_nsu: str, slug: str
    ) -> PaymentCheck | None:
        """payment_check com a tag do link; pago e com o valor cheio, ou
        None. InfinitePay fora do ar: a exceção sobe (o worker tenta de
        novo)."""
        check = await self.client.payment_check(
            handle=checkout.handle,
            order_nsu=checkout.order_nsu,
            transaction_nsu=transaction_nsu,
            slug=slug,
        )
        if not (check.success and check.paid):
            # Tag errada também cai aqui: deixa rastro para o suporte
            logger.warning(
                'InfinitePay payment_check denied checkout %s.', checkout.id
            )
            return None
        paid_amount = check.paid_amount or check.amount
        if paid_amount is None or paid_amount < checkout.amount:
            logger.warning(
                'InfinitePay checkout %s paid less than the link amount.',
                checkout.id,
            )
            return None
        return check
