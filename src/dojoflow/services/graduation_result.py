from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.models.enrollment_belt import EnrollmentBelt
from dojoflow.models.graduation_list import GraduationList, GraduationListEntry
from dojoflow.models.payment import Payment
from dojoflow.schemas.belt import BeltRead
from dojoflow.services.belt import BeltService
from dojoflow.services.belt_rules import local_today
from dojoflow.services.enrollment_belt import EnrollmentBeltService
from dojoflow.shared.enums import ExamResult, PaymentStatus
from dojoflow.shared.exceptions import ConflictError, NotFoundError

# Cobrança fechada: libera a aprovação
_SETTLED = {PaymentStatus.PAID, PaymentStatus.WAIVED}


def belts_to_award(
    belts: list[BeltRead],
    current_belt_id: int | None,
    target_belt_id: int,
) -> list[BeltRead]:
    """Faixas que a aprovação grava: as puladas e a alvo, na ordem.

    `belts` vem na ordem da modalidade. Sem faixa atual, faixa atual de
    fora da modalidade ou alvo que não está acima da atual: só a alvo.
    """
    by_id = {belt.id: belt for belt in belts}
    target = by_id[target_belt_id]
    current = by_id.get(current_belt_id) if current_belt_id else None

    if current is None or target.position <= current.position:
        return [target]

    return [
        belt
        for belt in belts
        if current.position < belt.position <= target.position
    ]


class GraduationResultService:
    """Aprovar, reprovar e desfazer o resultado do exame de um aluno."""

    def __init__(
        self,
        db_session: AsyncSession,
        belt_service: BeltService,
        enrollment_belt_service: EnrollmentBeltService,
    ) -> None:
        self.db_session = db_session
        self.belt_service = belt_service
        self.enrollment_belt_service = enrollment_belt_service

    @transactional
    async def approve(
        self,
        academy_id: int,
        list_id: int,
        entry_id: int,
        approved_on: date,
    ) -> None:
        entry = await self._pending_entry(academy_id, list_id, entry_id)
        await self._ensure_settled(entry_id)

        if approved_on > local_today():
            raise ConflictError(
                'The approval date cannot be in the future.',
                code='APPROVAL_DATE_IN_FUTURE',
            )

        current = (
            await self.enrollment_belt_service.current_belts(
                academy_id, [entry.enrollment_id]
            )
        ).get(entry.enrollment_id)

        if current and approved_on < current.graduated_on:
            raise ConflictError(
                'The approval date is before the current belt.',
                code='APPROVAL_DATE_BEFORE_CURRENT_BELT',
            )

        modality_id = await self.db_session.scalar(
            select(GraduationList.modality_id).where(
                GraduationList.id == list_id
            )
        )
        belts = await self.belt_service.list_by_modality(
            academy_id, modality_id
        )

        for belt in belts_to_award(
            belts, current.belt.id if current else None, entry.target_belt_id
        ):
            self.db_session.add(
                EnrollmentBelt(
                    academy_id=academy_id,
                    enrollment_id=entry.enrollment_id,
                    belt_id=belt.id,
                    graduated_on=approved_on,
                    graduation_entry_id=entry.id,
                )
            )

        entry.result = ExamResult.APPROVED
        entry.result_on = approved_on
        await self.db_session.flush()

    @transactional
    async def fail(self, academy_id: int, list_id: int, entry_id: int) -> None:
        entry = await self._pending_entry(academy_id, list_id, entry_id)
        entry.result = ExamResult.FAILED
        await self.db_session.flush()

    @transactional
    async def undo(self, academy_id: int, list_id: int, entry_id: int) -> None:
        entry = await self._entry(academy_id, list_id, entry_id)
        # Só as faixas que esta aprovação gravou (as que ainda existem)
        await self.db_session.execute(
            delete(EnrollmentBelt).where(
                EnrollmentBelt.academy_id == academy_id,
                EnrollmentBelt.graduation_entry_id == entry.id,
            )
        )
        entry.result = ExamResult.PENDING
        entry.result_on = None
        await self.db_session.flush()

    async def _entry(
        self, academy_id: int, list_id: int, entry_id: int
    ) -> GraduationListEntry:
        # Trava a linha: dois cliques seguidos não gravam faixa duas vezes
        entry = await self.db_session.scalar(
            select(GraduationListEntry)
            .where(
                GraduationListEntry.id == entry_id,
                GraduationListEntry.graduation_list_id == list_id,
                GraduationListEntry.academy_id == academy_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        if entry is None:
            raise NotFoundError(
                'Graduation entry not found.',
                code='GRADUATION_ENTRY_NOT_FOUND',
            )

        return entry

    async def _pending_entry(
        self, academy_id: int, list_id: int, entry_id: int
    ) -> GraduationListEntry:
        entry = await self._entry(academy_id, list_id, entry_id)

        if entry.result != ExamResult.PENDING:
            raise ConflictError(
                'This student already has an exam result.',
                code='RESULT_ALREADY_SET',
            )

        return entry

    async def _ensure_settled(self, entry_id: int) -> None:
        # Sem cobrança (lista sem data limite ou faixa sem preço): liberado
        status = await self.db_session.scalar(
            select(Payment.status).where(
                Payment.graduation_entry_id == entry_id
            )
        )

        if status is not None and status not in _SETTLED:
            raise ConflictError(
                'The graduation must be paid or waived before approval.',
                code='GRADUATION_NOT_PAID',
            )
