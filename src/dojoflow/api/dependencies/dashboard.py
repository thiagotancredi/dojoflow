from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.services.dashboard import DashboardService


def _get_dashboard_service(db_session_dep: DbSessionDep) -> DashboardService:
    return DashboardService(db_session=db_session_dep)


DashboardServiceDep = Annotated[
    DashboardService,
    Depends(_get_dashboard_service),
]
