from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.address import Address
from dojoflow.models.enrollment import Enrollment
from dojoflow.models.modality import Modality
from dojoflow.models.responsible import Responsible
from dojoflow.models.student import Student
from dojoflow.models.student_responsible import StudentResponsible
from dojoflow.repositories.academy_modality import AcademyModalityRepository
from dojoflow.repositories.address import AddressRepository
from dojoflow.repositories.enrollment import EnrollmentRepository
from dojoflow.repositories.responsible import ResponsibleRepository
from dojoflow.repositories.student import StudentRepository
from dojoflow.repositories.student_responsible import (
    StudentResponsibleRepository,
)
from dojoflow.schemas.address import AddressCreate
from dojoflow.schemas.enrollment import EnrollmentCreate
from dojoflow.schemas.responsible import ResponsibleCreate
from dojoflow.schemas.student import StudentCreate, StudentRead
from dojoflow.schemas.student_responsible import StudentResponsibleCreate
from dojoflow.shared.enums import StudentResponsibleRelationship, StudentSex
from dojoflow.shared.exceptions import NotFoundError


class StudentService:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        student_repository: StudentRepository,
        enrollment_repository: EnrollmentRepository,
        address_repository: AddressRepository,
        responsible_repository: ResponsibleRepository,
        student_responsible_repository: StudentResponsibleRepository,
        academy_modality_repository: AcademyModalityRepository,
        db_session: AsyncSession,
    ) -> None:
        self.student_repository = student_repository
        self.enrollment_repository = enrollment_repository
        self.address_repository = address_repository
        self.responsible_repository = responsible_repository
        self.student_responsible_repository = student_responsible_repository
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

        address_id = await self._get_address_id_from_context(
            academy_id=academy_id,
            context_data=context_data,
        )

        student_id = await self.student_repository.create(
            StudentCreate(
                academy_id=academy_id,
                address_id=address_id,
                name=context_data['student_name'],
                phone=context_data.get('phone'),
                phone_is_whatsapp=context_data.get('is_whatsapp'),
                cpf=context_data.get('cpf'),
                instagram=context_data.get('instagram'),
                email=context_data.get('email'),
                birth_date=self._parse_birth_date(context_data),
                sex=self._parse_student_sex(context_data),
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

        await self._create_responsibles(
            academy_id=academy_id,
            student_id=student_id,
            context_data=context_data,
        )

        student = await self.student_repository.get_by_id_or_fail(student_id)

        return StudentRead(**student)

    async def list_by_academy(
        self,
        academy_id: int,
        limit: int = 20,
    ) -> list[StudentRead]:
        students = await self.student_repository.list(
            filters=[Student.academy_id == academy_id],
            order_by=[Student.name],
            limit=limit,
        )

        return [StudentRead(**student) for student in students]

    async def search_by_name(
        self,
        academy_id: int,
        search_text: str,
        limit: int = 10,
    ) -> list[StudentRead]:
        normalized_search_text = ' '.join(search_text.strip().split())

        students = await self.student_repository.list(
            filters=[
                Student.academy_id == academy_id,
                Student.name.ilike(f'%{normalized_search_text}%'),
            ],
            order_by=[Student.name],
            limit=limit,
        )

        return [StudentRead(**student) for student in students]

    async def get_details(
        self,
        academy_id: int,
        student_id: int,
    ) -> dict[str, Any]:
        student = await self.student_repository.get_one(
            filters=[
                Student.id == student_id,
                Student.academy_id == academy_id,
            ],
        )

        if student is None:
            raise NotFoundError(
                f'Could not find Student with id {student_id}.'
            )

        enrollments = await self._get_student_enrollments(
            academy_id=academy_id,
            student_id=student_id,
        )
        address = await self._get_student_address(
            academy_id=academy_id,
            student=student,
        )
        responsibles = await self._get_student_responsibles(
            academy_id=academy_id,
            student_id=student_id,
        )

        return {
            'student': student,
            'enrollments': enrollments,
            'address': address,
            'responsibles': responsibles,
        }

    @transactional
    async def update_basic_data(
        self,
        academy_id: int,
        student_id: int,
        data: dict[str, Any],
    ) -> None:
        student = await self.student_repository.get_one(
            filters=[
                Student.id == student_id,
                Student.academy_id == academy_id,
            ],
        )

        if student is None:
            raise NotFoundError(
                f'Could not find Student with id {student_id}.'
            )

        update_data = dict(data)
        birth_date = update_data.get('birth_date')

        if birth_date is not None:
            update_data['birth_date'] = date.fromisoformat(str(birth_date))

        sex = update_data.get('sex')

        if sex is not None:
            update_data['sex'] = self._parse_student_sex({
                'sex': sex,
            })

        await self.student_repository.update_by_id(
            record_id=student_id,
            data=update_data,
        )

    @transactional
    async def update_modality(
        self,
        academy_id: int,
        student_id: int,
        modality_id: int,
    ) -> None:
        await self._ensure_modality_belongs_to_academy(
            academy_id=academy_id,
            modality_id=modality_id,
        )

        enrollments = await self.enrollment_repository.list(
            fields=[
                Enrollment.id,
                Enrollment.modality_id,
            ],
            filters=[
                Enrollment.academy_id == academy_id,
                Enrollment.student_id == student_id,
            ],
            order_by=[Enrollment.id],
            limit=1,
        )

        if not enrollments:
            raise NotFoundError(
                f'Could not find Enrollment for student id {student_id}.'
            )

        enrollment = enrollments[0]

        if enrollment['modality_id'] == modality_id:
            return

        await self.enrollment_repository.update_by_id(
            record_id=enrollment['id'],
            data={
                'modality_id': modality_id,
            },
        )

    @transactional
    async def update_enrollment(
        self,
        academy_id: int,
        student_id: int,
        data: dict[str, Any],
    ) -> None:
        enrollments = await self.enrollment_repository.list(
            fields=[Enrollment.id],
            filters=[
                Enrollment.academy_id == academy_id,
                Enrollment.student_id == student_id,
            ],
            order_by=[Enrollment.id],
            limit=1,
        )

        if not enrollments:
            raise NotFoundError(
                f'Could not find Enrollment for student id {student_id}.'
            )

        update_data = dict(data)
        monthly_fee = update_data.get('monthly_fee')

        if monthly_fee is not None:
            update_data['monthly_fee'] = Decimal(str(monthly_fee))

        await self.enrollment_repository.update_by_id(
            record_id=enrollments[0]['id'],
            data=update_data,
        )

    @transactional
    async def update_address(
        self,
        academy_id: int,
        student_id: int,
        address_data: dict[str, Any],
    ) -> None:
        student = await self._get_student_or_fail(
            academy_id=academy_id,
            student_id=student_id,
        )

        has_address_data = any(
            address_data.get(field)
            for field in (
                'zip_code',
                'street',
                'number',
                'complement',
                'neighborhood',
                'city',
                'state',
            )
        )

        if not has_address_data:
            await self.student_repository.update_by_id(
                record_id=student_id,
                data={'address_id': None},
            )
            return

        address_id = await self.address_repository.create(
            AddressCreate(
                academy_id=academy_id,
                zip_code=address_data.get('zip_code'),
                street=address_data.get('street'),
                number=address_data.get('number'),
                complement=address_data.get('complement'),
                neighborhood=address_data.get('neighborhood'),
                city=address_data.get('city'),
                state=address_data.get('state'),
            )
        )

        await self.student_repository.update_by_id(
            record_id=int(student['id']),
            data={'address_id': address_id},
        )

    @transactional
    async def reuse_address(
        self,
        academy_id: int,
        student_id: int,
        reference_student_id: int,
    ) -> None:
        await self._get_student_or_fail(
            academy_id=academy_id,
            student_id=student_id,
        )

        reference_address_id = await self._get_reference_student_address_id(
            academy_id=academy_id,
            student_id=reference_student_id,
        )

        await self.student_repository.update_by_id(
            record_id=student_id,
            data={'address_id': reference_address_id},
        )

    @transactional
    async def remove_address(
        self,
        academy_id: int,
        student_id: int,
    ) -> None:
        await self._get_student_or_fail(
            academy_id=academy_id,
            student_id=student_id,
        )

        await self.student_repository.update_by_id(
            record_id=student_id,
            data={'address_id': None},
        )

    async def _get_student_address(
        self,
        academy_id: int,
        student: dict[str, Any],
    ) -> dict[str, Any] | None:
        address_id = student.get('address_id')

        if address_id is None:
            return None

        address = await self.address_repository.get_one(
            filters=[
                Address.id == address_id,
                Address.academy_id == academy_id,
            ],
        )

        return address

    async def _get_student_enrollments(
        self,
        academy_id: int,
        student_id: int,
    ) -> list[dict[str, Any]]:
        smt = (
            select(
                Enrollment.id.label('enrollment_id'),
                Enrollment.status,
                Enrollment.monthly_fee,
                Enrollment.due_day,
                Enrollment.is_exempt,
                Modality.name.label('modality_name'),
            )
            .join(Modality, Modality.id == Enrollment.modality_id)
            .where(
                Enrollment.academy_id == academy_id,
                Enrollment.student_id == student_id,
            )
            .order_by(Modality.name)
        )

        result = await self.db_session.execute(smt)

        return [dict(row) for row in result.mappings().all()]

    async def _get_student_or_fail(
        self,
        academy_id: int,
        student_id: int,
    ) -> dict[str, Any]:
        student = await self.student_repository.get_one(
            filters=[
                Student.id == student_id,
                Student.academy_id == academy_id,
            ],
        )

        if student is None:
            raise NotFoundError(
                f'Could not find Student with id {student_id}.'
            )

        return student

    async def _get_student_responsibles(
        self,
        academy_id: int,
        student_id: int,
    ) -> list[dict[str, Any]]:
        smt = (
            select(
                StudentResponsible.id,
                StudentResponsible.academy_id,
                StudentResponsible.student_id,
                StudentResponsible.responsible_id,
                StudentResponsible.relationship,
                Responsible.name,
                Responsible.phone,
                Responsible.phone_is_whatsapp,
                Responsible.email,
            )
            .join(
                Responsible,
                Responsible.id == StudentResponsible.responsible_id,
            )
            .where(
                StudentResponsible.academy_id == academy_id,
                StudentResponsible.student_id == student_id,
            )
            .order_by(Responsible.name)
        )

        result = await self.db_session.execute(smt)

        return [dict(row) for row in result.mappings().all()]

    async def _get_address_id_from_context(
        self,
        academy_id: int,
        context_data: dict[str, Any],
    ) -> int | None:
        address_reference_student_id = context_data.get(
            'address_reference_student_id',
        )

        if address_reference_student_id is not None:
            return await self._get_reference_student_address_id(
                academy_id=academy_id,
                student_id=int(address_reference_student_id),
            )

        return await self._create_address_from_context(
            academy_id=academy_id,
            context_data=context_data,
        )

    async def _get_reference_student_address_id(
        self,
        academy_id: int,
        student_id: int,
    ) -> int:
        student = await self.student_repository.get_one(
            filters=[
                Student.id == student_id,
                Student.academy_id == academy_id,
            ],
        )

        if student is None:
            raise NotFoundError(
                f'Could not find Student with id {student_id}.'
            )

        address_id = student.get('address_id')

        if address_id is None:
            raise NotFoundError(
                f'Student with id {student_id} does not have address.'
            )

        return int(address_id)

    async def _create_address_from_context(
        self,
        academy_id: int,
        context_data: dict[str, Any],
    ) -> int | None:
        address = context_data.get('address')

        if not isinstance(address, dict):
            return None

        has_address_data = any(
            address.get(field)
            for field in (
                'zip_code',
                'street',
                'neighborhood',
                'city',
                'state',
                'number',
                'complement',
            )
        )

        if not has_address_data:
            return None

        return await self.address_repository.create(
            AddressCreate(
                academy_id=academy_id,
                zip_code=address.get('zip_code'),
                street=address.get('street'),
                neighborhood=address.get('neighborhood'),
                city=address.get('city'),
                state=address.get('state'),
                number=address.get('number'),
                complement=address.get('complement'),
            )
        )

    async def _create_responsibles(
        self,
        academy_id: int,
        student_id: int,
        context_data: dict[str, Any],
    ) -> None:
        responsibles = context_data.get('responsibles', [])

        for responsible in responsibles:
            responsible_id = await self.responsible_repository.create(
                ResponsibleCreate(
                    academy_id=academy_id,
                    name=responsible['name'],
                    phone=responsible['phone'],
                    phone_is_whatsapp=bool(
                        responsible['phone_is_whatsapp'],
                    ),
                    email=responsible.get('email'),
                )
            )

            await self.student_responsible_repository.create(
                StudentResponsibleCreate(
                    academy_id=academy_id,
                    student_id=student_id,
                    responsible_id=responsible_id,
                    relationship=StudentResponsibleRelationship(
                        responsible['relationship'],
                    ),
                )
            )

        await self._create_responsible_references(
            academy_id=academy_id,
            student_id=student_id,
            context_data=context_data,
        )

    async def _create_responsible_references(
        self,
        academy_id: int,
        student_id: int,
        context_data: dict[str, Any],
    ) -> None:
        responsible_references = context_data.get(
            'responsible_references',
            [],
        )

        for responsible_reference in responsible_references:
            responsible_id = int(responsible_reference['responsible_id'])

            exists = await self.responsible_repository.exists(
                filters=[
                    Responsible.id == responsible_id,
                    Responsible.academy_id == academy_id,
                ],
            )

            if not exists:
                raise NotFoundError(
                    f'Could not find Responsible with id {responsible_id}.'
                )

            await self.student_responsible_repository.create(
                StudentResponsibleCreate(
                    academy_id=academy_id,
                    student_id=student_id,
                    responsible_id=responsible_id,
                    relationship=StudentResponsibleRelationship(
                        responsible_reference['relationship'],
                    ),
                )
            )

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
    def _parse_student_sex(
        context_data: dict[str, Any],
    ) -> StudentSex:
        sex_mapping = {
            'male': StudentSex.MALE,
            'masculino': StudentSex.MALE,
            'female': StudentSex.FEMALE,
            'feminino': StudentSex.FEMALE,
            'other': StudentSex.OTHER,
            'outros': StudentSex.OTHER,
            'outro': StudentSex.OTHER,
        }

        sex = str(context_data['sex']).strip().lower()

        return sex_mapping[sex]

    @staticmethod
    def _parse_birth_date(
        context_data: dict[str, Any],
    ) -> date | None:
        birth_date = context_data.get('birth_date')

        if birth_date is None:
            return None

        return date.fromisoformat(birth_date)
