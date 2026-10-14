from uuid import UUID

from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.modality import ModalityServiceDep
from dojoflow.api.dependencies.public_ids import resolve_modality_id
from dojoflow.schemas.modality_api import (
    ModalityApiRead,
    ModalityOptionApiRead,
    ModalityToggleRead,
)

router = APIRouter(tags=['Modalities'])


@router.get(
    path='/modalities/catalog',
    status_code=status.HTTP_200_OK,
)
async def list_modality_catalog(
    current_master: CurrentMasterDep,
    modality_service_dep: ModalityServiceDep,
) -> list[ModalityApiRead]:
    modalities = await modality_service_dep.list_catalog()

    return [ModalityApiRead.from_internal(item) for item in modalities]


@router.get(
    path='/academy/modalities',
    status_code=status.HTTP_200_OK,
)
async def list_academy_modalities(
    current_master: CurrentMasterDep,
    modality_service_dep: ModalityServiceDep,
) -> list[ModalityOptionApiRead]:
    options = await modality_service_dep.list_academy_options(
        current_master.academy_id
    )

    return [ModalityOptionApiRead.from_internal(item) for item in options]


@router.put(
    path='/academy/modalities/{modality_id}/toggle',
    status_code=status.HTTP_200_OK,
)
async def toggle_academy_modality(
    modality_id: UUID,
    current_master: CurrentMasterDep,
    modality_service_dep: ModalityServiceDep,
    db_session_dep: DbSessionDep,
) -> ModalityToggleRead:
    internal_id = await resolve_modality_id(db_session_dep, modality_id)
    is_selected = await modality_service_dep.toggle_academy_modality(
        academy_id=current_master.academy_id,
        modality_id=internal_id,
    )

    return ModalityToggleRead(is_selected=is_selected)
