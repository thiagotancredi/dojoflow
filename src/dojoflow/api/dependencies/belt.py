from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.repositories.belt import BeltRepository
from dojoflow.services.belt import BeltService


def _get_belt_repository(
    db_session_dep: DbSessionDep,
) -> BeltRepository:
    return BeltRepository(db_session=db_session_dep)


BeltRepositoryDep = Annotated[
    BeltRepository,
    Depends(_get_belt_repository),
]


def _get_belt_service(
    belt_repository_dep: BeltRepositoryDep,
    db_session_dep: DbSessionDep,
) -> BeltService:
    return BeltService(
        belt_repository=belt_repository_dep,
        db_session=db_session_dep,
    )


BeltServiceDep = Annotated[
    BeltService,
    Depends(_get_belt_service),
]
