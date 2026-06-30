import re
from typing import Any

import httpx

from dojoflow.integrations.cep.schemas import CepAddress

ZIP_CODE_LENGTH = 8


class CepClient:
    async def search(
        self,
        zip_code: str,
    ) -> CepAddress | None:
        normalized_zip_code = self._normalize_zip_code(zip_code)

        if normalized_zip_code is None:
            return None

        providers = (
            self._search_brasil_api,
            self._search_via_cep,
            self._search_open_cep,
        )

        for provider in providers:
            cep_address = await provider(normalized_zip_code)

            if cep_address is not None:
                return cep_address

        return None

    @staticmethod
    def _normalize_zip_code(
        zip_code: str,
    ) -> str | None:
        digits = re.sub(r'\D', '', zip_code)

        if len(digits) != ZIP_CODE_LENGTH:
            return None

        return digits

    async def _search_brasil_api(
        self,
        zip_code: str,
    ) -> CepAddress | None:
        url = f'https://brasilapi.com.br/api/cep/v2/{zip_code}'

        data = await self._get_json(url)

        if data is None:
            return None

        city = data.get('city')
        state = data.get('state')

        if not city or not state:
            return None

        return CepAddress(
            zip_code=zip_code,
            street=data.get('street'),
            neighborhood=data.get('neighborhood'),
            city=city,
            state=state,
            provider='brasil_api',
        )

    async def _search_via_cep(
        self,
        zip_code: str,
    ) -> CepAddress | None:
        url = f'https://viacep.com.br/ws/{zip_code}/json/'

        data = await self._get_json(url)

        if data is None or data.get('erro') is True:
            return None

        city = data.get('localidade')
        state = data.get('uf')

        if not city or not state:
            return None

        return CepAddress(
            zip_code=zip_code,
            street=data.get('logradouro'),
            neighborhood=data.get('bairro'),
            city=city,
            state=state,
            provider='via_cep',
        )

    async def _search_open_cep(
        self,
        zip_code: str,
    ) -> CepAddress | None:
        url = f'https://opencep.com/v1/{zip_code}.json'

        data = await self._get_json(url)

        if data is None:
            return None

        city = data.get('localidade')
        state = data.get('uf')

        if not city or not state:
            return None

        return CepAddress(
            zip_code=zip_code,
            street=data.get('logradouro'),
            neighborhood=data.get('bairro'),
            city=city,
            state=state,
            provider='open_cep',
        )

    @staticmethod
    async def _get_json(
        url: str,
    ) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                return response.json()
        except (httpx.HTTPError, ValueError):
            return None
