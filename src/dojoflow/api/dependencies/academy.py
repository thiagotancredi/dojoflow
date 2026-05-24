from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.repositories.academy import AcademyRepository
from dojoflow.services.academy import AcademyService


def _get_academy_repository(
    db_session_dep: DbSessionDep,
) -> AcademyRepository:
    return AcademyRepository(db_session=db_session_dep)


AcademyRepositoryDep = Annotated[
    AcademyRepository,
    Depends(_get_academy_repository),
]


def _get_academy_service(
    academy_repository_dep: AcademyRepositoryDep,
    db_session_dep: DbSessionDep,
) -> AcademyService:
    return AcademyService(
        academy_repository=academy_repository_dep,
        db_session=db_session_dep,
    )


AcademyServiceDep = Annotated[
    AcademyService,
    Depends(_get_academy_service),
]
