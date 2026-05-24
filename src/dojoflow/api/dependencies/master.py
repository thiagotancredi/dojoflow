from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.repositories.master import MasterRepository
from dojoflow.services.master import MasterService


def _get_master_repository(
    db_session_dep: DbSessionDep,
) -> MasterRepository:
    return MasterRepository(db_session=db_session_dep)


MasterRepositoryDep = Annotated[
    MasterRepository,
    Depends(_get_master_repository),
]


def _get_master_service(
    master_repository_dep: MasterRepositoryDep,
    db_session_dep: DbSessionDep,
) -> MasterService:
    return MasterService(
        master_repository=master_repository_dep,
        db_session=db_session_dep,
    )


MasterServiceDep = Annotated[
    MasterService,
    Depends(_get_master_service),
]
