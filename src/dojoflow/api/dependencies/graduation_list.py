from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.belt import BeltServiceDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.enrollment_belt import EnrollmentBeltServiceDep
from dojoflow.repositories.academy_modality import AcademyModalityRepository
from dojoflow.repositories.graduation_list import GraduationListRepository
from dojoflow.repositories.graduation_list_entry import (
    GraduationListEntryRepository,
)
from dojoflow.services.graduation_list import GraduationListService


def _get_graduation_list_service(
    belt_service_dep: BeltServiceDep,
    enrollment_belt_service_dep: EnrollmentBeltServiceDep,
    db_session_dep: DbSessionDep,
) -> GraduationListService:
    return GraduationListService(
        graduation_list_repository=GraduationListRepository(
            db_session=db_session_dep
        ),
        graduation_list_entry_repository=GraduationListEntryRepository(
            db_session=db_session_dep
        ),
        belt_service=belt_service_dep,
        enrollment_belt_service=enrollment_belt_service_dep,
        academy_modality_repository=AcademyModalityRepository(
            db_session=db_session_dep
        ),
        db_session=db_session_dep,
    )


GraduationListServiceDep = Annotated[
    GraduationListService,
    Depends(_get_graduation_list_service),
]
