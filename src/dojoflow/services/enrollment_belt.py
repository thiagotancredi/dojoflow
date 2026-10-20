from typing import Any

from sqlalchemy import Select, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.models.belt import Belt
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.enrollment_belt import EnrollmentBelt
from dojoflow.models.student import Student
from dojoflow.repositories.enrollment_belt import EnrollmentBeltRepository
from dojoflow.schemas.belt import BeltRead
from dojoflow.schemas.enrollment_belt import (
    BeltRecord,
    EnrollmentBeltPayload,
    PendingBeltEnrollment,
)
from dojoflow.services.belt import BeltService
from dojoflow.shared.enums import EnrollmentStatus
from dojoflow.shared.exceptions import ConflictError, NotFoundError

BELT_PREFIX = 'belt_'

# Colunas da faixa com prefixo, para não colidir com as do registro
_BELT_COLUMNS = [
    column.label(f'{BELT_PREFIX}{column.name}')
    for column in Belt.__table__.columns
]


def _records_query() -> Select[Any]:
    return select(
        EnrollmentBelt.id,
        EnrollmentBelt.public_id,
        EnrollmentBelt.enrollment_id,
        EnrollmentBelt.graduated_on,
        *_BELT_COLUMNS,
    ).join(Belt, Belt.id == EnrollmentBelt.belt_id)


def _to_record(row: Any) -> BeltRecord:
    belt = {
        key.removeprefix(BELT_PREFIX): value
        for key, value in row.items()
        if key.startswith(BELT_PREFIX)
    }

    return BeltRecord(
        id=row['id'],
        public_id=row['public_id'],
        enrollment_id=row['enrollment_id'],
        graduated_on=row['graduated_on'],
        belt=BeltRead(**belt),
    )


# Faixa atual = data mais recente; empate: o registro criado por último
_NEWEST_FIRST = (EnrollmentBelt.graduated_on.desc(), EnrollmentBelt.id.desc())


