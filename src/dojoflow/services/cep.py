from dojoflow.integrations.cep.client import CepClient
from dojoflow.integrations.cep.schemas import CepAddress


class CepService:
    def __init__(
        self,
        cep_client: CepClient,
    ) -> None:
        self.cep_client = cep_client

    async def search(
        self,
        zip_code: str,
    ) -> CepAddress | None:
        return await self.cep_client.search(zip_code)
