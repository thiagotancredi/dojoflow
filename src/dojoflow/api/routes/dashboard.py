from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.dashboard import DashboardServiceDep
from dojoflow.schemas.dashboard import DashboardSummaryRead

router = APIRouter(prefix='/dashboard', tags=['Dashboard'])


@router.get(
    path='/summary',
    status_code=status.HTTP_200_OK,
)
async def get_dashboard_summary(
    current_master: CurrentMasterDep,
    dashboard_service_dep: DashboardServiceDep,
) -> DashboardSummaryRead:
    return await dashboard_service_dep.summary(current_master.academy_id)
