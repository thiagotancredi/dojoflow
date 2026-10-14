from typing import Annotated

from fastapi import APIRouter, Path, status

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.telegram import CepServiceDep
from dojoflow.integrations.cep.schemas import CepAddress
from dojoflow.shared.exceptions import NotFoundError

router = APIRouter(prefix='/cep', tags=['CEP'])


@router.get(
    path='/{zip_code}',
    status_code=status.HTTP_200_OK,
)
async def get_address_by_zip_code(
    zip_code: Annotated[str, Path(pattern=r'^\d{8}$')],
    current_master: CurrentMasterDep,
    cep_service_dep: CepServiceDep,
) -> CepAddress:
    address = await cep_service_dep.search(zip_code)

    if address is None:
        raise NotFoundError('Zip code not found.', code='CEP_NOT_FOUND')

    return address
