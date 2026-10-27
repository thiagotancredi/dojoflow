from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.infinitepay import InfinitePayServiceDep
from dojoflow.schemas.infinitepay_api import (
    InfinitePayConnectApi,
    InfinitePayStatusApi,
)

router = APIRouter(prefix='/academy/infinitepay', tags=['Billing'])


@router.get(path='', status_code=status.HTTP_200_OK)
async def read_infinitepay(
    current_master: CurrentMasterDep,
    infinitepay_service_dep: InfinitePayServiceDep,
) -> InfinitePayStatusApi:
    return await infinitepay_service_dep.status(current_master.academy_id)


@router.put(path='', status_code=status.HTTP_200_OK)
async def connect_infinitepay(
    data: InfinitePayConnectApi,
    current_master: CurrentMasterDep,
    infinitepay_service_dep: InfinitePayServiceDep,
) -> InfinitePayStatusApi:
    """Testar e ligar (também serve para trocar a chave)."""
    return await infinitepay_service_dep.connect(
        current_master.academy_id, data.handle, data.api_key
    )


@router.delete(path='', status_code=status.HTTP_200_OK)
async def disconnect_infinitepay(
    current_master: CurrentMasterDep,
    infinitepay_service_dep: InfinitePayServiceDep,
) -> InfinitePayStatusApi:
    return await infinitepay_service_dep.disconnect(current_master.academy_id)
