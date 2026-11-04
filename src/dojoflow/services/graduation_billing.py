"""Cobranças de graduação: uma por aluno da lista, sempre em dia com a
lista (aluno, faixa-alvo, data limite) e com o preço da faixa."""

from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.belt import Belt
from dojoflow.models.graduation_list import GraduationList, GraduationListEntry
from dojoflow.models.payment import Payment
from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing import refresh_paid_status
from dojoflow.shared.enums import PaymentKind, PaymentStatus

ZERO = Decimal('0.00')
CLOSED = {PaymentStatus.PAID, PaymentStatus.WAIVED}


def _untouched(charge: Payment) -> bool:
    """Em aberto e sem nada pago: pode sumir sem perder dinheiro."""
    return charge.status not in CLOSED and charge.amount_paid <= ZERO


class GraduationBillingService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def sync_list(self, academy_id: int, list_id: int) -> None:
        """Deixa as cobranças da lista como devem estar agora.

        Com data limite e faixa com preço: uma cobrança por aluno. A que
        está em aberto acompanha preço, faixa e data; a paga, a dispensada
        ou a que já recebeu algo não muda de valor para baixo do pago.
        """
        due_date = await self.db_session.scalar(
            select(GraduationList.payment_due_date).where(
                GraduationList.id == list_id,
                GraduationList.academy_id == academy_id,
            )
        )
        rows = (
            await self.db_session.execute(
                select(GraduationListEntry, Belt.name, Belt.price)
                .join(Belt, Belt.id == GraduationListEntry.target_belt_id)
                .where(
                    GraduationListEntry.graduation_list_id == list_id,
                    GraduationListEntry.academy_id == academy_id,
                )
            )
        ).all()
        if not rows:
            return

        charges = {
            charge.graduation_entry_id: charge
            for charge in await self.db_session.scalars(
                select(Payment)
                .where(
                    Payment.graduation_entry_id.in_([
                        entry.id for entry, _, _ in rows
                    ])
                )
                .with_for_update()
            )
        }

        for entry, belt_name, price in rows:
            charge = charges.get(entry.id)
            wanted = due_date is not None and price > ZERO

            if charge is None:
                if wanted:
                    self.db_session.add(
                        Payment(
                            academy_id=academy_id,
                            enrollment_id=entry.enrollment_id,
                            kind=PaymentKind.GRADUATION,
                            graduation_entry_id=entry.id,
                            description=belt_name,
                            reference_month=due_date.replace(day=1),
                            due_date=due_date,
                            amount_due=price,
                            amount_paid=ZERO,
                            status=PaymentStatus.PENDING,
                        )
                    )
                continue

            if charge.status in CLOSED:
                continue

            if not wanted:
                if _untouched(charge):
                    await self.db_session.delete(charge)
                continue

            # Nunca abaixo do que já foi pago: o saldo não fica negativo
            charge.amount_due = max(price, charge.amount_paid)
            charge.description = belt_name
            charge.due_date = due_date
            charge.reference_month = due_date.replace(day=1)
            refresh_paid_status(charge, charge.paid_at or local_today())

        await self.db_session.flush()

    async def sync_belt(self, academy_id: int, belt_id: int) -> None:
        """O preço da faixa mudou: atualiza as listas que a usam."""
        list_ids = await self.db_session.scalars(
            select(GraduationListEntry.graduation_list_id)
            .where(
                GraduationListEntry.academy_id == academy_id,
                GraduationListEntry.target_belt_id == belt_id,
            )
            .distinct()
        )
        for list_id in list_ids.all():
            await self.sync_list(academy_id, list_id)

    async def drop_open_charges(
        self, academy_id: int, entry_ids: list[int]
    ) -> None:
        """Antes de tirar alunos da lista: some o que não recebeu nada; o
        que já foi pago fica (a entrada vira NULL na cobrança)."""
        if not entry_ids:
            return
        await self.db_session.execute(
            delete(Payment).where(
                Payment.academy_id == academy_id,
                Payment.graduation_entry_id.in_(entry_ids),
                Payment.status.not_in(CLOSED),
                Payment.amount_paid <= ZERO,
            )
        )
