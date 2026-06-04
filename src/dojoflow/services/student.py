from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.repositories.academy_modality import AcademyModalityRepository
from dojoflow.repositories.enrollment import EnrollmentRepository
from dojoflow.repositories.student import StudentRepository
from dojoflow.schemas.enrollment import EnrollmentCreate
from dojoflow.schemas.student import StudentCreate, StudentRead
from dojoflow.shared.enums import StudentSex
from dojoflow.shared.exceptions import NotFoundError


class StudentService:
    def __init__(
        self,
        student_repository: StudentRepository,
        enrollment_repository: EnrollmentRepository,
        academy_modality_repository: AcademyModalityRepository,
        db_session: AsyncSession,
    ) -> None:
        self.student_repository = student_repository
        self.enrollment_repository = enrollment_repository
        self.academy_modality_repository = academy_modality_repository
        self.db_session = db_session

    @transactional
    async def create_from_telegram_context(
        self,
        academy_id: int,
        context_data: dict[str, Any],
    ) -> StudentRead:
        modality_id = int(context_data['modality_id'])

        await self._ensure_modality_belongs_to_academy(
            academy_id=academy_id,
            modality_id=modality_id,
        )

        student_id = await self.student_repository.create(
            StudentCreate(
                academy_id=academy_id,
                name=context_data['student_name'],
                phone=context_data.get('phone'),
                phone_is_whatsapp=context_data.get('is_whatsapp'),
                cpf=context_data.get('cpf'),
                instagram=context_data.get('instagram'),
                birth_date=self._parse_birth_date(context_data),
                sex=StudentSex(context_data['sex']),
            )
        )

        await self.enrollment_repository.create(
            EnrollmentCreate(
                academy_id=academy_id,
                student_id=student_id,
                modality_id=modality_id,
                monthly_fee=Decimal(context_data['monthly_fee']),
                due_day=int(context_data['due_day']),
                is_exempt=bool(context_data['is_exempt']),
            )
        )

        student = await self.student_repository.get_by_id_or_fail(student_id)

        return StudentRead(**student)

    async def _ensure_modality_belongs_to_academy(
        self,
        academy_id: int,
        modality_id: int,
    ) -> None:
        exists = await self.academy_modality_repository.exists(
            filters=[
                AcademyModality.academy_id == academy_id,
                AcademyModality.modality_id == modality_id,
            ],
        )

        if not exists:
            raise NotFoundError(
                'This modality is not configured for this academy.'
            )

    @staticmethod
    def _parse_birth_date(
        context_data: dict[str, Any],
    ) -> date | None:
        birth_date = context_data.get('birth_date')

        if birth_date is None:
            return None

        return date.fromisoformat(birth_date)
