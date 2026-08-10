from fastapi import APIRouter, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.modality import ModalityServiceDep
from dojoflow.schemas.modality import ModalityOptionRead, ModalityRead

router = APIRouter(tags=['Modalities'])


@router.get(
    path='/modalities/catalog',
    status_code=status.HTTP_200_OK,
)
async def list_modality_catalog(
    current_master: CurrentMasterDep,
    modality_service_dep: ModalityServiceDep,
) -> list[ModalityRead]:
    return await modality_service_dep.list_catalog()


@router.get(
    path='/academy/modalities',
    status_code=status.HTTP_200_OK,
)
async def list_academy_modalities(
    current_master: CurrentMasterDep,
    modality_service_dep: ModalityServiceDep,
) -> list[ModalityOptionRead]:
    return await modality_service_dep.list_academy_options(
        current_master.academy_id
    )


@router.put(
    path='/academy/modalities/{modality_id}/toggle',
    status_code=status.HTTP_200_OK,
)
async def toggle_academy_modality(
    modality_id: int,
    current_master: CurrentMasterDep,
    modality_service_dep: ModalityServiceDep,
) -> dict[str, bool]:
    is_selected = await modality_service_dep.toggle_academy_modality(
        academy_id=current_master.academy_id,
        modality_id=modality_id,
    )

    return {'is_selected': is_selected}