class EnrollmentBeltService:
    def __init__(
        self,
        enrollment_belt_repository: EnrollmentBeltRepository,
        belt_service: BeltService,
        db_session: AsyncSession,
    ) -> None:
        self.enrollment_belt_repository = enrollment_belt_repository
        self.belt_service = belt_service
        self.db_session = db_session

    async def list_history(
        self,
        academy_id: int,
        enrollment_id: int,
    ) -> list[BeltRecord]:
        stmt = _records_query().where(
            EnrollmentBelt.academy_id == academy_id,
            EnrollmentBelt.enrollment_id == enrollment_id,
        )
        result = await self.db_session.execute(stmt.order_by(*_NEWEST_FIRST))

        return [_to_record(row) for row in result.mappings().all()]

    async def current_belts(
        self,
        academy_id: int,
        enrollment_ids: list[int],
    ) -> dict[int, BeltRecord]:
        if not enrollment_ids:
            return {}

        stmt = (
            _records_query()
            .where(
                EnrollmentBelt.academy_id == academy_id,
                EnrollmentBelt.enrollment_id.in_(enrollment_ids),
            )
            .distinct(EnrollmentBelt.enrollment_id)
            .order_by(EnrollmentBelt.enrollment_id, *_NEWEST_FIRST)
        )
        result = await self.db_session.execute(stmt)

        return {
            record.enrollment_id: record
            for record in (_to_record(row) for row in result.mappings().all())
        }

    async def list_pending(
        self,
        academy_id: int,
        modality_id: int,
    ) -> list[PendingBeltEnrollment]:
        has_belt = exists().where(
            EnrollmentBelt.enrollment_id == Enrollment.id
        )
        stmt = (
            select(
                Enrollment.id.label('enrollment_id'),
                Enrollment.public_id.label('enrollment_public_id'),
                Student.public_id.label('student_public_id'),
                Student.name.label('student_name'),
            )
            .join(Student, Student.id == Enrollment.student_id)
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.modality_id == modality_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
                ~has_belt,
            )
            .order_by(Student.name, Enrollment.id)
        )
        result = await self.db_session.execute(stmt)

        return [
            PendingBeltEnrollment(**row) for row in result.mappings().all()
        ]

    @transactional
    async def bulk_add(
        self,
        academy_id: int,
        modality_id: int,
        items: list[tuple[int, EnrollmentBeltPayload]],
    ) -> int:
        enrollment_ids = [enrollment_id for enrollment_id, _ in items]

        if len(enrollment_ids) != len(set(enrollment_ids)):
            raise ConflictError(
                'The same enrollment appears more than once.',
                code='DUPLICATE_ENROLLMENT_IN_BATCH',
            )

        rows = await self.db_session.execute(
            select(Enrollment.id, Enrollment.modality_id).where(
                Enrollment.academy_id == academy_id,
                Enrollment.id.in_(enrollment_ids),
            )
        )
        modality_by_enrollment = dict(rows.tuples().all())
        pending_ids = {
            pending.enrollment_id
            for pending in await self.list_pending(academy_id, modality_id)
        }

        for enrollment_id, data in items:
            if modality_by_enrollment.get(enrollment_id) != modality_id:
                raise ConflictError(
                    'This enrollment belongs to another modality.',
                    code='ENROLLMENT_MODALITY_MISMATCH',
                )

            # Só matrícula ativa e ainda sem faixa (tela pode estar velha)
            if enrollment_id not in pending_ids:
                raise ConflictError(
                    'This enrollment is inactive or already has a belt.',
                    code='ENROLLMENT_NOT_PENDING',
                )

            await self.add(academy_id, enrollment_id, data)

        return len(items)

    @transactional
    async def add(
        self,
        academy_id: int,
        enrollment_id: int,
        data: EnrollmentBeltPayload,
    ) -> None:
        await self._ensure_belt_matches_enrollment(
            academy_id, enrollment_id, data.belt_id
        )

        await self.enrollment_belt_repository.create({
            'academy_id': academy_id,
            'enrollment_id': enrollment_id,
            'belt_id': data.belt_id,
            'graduated_on': data.graduated_on,
        })

    @transactional
    async def add_for_modality(
        self,
        academy_id: int,
        student_id: int,
        modality_id: int,
        data: EnrollmentBeltPayload,
    ) -> None:
        enrollment_id = await self.db_session.scalar(
            select(Enrollment.id).where(
                Enrollment.academy_id == academy_id,
                Enrollment.student_id == student_id,
                Enrollment.modality_id == modality_id,
            )
        )

        if enrollment_id is None:
            raise NotFoundError(
                'Could not find this enrollment.',
                code='ENROLLMENT_NOT_FOUND',
            )

        await self.add(academy_id, enrollment_id, data)

    @transactional
    async def update(
        self,
        academy_id: int,
        enrollment_id: int,
        record_id: int,
        data: EnrollmentBeltPayload,
    ) -> None:
        await self._ensure_belt_matches_enrollment(
            academy_id, enrollment_id, data.belt_id
        )

        await self.enrollment_belt_repository.update_by_id(
            record_id,
            {'belt_id': data.belt_id, 'graduated_on': data.graduated_on},
        )

    @transactional
    async def delete(
        self,
        academy_id: int,
        enrollment_id: int,
        record_id: int,
    ) -> None:
        await self.enrollment_belt_repository.delete_by_id(record_id)

    async def _ensure_belt_matches_enrollment(
        self,
        academy_id: int,
        enrollment_id: int,
        belt_id: int,
    ) -> None:
        modality_id = await self.db_session.scalar(
            select(Enrollment.modality_id).where(
                Enrollment.id == enrollment_id,
                Enrollment.academy_id == academy_id,
            )
        )

        if modality_id is None:
            raise NotFoundError(
                'Could not find this enrollment.',
                code='ENROLLMENT_NOT_FOUND',
            )

        belt = await self.belt_service.get(academy_id, belt_id)

        if belt.modality_id != modality_id:
            raise ConflictError(
                'This belt belongs to another modality.',
                code='BELT_MODALITY_MISMATCH',
            )
