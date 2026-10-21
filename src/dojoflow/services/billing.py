from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from dojoflow.database.transaction import transactional
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.modality import Modality
from dojoflow.models.payment import Payment
from dojoflow.models.payment_allocation import PaymentAllocation
from dojoflow.models.payment_transaction import PaymentTransaction
from dojoflow.schemas.billing import (
    AllocationPreview,
    AllocationRead,
    ChargeRead,
    PaymentRead,
    StudentBillingRead,
)
from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing_rules import (
    OpenCharge,
    allocate_oldest_first,
    billing_status,
    due_date_for,
    first_monthly_month,
    format_brl,
    join_names,
    month_name,
)
from dojoflow.shared.enums import (
    EnrollmentStatus,
    PaymentKind,
    PaymentMethod,
    PaymentStatus,
)
from dojoflow.shared.exceptions import ConflictError

CENTS = Decimal('0.01')
ENROLLMENT_FEE_LABEL = 'taxa de matrícula'
CLOSED_STATUSES = {'paid', 'waived'}


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


def _refresh_paid_status(charge: Payment, paid_on: date | None) -> None:
    """Situação gravada a partir do valor já alocado na cobrança."""
    if charge.status is PaymentStatus.WAIVED:
        return
    if charge.amount_paid >= (charge.amount_due or Decimal(0)):
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
            whatsapp_url=None,
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

        for payment, enrollment_public_id, modality_name in rows:
            amount = payment.amount_due or Decimal(0)
            due_date = payment.due_date or payment.reference_month
            charges.append(
                ChargeRead(
                    id=payment.id,
                    public_id=payment.public_id,
                    kind=payment.kind,
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
