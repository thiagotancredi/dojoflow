from typing import Annotated

from fastapi import Depends

from dojoflow.integrations.cep.client import CepClient
from dojoflow.services.cep import CepService


def get_cep_service() -> CepService:
    return CepService(cep_client=CepClient())


CepServiceDep = Annotated[
    CepService,
    Depends(get_cep_service),
]
