import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from dojoflow.core.settings import settings as app_settings
from dojoflow.database.transaction import transactional
from dojoflow.models.academy import Academy
from dojoflow.models.academy_billing_settings import AcademyBillingSettings
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.infinitepay_checkout import InfinitePayCheckout
from dojoflow.models.master import Master
from dojoflow.models.modality import Modality
from dojoflow.models.payment import Payment
from dojoflow.models.payment_allocation import PaymentAllocation
from dojoflow.models.payment_transaction import PaymentTransaction
from dojoflow.models.responsible import Responsible
from dojoflow.models.student import Student, new_pay_token
from dojoflow.models.student_responsible import StudentResponsible
from dojoflow.schemas.billing import (
    AllocationPreview,
    AllocationRead,
    BillingOverviewItemRead,
    BillingOverviewRead,
    ChargeRead,
    CheckoutReviewRead,
    OverviewFilter,
    PaymentRead,
    StudentBillingRead,
)
from dojoflow.schemas.billing_settings_api import BillingSettingsApi
from dojoflow.schemas.dashboard import DueSoonChargeRead, OverdueStudentRead
from dojoflow.schemas.public_pay import (
    PublicPaymentItemRead,
    PublicPaymentRead,
)
from dojoflow.services.belt_rules import ACADEMY_TIMEZONE, local_today
from dojoflow.services.billing_rules import (
    OpenCharge,
    age_on,
    allocate_oldest_first,
    billing_status,
    due_date_for,
    first_monthly_month,
    format_brl,
    join_names,
    month_name,
    whatsapp_phone,
)
from dojoflow.services.pix import pix_copy_paste
from dojoflow.shared.enums import (
    AcademyStatus,
    CheckoutStatus,
    EnrollmentStatus,
    PaymentKind,
    PaymentMethod,
    PaymentSource,
    PaymentStatus,
)
from dojoflow.shared.exceptions import ConflictError, NotFoundError
from dojoflow.shared.text import name_sort_key

CENTS = Decimal('0.01')
ZERO = Decimal('0.00')
# Sem "da/do {academia}" (o artigo depende do nome) e sem "sua mensalidade"
# (no aluno menor, quem lê é o responsável); assinada pelo mestre, com o
# nome em negrito no WhatsApp (*...*), e pela academia
DEFAULT_MESSAGE_TEMPLATE = (
    'Olá, {nome}! Tudo bem?\n\n'
    'Passando para lembrar que há uma mensalidade em aberto: {valor}.\n\n'
    'Para pagar pelo Pix, é só tocar aqui:\n{link}\n\n'
    'Se já pagou, desconsidere. Obrigado!\n\n'
    '*{mestre}*\n{academia}'
)
ENROLLMENT_FEE_LABEL = 'taxa de matrícula'
CLOSED_STATUSES = {'paid', 'waived'}
# Texto salvo sem {link}: o link entra no fim, para ninguém ficar sem ele
LINK_FALLBACK = '\n\nPara pagar pelo Pix, toque aqui: {link}'


def pay_url(token: str) -> str:
    """Endereço da página pública de pagamento do aluno."""
    return f'{app_settings.WEB_APP_URL}/pagar/{token}'


def _months_from(start: date, end: date) -> list[date]:
    """Meses (dia 1) de start até end, inclusive."""
    months = []
    month = start
    while month <= end:
        months.append(month)
        month = first_monthly_month(month)
    return months


def _charge_label(kind: PaymentKind, reference_month: date, year: int) -> str:
    if kind is PaymentKind.ENROLLMENT_FEE:
        return ENROLLMENT_FEE_LABEL
    return month_name(reference_month, year)


def open_label(charges: list[ChargeRead], current_year: int) -> str:
    """Ex.: "taxa de matrícula, janeiro e fevereiro"."""
    has_fee = any(c.kind is PaymentKind.ENROLLMENT_FEE for c in charges)
    months = sorted({
        c.reference_month for c in charges if c.kind is PaymentKind.MONTHLY
    })
    names = [month_name(month, current_year) for month in months]
    return join_names([ENROLLMENT_FEE_LABEL, *names] if has_fee else names)


ADULT_AGE = 18
DUE_SOON_DAYS = 7
DASHBOARD_LIMIT = 5


@dataclass(frozen=True)
class DashboardBilling:
    """Listas do dashboard (até 5 cada) e os totais de alunos."""

    overdue: list[OverdueStudentRead]
    due_soon: list[DueSoonChargeRead]
    overdue_students: int
    due_soon_students: int
    overdue_total: Decimal


@dataclass(frozen=True)
class Contact:
    name: str
    phone: str | None
    email: str | None = None


@dataclass(frozen=True)
class StudentContact:
    public_id: UUID
    name: str
    phone: str | None
    birth_date: date | None
    responsibles: tuple[Contact, ...]
    pay_token: str
    email: str | None = None


def choose_recipient(
    student: StudentContact, today: date
) -> tuple[Contact, bool] | None:
    """Quem recebe a cobrança: (contato, é responsável?).

    Menor de 18 com responsável com telefone: o primeiro responsável.
    Senão o próprio aluno; sem telefone dele, um responsável.
    """
    own = [(Contact(student.name, student.phone, student.email), False)]
    responsibles = [(contact, True) for contact in student.responsibles]
    is_minor = (
        student.birth_date is not None
        and age_on(student.birth_date, today) < ADULT_AGE
    )
    candidates = responsibles + own if is_minor else own + responsibles

    for contact, is_responsible in candidates:
        if whatsapp_phone(contact.phone):
            return contact, is_responsible

    return None


