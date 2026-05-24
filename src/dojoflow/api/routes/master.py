from fastapi import APIRouter, HTTPException, status

from dojoflow.api.dependencies.master import MasterServiceDep
from dojoflow.schemas.master_context import MasterContextRead

router = APIRouter(prefix='/masters', tags=['Masters'])


@router.get(
    path='/context/{telegram_user_id}',
    response_model=MasterContextRead,
    status_code=status.HTTP_200_OK,
)
async def get_master_context(
    telegram_user_id: int,
    master_service_dep: MasterServiceDep,
) -> MasterContextRead:
    context = await master_service_dep.get_context_by_telegram_user_id(
        telegram_user_id
    )

    if context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Master context not found.',
        )

    return context
