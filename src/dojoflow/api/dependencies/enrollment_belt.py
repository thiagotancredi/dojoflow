from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.belt import BeltServiceDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.repositories.enrollment_belt import EnrollmentBeltRepository
from dojoflow.services.enrollment_belt import EnrollmentBeltService


def _get_enrollment_belt_service(
    belt_service_dep: BeltServiceDep,
    db_session_dep: DbSessionDep,
) -> EnrollmentBeltService:
    return EnrollmentBeltService(
        enrollment_belt_repository=EnrollmentBeltRepository(
            db_session=db_session_dep
        ),
        belt_service=belt_service_dep,
        db_session=db_session_dep,
    )


EnrollmentBeltServiceDep = Annotated[
    EnrollmentBeltService,
    Depends(_get_enrollment_belt_service),
]
