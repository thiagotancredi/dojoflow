from http import HTTPStatus

import pytest
from httpx import AsyncClient

from dojoflow.shared.exceptions import NotFoundError


def test_custom_code_overrides_default() -> None:
    error = NotFoundError('missing', code='STUDENT_NOT_FOUND')

    assert error.code == 'STUDENT_NOT_FOUND'
    assert str(error) == 'missing'


def test_default_code_per_class() -> None:
    assert NotFoundError('x').code == 'NOT_FOUND'


@pytest.mark.asyncio
async def test_unauthorized_response_has_code(client: AsyncClient) -> None:
    response = await client.get('/api/v1/auth/me')

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {
        'detail': 'Authentication required.',
        'code': 'UNAUTHORIZED',
    }
