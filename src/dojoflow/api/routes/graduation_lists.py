from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.graduation_list import GraduationListServiceDep
from dojoflow.api.dependencies.public_ids import (
    GraduationEntryIdDep,
    GraduationListIdDep,
    resolve_academy_enrollment_id,
    resolve_belt_id,
    resolve_modality_id,
)
from dojoflow.schemas.graduation_list import (
    GraduationListCreate,
    GraduationListUpdate,
)
from dojoflow.schemas.graduation_list_api import (
    GraduationEntryApiCreate,
    GraduationEntryApiUpdate,
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


@router.post(
    path='/{list_id}/entries',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_graduation_entry(
    list_id: GraduationListIdDep,
    data: GraduationEntryApiCreate,
    current_master: CurrentMasterDep,
    graduation_list_service_dep: GraduationListServiceDep,
    db_session_dep: DbSessionDep,
) -> None:
    academy_id = current_master.academy_id
    enrollment_id = await resolve_academy_enrollment_id(
        db_session_dep, data.enrollment_id, academy_id
    )
    target_belt_id = (
        await resolve_belt_id(db_session_dep, data.target_belt_id, academy_id)
        if data.target_belt_id
        else None
    )

    await graduation_list_service_dep.add_entry(
        academy_id, list_id, enrollment_id, target_belt_id
    )


@router.patch(
    path='/{list_id}/entries/{entry_id}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_graduation_entry(  # noqa: PLR0913, PLR0917
    list_id: GraduationListIdDep,
    entry_id: GraduationEntryIdDep,
    data: GraduationEntryApiUpdate,
    current_master: CurrentMasterDep,
    graduation_list_service_dep: GraduationListServiceDep,
    db_session_dep: DbSessionDep,
) -> None:
    target_belt_id = await resolve_belt_id(
        db_session_dep, data.target_belt_id, current_master.academy_id
    )

    await graduation_list_service_dep.update_entry(
        current_master.academy_id, list_id, entry_id, target_belt_id
    )


@router.delete(
    path='/{list_id}/entries/{entry_id}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_graduation_entry(
    list_id: GraduationListIdDep,
    entry_id: GraduationEntryIdDep,
    current_master: CurrentMasterDep,
    graduation_list_service_dep: GraduationListServiceDep,
) -> None:
    await graduation_list_service_dep.remove_entry(
        current_master.academy_id, list_id, entry_id
    )
