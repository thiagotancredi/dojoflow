from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.academy_modality import AcademyModality
from dojoflow.models.address import Address
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
from dojoflow.services.student import StudentService
from dojoflow.shared.exceptions import NotFoundError
from tests.helpers.onboarding import register_onboarding

EXPECTED_SHARED_RESPONSIBLE_LINKS_COUNT = 2


def _make_student_context(
    student_name: str,
    modality_id: int,
    address_reference_student_id: int | None = None,
) -> dict[str, Any]:
    context_data: dict[str, Any] = {
        'student_name': student_name,
        'modality_id': modality_id,
        'sex': 'male',
        'cpf': None,
        'instagram': None,
        'email': None,
        'birth_date': None,
        'monthly_fee': '250',
        'due_day': 7,
        'is_exempt': False,
        'responsibles': [
            {
                'relationship': 'self',
                'name': student_name,
                'phone': '62999999999',
                'phone_is_whatsapp': True,
                'email': None,
            }
        ],
    }

    if address_reference_student_id is None:
        context_data['address'] = {
            'zip_code': '74815705',
            'street': 'Rua Natal',
            'neighborhood': 'Alto da Glória',
            'city': 'Goiânia',
            'state': 'GO',
            'number': '327',
            'complement': 'Casa 2',
        }
        return context_data

    context_data['address_reference_student_id'] = address_reference_student_id

    return context_data


def _make_student_service(db_session: AsyncSession) -> StudentService:
    return StudentService(
        student_repository=StudentRepository(db_session=db_session),
        enrollment_repository=EnrollmentRepository(db_session=db_session),
        address_repository=AddressRepository(db_session=db_session),
        responsible_repository=ResponsibleRepository(db_session=db_session),
        student_responsible_repository=StudentResponsibleRepository(
            db_session=db_session,
        ),
        academy_modality_repository=AcademyModalityRepository(
            db_session=db_session,
        ),
        db_session=db_session,
    )


async def _setup_academy_with_modality(
    client: AsyncClient,
    db_session: AsyncSession,
    academy_name: str,
    telegram_user_id: int,
) -> tuple[int, int]:
    onboarding_response, _ = await register_onboarding(
        client,
        academy_name=academy_name,
        telegram_user_id=telegram_user_id,
    )
    onboarding_body = onboarding_response.json()

    modality = Modality(
        name=f'Taekwondo {academy_name}',
        emoji='🥋',
        is_active=True,
    )
    db_session.add(modality)
    await db_session.flush()

    academy_modality = AcademyModality(
        academy_id=onboarding_body['academy_id'],
        modality_id=modality.id,
    )
    db_session.add(academy_modality)
    await db_session.commit()

    return onboarding_body['academy_id'], modality.id


