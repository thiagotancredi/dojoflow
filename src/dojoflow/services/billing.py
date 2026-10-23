from dataclasses import dataclass
from datetime import date, timedelta
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
from dojoflow.models.modality import Modality
from dojoflow.models.payment import Payment
from dojoflow.models.payment_allocation import PaymentAllocation
from dojoflow.models.payment_transaction import PaymentTransaction
from dojoflow.models.responsible import Responsible
from dojoflow.models.student import Student
from dojoflow.models.student_responsible import StudentResponsible
from dojoflow.schemas.billing import (
    AllocationPreview,
    AllocationRead,
    BillingOverviewItemRead,
    BillingOverviewRead,
    ChargeRead,
    OverviewFilter,
    PaymentRead,
    StudentBillingRead,
)
from dojoflow.schemas.billing_settings_api import BillingSettingsApi
from dojoflow.schemas.dashboard import DueSoonChargeRead, OverdueStudentRead
from dojoflow.services.belt_rules import local_today
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
from dojoflow.shared.enums import (
    EnrollmentStatus,
    PaymentKind,
    PaymentMethod,
    PaymentStatus,
)
from dojoflow.shared.exceptions import ConflictError
from dojoflow.shared.text import name_sort_key

CENTS = Decimal('0.01')
ZERO = Decimal('0.00')
DEFAULT_MESSAGE_TEMPLATE = (
    'Olá, {nome}! Tudo bem? 🥋\n\n'
    'Passando para lembrar que a mensalidade da {academia} está em '
    'aberto: {valor} ({meses}).\n\n'
    'Para pagar pelo Pix, é só tocar aqui:\n{link}\n\n'
    'Se já pagou, desconsidere. Obrigado!'
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


@dataclass(frozen=True)
class StudentContact:
    public_id: UUID
    name: str
    phone: str | None
    birth_date: date | None
    responsibles: tuple[Contact, ...]
    pay_token: str


def choose_recipient(
    student: StudentContact, today: date
) -> tuple[Contact, bool] | None:
    """Quem recebe a cobrança: (contato, é responsável?).

    Menor de 18 com responsável com telefone: o primeiro responsável.
    Senão o próprio aluno; sem telefone dele, um responsável.
    """
    own = [(Contact(student.name, student.phone), False)]
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


def whatsapp_url(  # noqa: PLR0913, PLR0917
    student: StudentContact,
    overdue_charges: list[ChargeRead],
    settings: BillingSettingsApi,
    academy_name: str,
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
        '{academia}': academy_name,
        '{valor}': format_brl(overdue_total),
        '{meses}': open_label(overdue_charges, today.year),
        '{pix}': settings.pix_key or '',
        '{recebedor}': settings.recipient_name or academy_name,
        '{link}': pay_url(student.pay_token),
    }
    text = settings.message_template or DEFAULT_MESSAGE_TEMPLATE
    if '{link}' not in text:
        text += LINK_FALLBACK
    # Troca simples: chaves que o mestre escrever no texto não quebram nada
    for marker, value in values.items():
        text = text.replace(marker, value)

    return f'https://wa.me/{whatsapp_phone(contact.phone)}?text={quote(text)}'


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


class BillingService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    @transactional
    async def ensure_monthly_charges(
        self,
        academy_id: int | None,
        today: date,
    ) -> int:
        """Cria as mensalidades que faltam até o mês de hoje.

        academy_id=None: todas as academias (disparo diário). Pode rodar
        quantas vezes quiser: um mês que já existe nunca é criado de novo.
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

        # Duas gerações ao mesmo tempo (disparo diário + tela aberta):
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
        await self.ensure_monthly_charges(academy_id, today)

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
        )

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

    async def _lock_student_charges(
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
        # As mensalidades do mês nascem quando alguém abre as telas; garante
        # que existam antes de abater
        await self.ensure_monthly_charges(academy_id, local_today())
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
    ) -> PaymentRead:
        """Baixa do aluno, abatendo da cobrança mais antiga à mais nova."""
        today = local_today()
        locked = await self._lock_student_charges(academy_id, student_id)
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
        locked = await self._lock_student_charges(academy_id, student_id)
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

    async def _contacts(
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
                Contact(link.name, link.phone)
            )

        return {
            row.id: StudentContact(
                public_id=row.public_id,
                name=row.name,
                phone=row.phone,
                birth_date=row.birth_date,
                responsibles=tuple(responsibles.get(row.id, [])),
                pay_token=row.pay_token,
            )
            for row in students
        }

    async def _academy_name(self, academy_id: int) -> str:
        return (
            await self.db_session.scalar(
                select(Academy.name).where(Academy.id == academy_id)
            )
            or ''
        )

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

        contacts = await self._contacts(academy_id, {student_id})
        return whatsapp_url(
            contacts[student_id],
            overdue,
            await self.get_settings(academy_id),
            await self._academy_name(academy_id),
            today,
        )

    async def _open_or_month_charges(
        self, academy_id: int, month: date, today: date
    ) -> list[ChargeRead]:
        """Tudo em aberto (qualquer mês) e tudo do mês escolhido."""
        await self.ensure_monthly_charges(academy_id, today)
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

        contacts = await self._contacts(academy_id, set(by_student))
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
        academy_name = await self._academy_name(academy_id)
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
                        contact, student_overdue, settings, academy_name, today
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
        contacts = await self._contacts(
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
            )
            for transaction in transactions
        ]