def choose_email_recipient(
    student: StudentContact, today: date
) -> Contact | None:
    """Quem recebe a cobrança por e-mail, na mesma ordem do WhatsApp.

    Menor de 18: responsáveis antes do próprio aluno. Vale o primeiro
    com e-mail preenchido.
    """
    own = [Contact(student.name, student.phone, student.email)]
    responsibles = list(student.responsibles)
    is_minor = (
        student.birth_date is not None
        and age_on(student.birth_date, today) < ADULT_AGE
    )
    candidates = responsibles + own if is_minor else own + responsibles

    for contact in candidates:
        if contact.email and contact.email.strip():
            return contact

    return None


def has_pix(settings: BillingSettingsApi) -> bool:
    """Chave Pix completa: dá para montar o código copia e cola."""
    return bool(
        settings.pix_key and settings.pix_key_type and settings.pix_city
    )


@dataclass(frozen=True)
class MessageSender:
    """Quem assina a cobrança: a academia e o mestre dela."""

    academy: str
    master: str


def whatsapp_url(  # noqa: PLR0913, PLR0917
    student: StudentContact,
    overdue_charges: list[ChargeRead],
    settings: BillingSettingsApi,
    sender: MessageSender,
    today: date,
) -> str | None:
    """Link wa.me com a mensagem de cobrança; None sem atraso ou telefone."""
    recipient = choose_recipient(student, today)

    if not overdue_charges or recipient is None:
        return None

    contact, _ = recipient
    overdue_total = sum((c.open_amount for c in overdue_charges), ZERO)
    values = {
        '{nome}': contact.name.split()[0],
        '{mestre}': sender.master,
        '{academia}': sender.academy,
        '{valor}': format_brl(overdue_total),
        '{meses}': open_label(overdue_charges, today.year),
        '{pix}': settings.pix_key or '',
        '{recebedor}': settings.recipient_name or sender.academy,
        '{link}': pay_url(student.pay_token),
    }
    text = settings.message_template or DEFAULT_MESSAGE_TEMPLATE
    if '{link}' not in text:
        text += LINK_FALLBACK
    # Troca simples: chaves que o mestre escrever no texto não quebram nada
    for marker, value in values.items():
        text = text.replace(marker, value)

    return f'https://wa.me/{whatsapp_phone(contact.phone)}?text={quote(text)}'


def _public_label(
    charge: ChargeRead,
    year: int,
    student_first_name: str | None,
    show_modality: bool,
) -> str:
    """Ex.: "Mensalidade · janeiro" ou "Mensalidade de Ana · janeiro"."""
    of_student = f' de {student_first_name}' if student_first_name else ''
    if charge.kind is PaymentKind.ENROLLMENT_FEE:
        label = f'Taxa de matrícula{of_student}'
    else:
        month = month_name(charge.reference_month, year)
        label = f'Mensalidade{of_student} · {month}'
    return f'{label} · {charge.modality_name}' if show_modality else label


def _refresh_paid_status(charge: Payment, paid_on: date | None) -> None:
    """Situação gravada a partir do valor já alocado na cobrança."""
    if charge.status is PaymentStatus.WAIVED:
        return
    if charge.amount_paid >= (charge.amount_due or ZERO):
        if charge.status is not PaymentStatus.PAID:
            charge.paid_at = paid_on
        charge.status = PaymentStatus.PAID
        return
    charge.status = (
        PaymentStatus.PARTIAL
        if charge.amount_paid > 0
        else PaymentStatus.PENDING
    )
    charge.paid_at = None


def local_date(moment: datetime) -> date:
    """Data em Brasília de um instante gravado em UTC."""
    return moment.astimezone(ACADEMY_TIMEZONE).date()