@pytest.mark.asyncio
async def test_create_student_reusing_address_from_another_student(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    academy_id, modality_id = await _setup_academy_with_modality(
        client=client,
        db_session=db_session,
        academy_name='Academia Luna',
        telegram_user_id=100000001,
    )

    student_service = _make_student_service(db_session)

    first_student = await student_service.create_from_telegram_context(
        academy_id=academy_id,
        context_data=_make_student_context(
            student_name='Luna',
            modality_id=modality_id,
        ),
    )

    second_student = await student_service.create_from_telegram_context(
        academy_id=academy_id,
        context_data=_make_student_context(
            student_name='Castiel',
            modality_id=modality_id,
            address_reference_student_id=first_student.id,
        ),
    )

    first_student_result = await db_session.execute(
        select(Student).where(Student.id == first_student.id)
    )
    second_student_result = await db_session.execute(
        select(Student).where(Student.id == second_student.id)
    )

    first_student_model = first_student_result.scalar_one()
    second_student_model = second_student_result.scalar_one()

    address_count_result = await db_session.execute(
        select(func.count(Address.id))
    )

    assert first_student_model.address_id is not None
    assert second_student_model.address_id == first_student_model.address_id
    assert address_count_result.scalar_one() == 1


@pytest.mark.asyncio
async def test_create_student_cannot_reuse_address_from_another_academy(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    first_academy_id, first_modality_id = await _setup_academy_with_modality(
        client=client,
        db_session=db_session,
        academy_name='Academia Luna',
        telegram_user_id=100000001,
    )
    second_academy_id, second_modality_id = await _setup_academy_with_modality(
        client=client,
        db_session=db_session,
        academy_name='Academia Castiel',
        telegram_user_id=100000002,
    )

    student_service = _make_student_service(db_session)

    first_student = await student_service.create_from_telegram_context(
        academy_id=first_academy_id,
        context_data=_make_student_context(
            student_name='Luna',
            modality_id=first_modality_id,
        ),
    )

    with pytest.raises(NotFoundError):
        await student_service.create_from_telegram_context(
            academy_id=second_academy_id,
            context_data=_make_student_context(
                student_name='Castiel',
                modality_id=second_modality_id,
                address_reference_student_id=first_student.id,
            ),
        )


@pytest.mark.asyncio
async def test_create_student_reusing_responsible_from_another_student(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    academy_id, modality_id = await _setup_academy_with_modality(
        client=client,
        db_session=db_session,
        academy_name='Academia Luna',
        telegram_user_id=100000001,
    )

    student_service = _make_student_service(db_session)

    first_student = await student_service.create_from_telegram_context(
        academy_id=academy_id,
        context_data=_make_student_context(
            student_name='Luna',
            modality_id=modality_id,
        ),
    )

    first_student_responsible_result = await db_session.execute(
        select(StudentResponsible).where(
            StudentResponsible.student_id == first_student.id
        )
    )
    first_student_responsible = first_student_responsible_result.scalar_one()

    second_student_context = _make_student_context(
        student_name='Castiel',
        modality_id=modality_id,
    )
    second_student_context['responsibles'] = []
    second_student_context['responsible_references'] = [
        {
            'responsible_id': first_student_responsible.responsible_id,
            'relationship': 'father',
        }
    ]

    second_student = await student_service.create_from_telegram_context(
        academy_id=academy_id,
        context_data=second_student_context,
    )

    second_student_responsible_result = await db_session.execute(
        select(StudentResponsible).where(
            StudentResponsible.student_id == second_student.id
        )
    )
    second_student_responsible = second_student_responsible_result.scalar_one()

    responsible_count_result = await db_session.execute(
        select(func.count(Responsible.id))
    )
    student_responsible_count_result = await db_session.execute(
        select(func.count(StudentResponsible.id))
    )

    assert (
        second_student_responsible.responsible_id
        == first_student_responsible.responsible_id
    )
    assert second_student_responsible.relationship == 'father'
    assert responsible_count_result.scalar_one() == 1
    assert (
        student_responsible_count_result.scalar_one()
        == EXPECTED_SHARED_RESPONSIBLE_LINKS_COUNT
    )


@pytest.mark.asyncio
async def test_create_student_cannot_reuse_responsible_from_another_academy(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    first_academy_id, first_modality_id = await _setup_academy_with_modality(
        client=client,
        db_session=db_session,
        academy_name='Academia Luna',
        telegram_user_id=100000001,
    )
    second_academy_id, second_modality_id = await _setup_academy_with_modality(
        client=client,
        db_session=db_session,
        academy_name='Academia Castiel',
        telegram_user_id=100000002,
    )

    student_service = _make_student_service(db_session)

    first_student = await student_service.create_from_telegram_context(
        academy_id=first_academy_id,
        context_data=_make_student_context(
            student_name='Luna',
            modality_id=first_modality_id,
        ),
    )

    first_student_responsible_result = await db_session.execute(
        select(StudentResponsible).where(
            StudentResponsible.student_id == first_student.id
        )
    )
    first_student_responsible = first_student_responsible_result.scalar_one()

    second_student_context = _make_student_context(
        student_name='Castiel',
        modality_id=second_modality_id,
    )
    second_student_context['responsibles'] = []
    second_student_context['responsible_references'] = [
        {
            'responsible_id': first_student_responsible.responsible_id,
            'relationship': 'father',
        }
    ]

    with pytest.raises(NotFoundError):
        await student_service.create_from_telegram_context(
            academy_id=second_academy_id,
            context_data=second_student_context,
        )
