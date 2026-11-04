"""Cobranças de graduação: uma por aluno da lista, em dia com a lista
(aluno, faixa-alvo, data limite) e com o preço da faixa.

Cada mudança mexe só no que mudou: um desconto ou um vencimento que o
mestre editou à mão na cobrança não volta ao valor da lista.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.belt import Belt
from dojoflow.models.graduation_list import GraduationList, GraduationListEntry
from dojoflow.models.payment import Payment
from dojoflow.services.belt_rules import local_today
from dojoflow.services.billing import refresh_paid_status
from dojoflow.shared.enums import PaymentKind, PaymentStatus

ZERO = Decimal('0.00')
CLOSED = {PaymentStatus.PAID, PaymentStatus.WAIVED}


class GraduationBillingService:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def _lock_list(self, academy_id: int, list_id: int) -> date | None:
        """Trava a lista (uma sincronização por vez) e devolve a data
        limite."""
        return await self.db_session.scalar(
            select(GraduationList.payment_due_date)
            .where(
                GraduationList.id == list_id,
                GraduationList.academy_id == academy_id,
            )
            .with_for_update()
        )

    async def _charges_by_entry(
        self, entry_ids: list[int]
    ) -> dict[int, Payment]:
        if not entry_ids:
            return {}
        rows = await self.db_session.scalars(
            select(Payment)
            .where(Payment.graduation_entry_id.in_(entry_ids))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return {charge.graduation_entry_id: charge for charge in rows}

    async def _drop_or_close(self, charge: Payment) -> None:
        """A cobrança não é mais devida. Sem nada pago, some; com parte
        paga, fecha no que foi pago (nada fica em aberto sem lista)."""
        if charge.amount_paid <= ZERO:
            await self.db_session.delete(charge)
            return
        charge.amount_due = charge.amount_paid
        refresh_paid_status(charge, local_today())

    async def sync_list(
        self,
        academy_id: int,
        list_id: int,
        *,
        entry_ids: list[int] | None = None,
        reprice: bool = False,
    ) -> None:
        """Cria a cobrança de quem não tem e tira a de quem não deve mais.

        entry_ids: só essas entradas (None = a lista toda).
        reprice: a faixa-alvo mudou; o valor em aberto passa ao preço dela.
        """
        due_date = await self._lock_list(academy_id, list_id)
        filters = [
            GraduationListEntry.graduation_list_id == list_id,
            GraduationListEntry.academy_id == academy_id,
        ]
        if entry_ids is not None:
            filters.append(GraduationListEntry.id.in_(entry_ids))
        rows = (
            await self.db_session.execute(
                select(GraduationListEntry, Belt.name, Belt.price)
                .join(Belt, Belt.id == GraduationListEntry.target_belt_id)
                .where(*filters)
            )
        ).all()
        charges = await self._charges_by_entry([e.id for e, _, _ in rows])

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
                await self._drop_or_close(charge)
                continue
            if reprice:
                charge.description = belt_name
                # Nunca abaixo do que já foi pago: o saldo não fica negativo
                charge.amount_due = max(price, charge.amount_paid)
                refresh_paid_status(charge, charge.paid_at or local_today())

        await self.db_session.flush()

    async def move_deadline(
        self, academy_id: int, list_id: int, old_due_date: date | None
    ) -> None:
        """A data limite da lista mudou: quem ainda vencia na data antiga
        passa à nova; um vencimento editado à mão fica. Depois cria ou tira
        cobranças (data apagada = a lista para de cobrar)."""
        new_due_date = await self._lock_list(academy_id, list_id)

        if new_due_date is not None and old_due_date is not None:
            entry_ids = select(GraduationListEntry.id).where(
                GraduationListEntry.graduation_list_id == list_id
            )
            charges = await self.db_session.scalars(
                select(Payment)
                .where(
                    Payment.academy_id == academy_id,
                    Payment.graduation_entry_id.in_(entry_ids),
                    Payment.status.not_in(CLOSED),
                    Payment.due_date == old_due_date,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            for charge in charges:
                charge.due_date = new_due_date
                charge.reference_month = new_due_date.replace(day=1)

        await self.sync_list(academy_id, list_id)

    async def reprice_belt(
        self, academy_id: int, belt_id: int, old_price: Decimal
    ) -> None:
        """O preço (ou o nome) da faixa mudou. Quem ainda pagava o preço
        antigo passa ao novo; um desconto dado à mão fica."""
        belt = await self.db_session.get(Belt, belt_id, populate_existing=True)
        list_ids = (
            await self.db_session.scalars(
                select(GraduationListEntry.graduation_list_id)
                .where(
                    GraduationListEntry.academy_id == academy_id,
                    GraduationListEntry.target_belt_id == belt_id,
                )
                .distinct()
                .order_by(GraduationListEntry.graduation_list_id)
            )
        ).all()

        for list_id in list_ids:
            await self._lock_list(academy_id, list_id)
            entry_ids = (
                await self.db_session.scalars(
                    select(GraduationListEntry.id).where(
                        GraduationListEntry.graduation_list_id == list_id,
                        GraduationListEntry.target_belt_id == belt_id,
                    )
                )
            ).all()
            for charge in (await self._charges_by_entry(entry_ids)).values():
                if charge.status in CLOSED:
                    continue
                charge.description = belt.name
                if charge.amount_due == old_price and belt.price > ZERO:
                    charge.amount_due = max(belt.price, charge.amount_paid)
                    refresh_paid_status(
                        charge, charge.paid_at or local_today()
                    )
            # Preço que virou zero tira a cobrança; que saiu do zero, cria
            await self.sync_list(academy_id, list_id, entry_ids=entry_ids)

    async def drop_open_charges(
        self, academy_id: int, entry_ids: list[int]
    ) -> None:
        """Antes de tirar alunos da lista: some o que não recebeu nada e
        fecha no valor pago o que recebeu parte. O que já estava pago fica
        (a entrada vira NULL na cobrança)."""
        charges = await self._charges_by_entry(entry_ids)
        for charge in charges.values():
            if charge.academy_id == academy_id and charge.status not in CLOSED:
                await self._drop_or_close(charge)
        await self.db_session.flush()
