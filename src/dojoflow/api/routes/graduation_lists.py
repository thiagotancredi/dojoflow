from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.graduation_list import GraduationListServiceDep
from dojoflow.api.dependencies.public_ids import (
    GraduationListIdDep,
    resolve_modality_id,
)
from dojoflow.schemas.graduation_list import (
    GraduationListCreate,
    GraduationListUpdate,
)
from dojoflow.schemas.graduation_list_api import (
    GraduationListApiCreate,
    GraduationListDetailApiRead,
    GraduationListSummaryApiRead,
)

router = APIRouter(prefix='/graduation-lists', tags=['Graduation lists'])


@router.get(path='', status_code=status.HTTP_200_OK)
async def list_graduation_lists(
    current_master: CurrentMasterDep,
    graduation_list_service_dep: GraduationListServiceDep,
) -> list[GraduationListSummaryApiRead]:
    summaries = await graduation_list_service_dep.list_summaries(
        current_master.academy_id
    )

    return [GraduationListSummaryApiRead.from_internal(s) for s in summaries]


@router.post(path='', status_code=status.HTTP_201_CREATED)
async def create_graduation_list(
    data: GraduationListApiCreate,
    current_master: CurrentMasterDep,
    graduation_list_service_dep: GraduationListServiceDep,
    db_session_dep: DbSessionDep,
) -> GraduationListSummaryApiRead:
    modality_id = await resolve_modality_id(db_session_dep, data.modality_id)
    summary = await graduation_list_service_dep.create(
        current_master.academy_id,
        GraduationListCreate(
            name=data.name,
            modality_id=modality_id,
            exam_date=data.exam_date,
        ),
    )

    return GraduationListSummaryApiRead.from_internal(summary)


@router.get(path='/{list_id}', status_code=status.HTTP_200_OK)
async def get_graduation_list(
    list_id: GraduationListIdDep,
    current_master: CurrentMasterDep,
    graduation_list_service_dep: GraduationListServiceDep,
) -> GraduationListDetailApiRead:
    detail = await graduation_list_service_dep.get_detail(
        current_master.academy_id, list_id
    )

    return GraduationListDetailApiRead.from_internal(detail)


@router.patch(path='/{list_id}', status_code=status.HTTP_204_NO_CONTENT)
async def update_graduation_list(
    list_id: GraduationListIdDep,
    data: GraduationListUpdate,
    current_master: CurrentMasterDep,
    graduation_list_service_dep: GraduationListServiceDep,
) -> None:
    await graduation_list_service_dep.update(
        current_master.academy_id, list_id, data
    )


@router.delete(path='/{list_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_graduation_list(
    list_id: GraduationListIdDep,
    current_master: CurrentMasterDep,
    graduation_list_service_dep: GraduationListServiceDep,
) -> None:
    await graduation_list_service_dep.delete(
        current_master.academy_id, list_id
    )