class BillingService:  # noqa: PLR0904
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    @transactional
    async def ensure_monthly_charges(
        self,
        academy_id: int | None,
        today: date,
    ) -> int:
        """Cria as mensalidades que faltam até o mês de hoje.

        academy_id=None: todas as academias (o worker, no dia 1º e ao
        ligar). Pode rodar quantas vezes quiser: um mês que já existe nunca
        é criado de novo. As telas não geram: mostram o que existe.
        """
        this_month = today.replace(day=1)

        # Último mês já gerado de cada matrícula, a partir do início da
        # cobrança (meses lançados à mão antes disso não contam)
        last_generated = (
            select(
                Payment.enrollment_id,
                func.max(Payment.reference_month).label('last_month'),
            )
            .join(Enrollment, Enrollment.id == Payment.enrollment_id)
            .where(
                Payment.kind == PaymentKind.MONTHLY,
                Payment.reference_month >= Enrollment.billing_start_month,
            )
            .group_by(Payment.enrollment_id)
            .subquery()
        )

        stmt = (
            select(
                Enrollment.id,
                Enrollment.academy_id,
                Enrollment.monthly_fee,
                Enrollment.due_day,
                Enrollment.billing_start_month,
                last_generated.c.last_month,
            )
            .outerjoin(
                last_generated,
                last_generated.c.enrollment_id == Enrollment.id,
            )
            .where(
                Enrollment.status == EnrollmentStatus.ACTIVE,
                Enrollment.is_exempt.is_(False),
                Enrollment.monthly_fee > 0,
                Enrollment.due_day.is_not(None),
                Enrollment.billing_start_month.is_not(None),
                Enrollment.billing_start_month <= this_month,
            )
        )

        if academy_id is not None:
            stmt = stmt.where(Enrollment.academy_id == academy_id)

        rows = (await self.db_session.execute(stmt)).all()
        values: list[dict[str, Any]] = []

        for row in rows:
            start = row.billing_start_month
            if row.last_month is not None:
                start = max(start, first_monthly_month(row.last_month))

            values.extend(
                {
                    'academy_id': row.academy_id,
                    'enrollment_id': row.id,
                    'kind': PaymentKind.MONTHLY,
                    'reference_month': month,
                    'due_date': due_date_for(month, row.due_day),
                    'status': PaymentStatus.PENDING,
                    'amount_due': row.monthly_fee,
                    'amount_paid': Decimal(0),
                }
                for month in _months_from(start, this_month)
            )

        if not values:
            return 0

        # Duas gerações ao mesmo tempo (agenda + conferência ao ligar):
        # a constraint única barra a segunda, sem erro
        created = await self.db_session.scalars(
            insert(Payment)
            .values(values)
            .on_conflict_do_nothing(
                constraint='uq_payment_enrollment_kind_month'
            )
            .returning(Payment.id)
        )

        return len(created.all())

    async def get_settings(self, academy_id: int) -> BillingSettingsApi:
        """Configurações de cobrança; sem texto salvo, devolve o padrão."""
        settings = await self.db_session.scalar(
            select(AcademyBillingSettings).where(
                AcademyBillingSettings.academy_id == academy_id
            )
        )

        if settings is None:
            return BillingSettingsApi(
                message_template=DEFAULT_MESSAGE_TEMPLATE
            )

        return BillingSettingsApi.model_construct(
            pix_key=settings.pix_key,
            pix_key_type=settings.pix_key_type,
            pix_city=settings.pix_city,
            recipient_name=settings.recipient_name,
            bank_details=settings.bank_details,
            message_template=(
                settings.message_template or DEFAULT_MESSAGE_TEMPLATE
            ),
        )

    @transactional
    async def save_settings(
        self, academy_id: int, data: BillingSettingsApi
    ) -> BillingSettingsApi:
        values = data.model_dump()
        # Texto igual ao padrão não é gravado: segue o padrão se ele mudar
        if values['message_template'] == DEFAULT_MESSAGE_TEMPLATE:
            values['message_template'] = None

        await self.db_session.execute(
            insert(AcademyBillingSettings)
            .values(academy_id=academy_id, **values)
            .on_conflict_do_update(
                index_elements=[AcademyBillingSettings.academy_id],
                set_={**values, 'updated_at': func.now()},
            )
        )

        return await self.get_settings(academy_id)

    async def create_enrollment_fee(
        self,
        academy_id: int,
        enrollment_id: int,
        amount: Decimal | None,
        enrolled_on: date,
    ) -> None:
        """Taxa da matrícula, vencendo no dia dela; sem valor = isenta."""
        charged = amount is not None and amount > 0
        self.db_session.add(
            Payment(
                academy_id=academy_id,
                enrollment_id=enrollment_id,
                kind=PaymentKind.ENROLLMENT_FEE,
                reference_month=enrolled_on.replace(day=1),
                due_date=enrolled_on,
                status=(
                    PaymentStatus.PENDING if charged else PaymentStatus.WAIVED
                ),
                amount_due=amount.quantize(CENTS) if charged else ZERO,
                amount_paid=ZERO,
            )
        )
        await self.db_session.flush()

    async def start_enrollment_billing(
        self,
        academy_id: int,
        enrollment_id: int,
        enrollment_fee: Decimal | None,
        *,
        bills_monthly: bool,
    ) -> None:
        """Matrícula nova: taxa hoje e 1ª mensalidade no mês seguinte."""
        today = local_today()

        if bills_monthly:
            await self.restart_monthly_billing(enrollment_id, today)

        await self.create_enrollment_fee(
            academy_id, enrollment_id, enrollment_fee, today
        )

    async def restart_monthly_billing(
        self, enrollment_id: int, today: date | None = None
    ) -> None:
        """Mensalidades automáticas a partir do mês seguinte a hoje."""
        start = first_monthly_month(today or local_today())
        await self.db_session.execute(
            update(Enrollment)
            .where(Enrollment.id == enrollment_id)
            .values(billing_start_month=start)
        )

    async def student_billing(
        self,
        academy_id: int,
        student_id: int,
        today: date | None = None,
    ) -> StudentBillingRead:
        today = today or local_today()
        charges = await self._charges(
            academy_id, today, Enrollment.student_id == student_id
        )
        open_charges = [c for c in charges if c.status not in CLOSED_STATUSES]
        open_total = sum((c.amount - c.paid for c in open_charges), Decimal(0))

        return StudentBillingRead(
            open_total=open_total.quantize(CENTS),
            open_months=open_label(open_charges, today.year),
            whatsapp_url=await self._whatsapp_url_for(
                academy_id, student_id, charges, today
            ),
            pay_url=pay_url(
                await self.db_session.scalar(
                    select(Student.pay_token).where(
                        Student.academy_id == academy_id,
                        Student.id == student_id,
                    )
                )
                or ''
            ),
            charges=charges,
            payments=await self._payments(
                academy_id, today, PaymentTransaction.student_id == student_id
            ),
            reviews=await self._reviews(academy_id, student_id),
        )

    async def _reviews(
        self, academy_id: int, student_id: int
    ) -> list[CheckoutReviewRead]:
        """Pagamentos da InfinitePay "a conferir", do mais novo ao mais
        antigo."""
        rows = (
            await self.db_session.scalars(
                select(InfinitePayCheckout)
                .where(
                    InfinitePayCheckout.academy_id == academy_id,
                    InfinitePayCheckout.student_id == student_id,
                    InfinitePayCheckout.status == CheckoutStatus.REVIEW,
                )
                .order_by(InfinitePayCheckout.paid_at.desc())
            )
        ).all()
        return [
            CheckoutReviewRead(
                public_id=row.public_id,
                amount=row.paid_amount or row.amount,
                paid_at=local_date(row.paid_at or row.updated_at),
                receipt_url=row.receipt_url,
            )
            for row in rows
        ]

    async def _charges(
        self,
        academy_id: int,
        today: date,
        *filters: ColumnElement[bool],
    ) -> list[ChargeRead]:
        stmt = (
            select(
                Payment,
                Enrollment.student_id,
                Enrollment.public_id.label('enrollment_public_id'),
                Modality.name.label('modality_name'),
            )
            .join(Enrollment, Enrollment.id == Payment.enrollment_id)
            .join(Modality, Modality.id == Enrollment.modality_id)
            .where(Payment.academy_id == academy_id, *filters)
            .order_by(Payment.due_date.desc(), Payment.id.desc())
        )
        rows = (await self.db_session.execute(stmt)).all()
        charges = []

        for payment, student_id, enrollment_public_id, modality_name in rows:
            amount = (
                payment.amount_due if payment.amount_due is not None else ZERO
            )
            due_date = payment.due_date or payment.reference_month
            charges.append(
                ChargeRead(
                    id=payment.id,
                    public_id=payment.public_id,
                    kind=payment.kind,
                    student_id=student_id,
                    enrollment_public_id=enrollment_public_id,
                    modality_name=modality_name,
                    reference_month=payment.reference_month,
                    due_date=due_date,
                    amount=amount,
                    paid=payment.amount_paid,
                    status=billing_status(
                        amount,
                        payment.amount_paid,
                        payment.status is PaymentStatus.WAIVED,
                        due_date,
                        today,
                    ),
                    created_at=payment.created_at,
                )
            )

        return charges

    async def _charge(
        self, academy_id: int, charge_id: int, today: date
    ) -> ChargeRead:
        (charge,) = await self._charges(
            academy_id, today, Payment.id == charge_id
        )
        return charge

    async def _ensure_no_payments(self, charge: Payment) -> None:
        has_allocation = await self.db_session.scalar(
            select(exists().where(PaymentAllocation.payment_id == charge.id))
        )

        if has_allocation or charge.amount_paid > 0:
            raise ConflictError(
                'This charge already has payments.',
                code='CHARGE_HAS_PAYMENTS',
            )

    @transactional
    async def launch_past_charge(  # noqa: PLR0913, PLR0917
        self,
        academy_id: int,
        enrollment_id: int,
        reference_month: date,
        amount: Decimal,
        due_date: date,
        today: date | None = None,
    ) -> ChargeRead:
        """Lança à mão uma mensalidade de antes da cobrança automática."""
        today = today or local_today()
        enrollment = await self.db_session.get_one(Enrollment, enrollment_id)
        # Sem cobrança automática, qualquer mês até o atual
        limit = enrollment.billing_start_month or first_monthly_month(today)

        if reference_month >= limit:
            raise ConflictError(
                'Only months before the automatic billing can be launched.',
                code='CHARGE_NOT_PAST',
            )

        created = await self.db_session.scalar(
            insert(Payment)
            .values(
                academy_id=academy_id,
                enrollment_id=enrollment_id,
                kind=PaymentKind.MONTHLY,
                reference_month=reference_month,
                due_date=due_date,
                status=PaymentStatus.PENDING,
                amount_due=amount,
                amount_paid=Decimal(0),
            )
            .on_conflict_do_nothing(
                constraint='uq_payment_enrollment_kind_month'
            )
            .returning(Payment.id)
        )

        if created is None:
            raise ConflictError(
                'This month already has a charge for this enrollment.',
                code='CHARGE_ALREADY_EXISTS',
            )

        return await self._charge(academy_id, created, today)

    @transactional
    async def update_charge(
        self,
        academy_id: int,
        charge_id: int,
        amount: Decimal | None,
        due_date: date | None,
    ) -> ChargeRead:
        """Muda valor e/ou vencimento de uma cobrança ainda sem baixa."""
        charge = await self.db_session.get_one(Payment, charge_id)
        await self._ensure_no_payments(charge)

        if amount is not None:
            charge.amount_due = amount.quantize(CENTS)
        if due_date is not None:
            charge.due_date = due_date

        await self.db_session.flush()
        return await self._charge(academy_id, charge_id, local_today())

    @transactional
    async def set_waived(
        self,
        academy_id: int,
        charge_id: int,
        waived: bool,
    ) -> ChargeRead:
        """Isenta a cobrança (sem baixa) ou desfaz a isenção."""
        charge = await self.db_session.get_one(Payment, charge_id)

        if waived:
            await self._ensure_no_payments(charge)

        charge.status = (
            PaymentStatus.WAIVED if waived else PaymentStatus.PENDING
        )
        await self.db_session.flush()
        return await self._charge(academy_id, charge_id, local_today())

    async def lock_student_charges(
        self, academy_id: int, student_id: int
    ) -> dict[int, Payment]:
        # Duas baixas ao mesmo tempo para o mesmo aluno: a segunda espera a
        # primeira terminar e enxerga os saldos já atualizados
        rows = await self.db_session.scalars(
            select(Payment)
            .join(Enrollment, Enrollment.id == Payment.enrollment_id)
            .where(
                Payment.academy_id == academy_id,
                Enrollment.student_id == student_id,
            )
            .with_for_update(of=Payment)
            .execution_options(populate_existing=True)
        )
        return {charge.id: charge for charge in rows}

    async def _plan_allocations(
        self,
        academy_id: int,
        student_id: int,
        amount: Decimal,
        today: date,
    ) -> list[tuple[ChargeRead, Decimal]]:
        charges = await self._charges(
            academy_id, today, Enrollment.student_id == student_id
        )
        open_charges = {
            c.id: c for c in charges if c.status not in CLOSED_STATUSES
        }

        if not open_charges:
            raise ConflictError(
                'Este aluno não tem nada em aberto.', code='NOTHING_TO_PAY'
            )

        open_total = sum(
            (c.open_amount for c in open_charges.values()), Decimal(0)
        )
        if amount > open_total:
            raise ConflictError(
                'O valor é maior que o total em aberto. '
                f'O máximo é {format_brl(open_total)}.',
                code='PAYMENT_EXCEEDS_OPEN',
            )

        plan = allocate_oldest_first(
            [
                OpenCharge(c.id, c.due_date, c.created_at, c.open_amount)
                for c in open_charges.values()
            ],
            amount,
        )
        return [(open_charges[charge_id], part) for charge_id, part in plan]

    async def preview_payment(
        self,
        academy_id: int,
        student_id: int,
        amount: Decimal,
    ) -> list[AllocationPreview]:
        """Como a baixa vai ser abatida, sem gravar nada."""
        today = local_today()
        plan = await self._plan_allocations(
            academy_id, student_id, amount, today
        )

        return [
            AllocationPreview(
                charge_public_id=charge.public_id,
                label=_charge_label(
                    charge.kind, charge.reference_month, today.year
                ),
                amount=part.quantize(CENTS),
                settles=part == charge.open_amount,
            )
            for charge, part in plan
        ]

    @transactional
    async def create_bulk_payments(
        self,
        academy_id: int,
        items: list[tuple[int, Decimal]],
        paid_on: date,
        method: PaymentMethod | None,
    ) -> Decimal:
        """Baixa em lote: um pagamento por aluno, numa transação só (se um
        falhar, nenhum entra). Cada um segue a regra da baixa individual."""
        total = ZERO

        for student_id, amount in items:
            await self.create_payment(
                academy_id, student_id, amount, paid_on, method, None
            )
            total += amount

        return total

    @transactional
    async def create_payment(  # noqa: PLR0913, PLR0917
        self,
        academy_id: int,
        student_id: int,
        amount: Decimal,
        paid_on: date,
        method: PaymentMethod | None,
        notes: str | None,
        *,
        source: PaymentSource = PaymentSource.MANUAL,
    ) -> PaymentRead:
        """Baixa do aluno, abatendo da cobrança mais antiga à mais nova.

        Baixa manual cancela (do lado do Katsuflow) os links de checkout
        abertos do aluno: a página /pagar não os reaproveita mais.
        """
        today = local_today()
        locked = await self.lock_student_charges(academy_id, student_id)
        plan = await self._plan_allocations(
            academy_id, student_id, amount, today
        )

        transaction = PaymentTransaction(
            academy_id=academy_id,
            student_id=student_id,
            payment_method=method,
            gross_amount=amount,
            received_at=paid_on,
            notes=notes,
            source=source,
        )
        self.db_session.add(transaction)
        await self.db_session.flush()

        for charge, part in plan:
            self.db_session.add(
                PaymentAllocation(
                    academy_id=academy_id,
                    payment_transaction_id=transaction.id,
                    payment_id=charge.id,
                    allocated_amount=part,
                )
            )
            row = locked[charge.id]
            row.amount_paid += part
            _refresh_paid_status(row, paid_on)

        if source is PaymentSource.MANUAL:
            await self._cancel_open_checkouts(academy_id, student_id)

        await self.db_session.flush()
        (payment,) = await self._payments(
            academy_id, today, PaymentTransaction.id == transaction.id
        )
        return payment

    @transactional
    async def delete_payment(
        self,
        academy_id: int,
        student_id: int,
        payment_id: int,
    ) -> None:
        """Desfaz a baixa: cada cobrança volta ao saldo de antes dela."""
        locked = await self.lock_student_charges(academy_id, student_id)
        allocations = (
            await self.db_session.scalars(
                select(PaymentAllocation).where(
                    PaymentAllocation.academy_id == academy_id,
                    PaymentAllocation.payment_transaction_id == payment_id,
                )
            )
        ).all()

        for allocation in allocations:
            charge = locked[allocation.payment_id]
            charge.amount_paid -= allocation.allocated_amount
            _refresh_paid_status(charge, None)

        # Baixa automática desfeita: o link continua pago (o dinheiro está
        # na InfinitePay), só deixa de apontar para a baixa
        await self.db_session.execute(
            update(InfinitePayCheckout)
            .where(
                InfinitePayCheckout.academy_id == academy_id,
                InfinitePayCheckout.payment_transaction_id == payment_id,
            )
            .values(payment_transaction_id=None)
        )
        await self.db_session.execute(
            delete(PaymentAllocation).where(
                PaymentAllocation.payment_transaction_id == payment_id
            )
        )
        await self.db_session.execute(
            delete(PaymentTransaction).where(
                PaymentTransaction.id == payment_id,
                PaymentTransaction.academy_id == academy_id,
            )
        )

    async def contacts(
        self, academy_id: int, student_ids: set[int]
    ) -> dict[int, StudentContact]:
        if not student_ids:
            return {}

        students = (
            await self.db_session.execute(
                select(
                    Student.id,
                    Student.public_id,
                    Student.name,
                    Student.phone,
                    Student.birth_date,
                    Student.pay_token,
                    Student.email,
                ).where(
                    Student.academy_id == academy_id,
                    Student.id.in_(student_ids),
                )
            )
        ).all()
        links = (
            await self.db_session.execute(
                select(
                    StudentResponsible.student_id,
                    Responsible.name,
                    Responsible.phone,
                    Responsible.email,
                )
                .join(
                    Responsible,
                    Responsible.id == StudentResponsible.responsible_id,
                )
                .where(
                    StudentResponsible.academy_id == academy_id,
                    StudentResponsible.student_id.in_(student_ids),
                )
                .order_by(StudentResponsible.id)
            )
        ).all()

        responsibles: dict[int, list[Contact]] = {}
        for link in links:
            responsibles.setdefault(link.student_id, []).append(
                Contact(link.name, link.phone, link.email)
            )

        return {
            row.id: StudentContact(
                public_id=row.public_id,
                name=row.name,
                phone=row.phone,
                birth_date=row.birth_date,
                responsibles=tuple(responsibles.get(row.id, [])),
                pay_token=row.pay_token,
                email=row.email,
            )
            for row in students
        }

    async def academy_name(self, academy_id: int) -> str:
        return (
            await self.db_session.scalar(
                select(Academy.name).where(Academy.id == academy_id)
            )
            or ''
        )

    async def academy_master(self, academy_id: int) -> tuple[str, str | None]:
        """(nome, e-mail) de quem assina pela academia.

        Academia com mais de um mestre: o primeiro cadastrado.
        """
        row = (
            await self.db_session.execute(
                select(Master.name, Master.email)
                .where(Master.academy_id == academy_id)
                .order_by(Master.id)
                .limit(1)
            )
        ).one_or_none()
        return (row.name, row.email) if row else ('', None)

    async def billing_configured(self, academy_id: int) -> bool:
        """Chave Pix completa ou InfinitePay ligada."""
        return has_pix(await self.get_settings(academy_id)) or (
            await self.checkout_enabled(academy_id)
        )

    async def _sender(self, academy_id: int) -> MessageSender:
        return MessageSender(
            academy=await self.academy_name(academy_id),
            master=(await self.academy_master(academy_id))[0],
        )

    @transactional
    async def renew_pay_token(self, academy_id: int, student_id: int) -> str:
        """Troca o código do link de pagamento; o antigo para de valer."""
        token = new_pay_token()
        updated = await self.db_session.scalar(
            update(Student)
            .where(Student.academy_id == academy_id, Student.id == student_id)
            .values(pay_token=token)
            .returning(Student.id)
        )
        if updated is None:
            raise NotFoundError('Student not found.', code='STUDENT_NOT_FOUND')

        # O checkout aberto volta para o link antigo depois de pago (e cairia
        # em "Link inválido"): o próximo "Pagar" cria outro
        await self._cancel_open_checkouts(academy_id, student_id)
        return pay_url(token)

    async def _cancel_open_checkouts(
        self, academy_id: int, student_id: int
    ) -> None:
        """Faz o Katsuflow parar de reaproveitar os links abertos do aluno."""
        await self.db_session.execute(
            update(InfinitePayCheckout)
            .where(
                InfinitePayCheckout.academy_id == academy_id,
                InfinitePayCheckout.student_id == student_id,
                InfinitePayCheckout.status == CheckoutStatus.OPEN,
            )
            .values(status=CheckoutStatus.CANCELED)
        )

    async def public_payment(
        self, token: str, today: date | None = None
    ) -> PublicPaymentRead | None:
        """Página pública /pagar: o que há a pagar (vencido e o do mês) e o
        código Pix.

        None quando o código não existe ou a academia está bloqueada.
        """
        row = (
            await self.db_session.execute(
                select(Student.id, Student.academy_id, Academy.name)
                .join(Academy, Academy.id == Student.academy_id)
                .where(
                    Student.pay_token == token,
                    Academy.status == AcademyStatus.ACTIVE,
                )
            )
        ).one_or_none()
        if row is None:
            return None

        student_id, academy_id, academy_name = row
        today = today or local_today()
        overdue = await self.payable_for_student(academy_id, student_id, today)
        contact = (await self.contacts(academy_id, {student_id}))[student_id]
        recipient = choose_recipient(contact, today)
        to_responsible = recipient is not None and recipient[1]
        greeting = recipient[0].name if recipient else contact.name
        settings = await self.get_settings(academy_id)
        total = sum((c.open_amount for c in overdue), ZERO)

        checkout_enabled = await self.checkout_enabled(academy_id)

        pix_code = None
        if overdue and not checkout_enabled and has_pix(settings):
            pix_code = pix_copy_paste(
                settings.pix_key,
                settings.recipient_name or academy_name,
                settings.pix_city,
                total,
            )

        return PublicPaymentRead(
            academy_name=academy_name,
            master_name=(await self.academy_master(academy_id))[0],
            greeting_name=' '.join(greeting.split()),
            status='open' if overdue else 'clear',
            items=[
                PublicPaymentItemRead(
                    label=_public_label(
                        charge,
                        today.year,
                        contact.name.split()[0] if to_responsible else None,
                        len({c.modality_name for c in overdue}) > 1,
                    ),
                    amount=charge.open_amount,
                )
                for charge in overdue
            ],
            total=total.quantize(CENTS),
            recipient_name=settings.recipient_name or academy_name,
            pix_code=pix_code,
            checkout_enabled=checkout_enabled,
        )

    async def pay_token_owner(self, token: str) -> tuple[int, int] | None:
        """(academy_id, student_id) do dono do link /pagar; None quando o
        código não existe ou a academia está bloqueada."""
        row = (
            await self.db_session.execute(
                select(Student.academy_id, Student.id)
                .join(Academy, Academy.id == Student.academy_id)
                .where(
                    Student.pay_token == token,
                    Academy.status == AcademyStatus.ACTIVE,
                )
            )
        ).one_or_none()
        return (row.academy_id, row.id) if row else None

    async def overdue_for_student(
        self, academy_id: int, student_id: int, today: date
    ) -> list[ChargeRead]:
        """O que o aluno deve hoje (vencido), do mais antigo ao mais novo:
        é o que a página /pagar mostra e o que o checkout cobra."""
        return sorted(
            (
                c
                for c in await self._charges(
                    academy_id, today, Enrollment.student_id == student_id
                )
                if c.status == 'overdue'
            ),
            key=lambda c: (c.reference_month, c.kind is PaymentKind.MONTHLY),
        )

    async def payable_for_student(
        self, academy_id: int, student_id: int, today: date
    ) -> list[ChargeRead]:
        """O que o aluno pode pagar hoje, do mais antigo ao mais novo: o
        vencido mais a cobrança em aberto que vence até o fim do mês de hoje.
        É o que a página /pagar mostra e o que o checkout cobra e confere."""
        month_end = date(
            today.year,
            today.month,
            calendar.monthrange(today.year, today.month)[1],
        )
        return sorted(
            (
                c
                for c in await self._charges(
                    academy_id, today, Enrollment.student_id == student_id
                )
                if c.status not in CLOSED_STATUSES and c.due_date <= month_end
            ),
            key=lambda c: (c.reference_month, c.kind is PaymentKind.MONTHLY),
        )

    async def checkout_enabled(self, academy_id: int) -> bool:
        """Baixa automática ligada (tag e chave salvas e testadas)."""
        row = (
            await self.db_session.execute(
                select(
                    AcademyBillingSettings.infinitepay_enabled,
                    AcademyBillingSettings.infinitepay_handle,
                    AcademyBillingSettings.infinitepay_api_key,
                ).where(AcademyBillingSettings.academy_id == academy_id)
            )
        ).one_or_none()
        return bool(row and row[0] and row[1] and row[2])

    async def _whatsapp_url_for(
        self,
        academy_id: int,
        student_id: int,
        charges: list[ChargeRead],
        today: date,
    ) -> str | None:
        overdue = [c for c in charges if c.status == 'overdue']
        if not overdue:
            return None

        contacts = await self.contacts(academy_id, {student_id})
        return whatsapp_url(
            contacts[student_id],
            overdue,
            await self.get_settings(academy_id),
            await self._sender(academy_id),
            today,
        )

    async def _open_or_month_charges(
        self, academy_id: int, month: date, today: date
    ) -> list[ChargeRead]:
        """Tudo em aberto (qualquer mês) e tudo do mês escolhido."""
        return await self._charges(
            academy_id,
            today,
            or_(
                and_(
                    Payment.status != PaymentStatus.WAIVED,
                    Payment.amount_paid < Payment.amount_due,
                ),
                Payment.reference_month == month,
            ),
        )

    async def overview(  # noqa: PLR0913, PLR0914
        self,
        academy_id: int,
        *,
        month: date | None,
        status_filter: OverviewFilter,
        search: str | None,
        page: int,
        page_size: int,
    ) -> BillingOverviewRead:
        """Página Mensalidades: números do mês e alunos do filtro."""
        today = local_today()
        month = month or today.replace(day=1)
        charges = await self._open_or_month_charges(academy_id, month, today)

        in_month = [c for c in charges if c.reference_month == month]
        overdue = [c for c in charges if c.status == 'overdue']
        due_soon = [
            c
            for c in charges
            if c.status in {'upcoming', 'partial'}
            and c.due_date <= today + timedelta(days=DUE_SOON_DAYS)
        ]
        scopes: dict[str, list[ChargeRead]] = {
            'overdue': overdue,
            'upcoming': [
                c for c in in_month if c.status in {'upcoming', 'partial'}
            ],
            'paid': [c for c in in_month if c.status == 'paid'],
            'all': in_month,
        }
        scope = scopes[status_filter]

        by_student: dict[int, list[ChargeRead]] = {}
        for charge in scope:
            by_student.setdefault(charge.student_id, []).append(charge)

        contacts = await self.contacts(academy_id, set(by_student))
        # "Em aberto" é sempre o que o aluno deve (todos os meses); o filtro
        # só decide quais alunos aparecem
        owed: dict[int, Decimal] = {}
        for charge in charges:
            if charge.status not in CLOSED_STATUSES:
                owed[charge.student_id] = (
                    owed.get(charge.student_id, ZERO) + charge.open_amount
                )
        normalized = ' '.join(search.split()).casefold() if search else ''
        settings = await self.get_settings(academy_id)
        sender = await self._sender(academy_id)
        items = []

        for student_id, student_charges in by_student.items():
            contact = contacts[student_id]
            if normalized and normalized not in contact.name.casefold():
                continue

            student_overdue = [
                c for c in overdue if c.student_id == student_id
            ]
            recipient = choose_recipient(contact, today)
            items.append(
                BillingOverviewItemRead(
                    student_id=contact.public_id,
                    name=contact.name,
                    responsible_name=(
                        recipient[0].name
                        if recipient and recipient[1] and student_overdue
                        else None
                    ),
                    modalities=sorted({
                        c.modality_name for c in student_charges
                    }),
                    open_amount=owed.get(student_id, ZERO),
                    days_late=(
                        (today - min(c.due_date for c in student_overdue)).days
                        if student_overdue
                        else None
                    ),
                    whatsapp_url=whatsapp_url(
                        contact, student_overdue, settings, sender, today
                    ),
                )
            )

        # Sempre de A a Z, em todos os filtros
        items.sort(key=lambda item: name_sort_key(item.name))

        start = (page - 1) * page_size
        return BillingOverviewRead(
            month_expected=sum(
                (c.amount for c in in_month if c.status != 'waived'), ZERO
            ),
            month_received=await self._received_in(academy_id, month),
            overdue_total=sum((c.open_amount for c in overdue), ZERO),
            overdue_students=len({c.student_id for c in overdue}),
            due_soon_total=sum((c.open_amount for c in due_soon), ZERO),
            due_soon_students=len({c.student_id for c in due_soon}),
            items=items[start : start + page_size],
            total=len(items),
            page=page,
            page_size=page_size,
        )

    async def _received_in(self, academy_id: int, month: date) -> Decimal:
        received = await self.db_session.scalar(
            select(func.sum(PaymentTransaction.gross_amount)).where(
                PaymentTransaction.academy_id == academy_id,
                PaymentTransaction.received_at >= month,
                PaymentTransaction.received_at < first_monthly_month(month),
            )
        )
        return (received or ZERO).quantize(CENTS)

    async def dashboard_lists(self, academy_id: int) -> DashboardBilling:
        """Inadimplentes (mais atrasados primeiro) e vencem em 7 dias."""
        today = local_today()
        charges = await self._open_or_month_charges(
            academy_id, today.replace(day=1), today
        )
        overdue = [c for c in charges if c.status == 'overdue']
        due_soon = sorted(
            (
                c
                for c in charges
                if c.status in {'upcoming', 'partial'}
                and c.due_date <= today + timedelta(days=DUE_SOON_DAYS)
            ),
            key=lambda c: (c.due_date, c.id),
        )
        contacts = await self.contacts(
            academy_id, {c.student_id for c in [*overdue, *due_soon]}
        )

        by_student: dict[int, list[ChargeRead]] = {}
        for charge in overdue:
            by_student.setdefault(charge.student_id, []).append(charge)

        overdue_students = sorted(
            (
                OverdueStudentRead(
                    student_id=contacts[student_id].public_id,
                    name=contacts[student_id].name,
                    modality=join_names(
                        sorted({c.modality_name for c in student_charges})
                    ),
                    amount=sum((c.open_amount for c in student_charges), ZERO),
                    days_late=(
                        today - min(c.due_date for c in student_charges)
                    ).days,
                )
                for student_id, student_charges in by_student.items()
            ),
            key=lambda item: (-item.days_late, item.name),
        )

        return DashboardBilling(
            overdue=overdue_students[:DASHBOARD_LIMIT],
            due_soon=[
                DueSoonChargeRead(
                    student_id=contacts[c.student_id].public_id,
                    name=contacts[c.student_id].name,
                    modality=c.modality_name,
                    amount=c.open_amount,
                    due_date=c.due_date,
                )
                for c in due_soon[:DASHBOARD_LIMIT]
            ],
            overdue_students=len(by_student),
            due_soon_students=len({c.student_id for c in due_soon}),
            overdue_total=sum((c.open_amount for c in overdue), ZERO),
        )

    async def _payments(
        self,
        academy_id: int,
        today: date,
        *filters: ColumnElement[bool],
    ) -> list[PaymentRead]:
        transactions = (
            await self.db_session.scalars(
                select(PaymentTransaction)
                .where(PaymentTransaction.academy_id == academy_id, *filters)
                .order_by(
                    PaymentTransaction.received_at.desc(),
                    PaymentTransaction.id.desc(),
                )
            )
        ).all()

        if not transactions:
            return []

        allocation_rows = (
            await self.db_session.execute(
                select(
                    PaymentAllocation.payment_transaction_id,
                    PaymentAllocation.allocated_amount,
                    Payment.public_id,
                    Payment.kind,
                    Payment.reference_month,
                )
                .join(Payment, Payment.id == PaymentAllocation.payment_id)
                .where(
                    PaymentAllocation.payment_transaction_id.in_([
                        t.id for t in transactions
                    ])
                )
                .order_by(Payment.due_date, Payment.id)
            )
        ).all()

        receipts = dict(
            (
                await self.db_session.execute(
                    select(
                        InfinitePayCheckout.payment_transaction_id,
                        InfinitePayCheckout.receipt_url,
                    ).where(
                        InfinitePayCheckout.payment_transaction_id.in_([
                            t.id for t in transactions
                        ])
                    )
                )
            ).all()
        )

        allocations: dict[int, list[AllocationRead]] = {}
        for row in allocation_rows:
            allocations.setdefault(row.payment_transaction_id, []).append(
                AllocationRead(
                    charge_public_id=row.public_id,
                    label=_charge_label(
                        row.kind, row.reference_month, today.year
                    ),
                    amount=row.allocated_amount,
                )
            )

        return [
            PaymentRead(
                id=transaction.id,
                public_id=transaction.public_id,
                amount=transaction.gross_amount,
                paid_on=transaction.received_at,
                method=transaction.payment_method,
                notes=transaction.notes,
                allocations=allocations.get(transaction.id, []),
                source=transaction.source,
                receipt_url=receipts.get(transaction.id),
            )
            for transaction in transactions
        ]
