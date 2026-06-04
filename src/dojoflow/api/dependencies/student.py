from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.repositories.academy_modality import AcademyModalityRepository
from dojoflow.repositories.enrollment import EnrollmentRepository
from dojoflow.repositories.student import StudentRepository
from dojoflow.repositories.student_responsible import (
    StudentResponsibleRepository,
)
from dojoflow.services.student import StudentService


def _get_student_repository(
    db_session_dep: DbSessionDep,
) -> StudentRepository:
    return StudentRepository(db_session=db_session_dep)


StudentRepositoryDep = Annotated[
    StudentRepository,
    Depends(_get_student_repository),
]


def _get_enrollment_repository(
    db_session_dep: DbSessionDep,
) -> EnrollmentRepository:
    return EnrollmentRepository(db_session=db_session_dep)


EnrollmentRepositoryDep = Annotated[
    EnrollmentRepository,
    Depends(_get_enrollment_repository),
]


def _get_student_responsible_repository(
    db_session_dep: DbSessionDep,
) -> StudentResponsibleRepository:
    return StudentResponsibleRepository(db_session=db_session_dep)


StudentResponsibleRepositoryDep = Annotated[
    StudentResponsibleRepository,
    Depends(_get_student_responsible_repository),
]


def _get_academy_modality_repository(
    db_session_dep: DbSessionDep,
) -> AcademyModalityRepository:
    return AcademyModalityRepository(db_session=db_session_dep)


AcademyModalityRepositoryDep = Annotated[
    AcademyModalityRepository,
    Depends(_get_academy_modality_repository),
]


def _get_student_service(
    student_repository_dep: StudentRepositoryDep,
    enrollment_repository_dep: EnrollmentRepositoryDep,
    student_responsible_repository_dep: StudentResponsibleRepositoryDep,
    academy_modality_repository_dep: AcademyModalityRepositoryDep,
    db_session_dep: DbSessionDep,
) -> StudentService:
    return StudentService(
        student_repository=student_repository_dep,
        enrollment_repository=enrollment_repository_dep,
        student_responsible_repository=student_responsible_repository_dep,
        academy_modality_repository=academy_modality_repository_dep,
        db_session=db_session_dep,
    )


StudentServiceDep = Annotated[
    StudentService,
    Depends(_get_student_service),
]
