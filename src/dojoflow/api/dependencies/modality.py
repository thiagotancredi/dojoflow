from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.repositories.academy_modality import AcademyModalityRepository
from dojoflow.repositories.modality import ModalityRepository
from dojoflow.services.modality import ModalityService


def _get_modality_repository(
    db_session_dep: DbSessionDep,
) -> ModalityRepository:
    return ModalityRepository(db_session=db_session_dep)


ModalityRepositoryDep = Annotated[
    ModalityRepository,
    Depends(_get_modality_repository),
]


def _get_academy_modality_repository(
    db_session_dep: DbSessionDep,
) -> AcademyModalityRepository:
    return AcademyModalityRepository(db_session=db_session_dep)


AcademyModalityRepositoryDep = Annotated[
    AcademyModalityRepository,
    Depends(_get_academy_modality_repository),
]


def _get_modality_service(
    modality_repository_dep: ModalityRepositoryDep,
    academy_modality_repository_dep: AcademyModalityRepositoryDep,
    db_session_dep: DbSessionDep,
) -> ModalityService:
    return ModalityService(
        modality_repository=modality_repository_dep,
        academy_modality_repository=academy_modality_repository_dep,
        db_session=db_session_dep,
    )


ModalityServiceDep = Annotated[
    ModalityService,
    Depends(_get_modality_service),
]
