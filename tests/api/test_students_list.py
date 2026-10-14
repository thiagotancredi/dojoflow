import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import auth_headers, create_modality

URL = '/api/v1/students'
TWO_STUDENTS = 2
DEFAULT_PAGE_SIZE = 20


async def _setup(
    client: AsyncClient,
    db_session: AsyncSession,
) -> tuple[dict[str, str], str, str]:
    headers = await auth_headers(client)
    ids = []

    for name in ('Jiu', 'Judô'):
        modality = await create_modality(db_session, name)
        ids.append(str(modality.public_id))
        await client.put(
            f'/api/v1/academy/modalities/{ids[-1]}/toggle',
            headers=headers,
        )

    return headers, ids[0], ids[1]


async def _student(
    client: AsyncClient,
    headers: dict[str, str],
    name: str,
    modality_id: str,
    status: str = 'active',
) -> str:
    response = await client.post(
        URL,
        headers=headers,
        json={
            'name': name,
            'enrollment': {'modality_id': modality_id, 'status': status},
        },
    )

    return response.json()['id']


@pytest.mark.asyncio
async def test_page_shape_order_and_modalities(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, jiu, _ = await _setup(client, db_session)
    await _student(client, headers, 'Bruno', jiu)
    await _student(client, headers, 'Ana', jiu)

    response = await client.get(URL, headers=headers)

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body['total'] == TWO_STUDENTS
    assert body['page'] == 1
    assert body['page_size'] == DEFAULT_PAGE_SIZE
    assert [item['name'] for item in body['items']] == ['Ana', 'Bruno']
    assert body['items'][0]['modalities'] == ['Jiu']


@pytest.mark.asyncio
async def test_status_and_modality_filters(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, jiu, judo = await _setup(client, db_session)
    await _student(client, headers, 'Ativo Jiu', jiu)
    await _student(client, headers, 'Inativo Judo', judo, status='inactive')

    active = await client.get(
        URL, headers=headers, params={'status': 'active'}
    )
    inactive = await client.get(
        URL, headers=headers, params={'status': 'inactive'}
    )
    by_judo = await client.get(
        URL, headers=headers, params={'modality_id': judo}
    )

    assert [i['name'] for i in active.json()['items']] == ['Ativo Jiu']
    assert [i['name'] for i in inactive.json()['items']] == ['Inativo Judo']
    assert [i['name'] for i in by_judo.json()['items']] == ['Inativo Judo']


@pytest.mark.asyncio
async def test_search_treats_wildcards_literally(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, jiu, _ = await _setup(client, db_session)
    await _student(client, headers, 'Ana Lima', jiu)
    await _student(client, headers, 'Carla 100%', jiu)

    percent = await client.get(URL, headers=headers, params={'search': '%'})
    partial = await client.get(URL, headers=headers, params={'search': 'lim'})

    assert [i['name'] for i in percent.json()['items']] == ['Carla 100%']
    assert [i['name'] for i in partial.json()['items']] == ['Ana Lima']


@pytest.mark.asyncio
async def test_whitespace_only_search_is_no_search(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, jiu, _ = await _setup(client, db_session)
    await _student(client, headers, 'Ana Lima', jiu)
    await _student(client, headers, 'Bia Souza', jiu)

    response = await client.get(URL, headers=headers, params={'search': '   '})

    assert response.json()['total'] == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_page_beyond_end_and_unknown_modality_are_empty(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, jiu, _ = await _setup(client, db_session)
    await _student(client, headers, 'Ana', jiu)

    beyond = await client.get(
        URL, headers=headers, params={'page': 5, 'page_size': 10}
    )
    unknown = await client.get(
        URL, headers=headers, params={'modality_id': str(uuid.uuid4())}
    )

    assert beyond.status_code == HTTPStatus.OK
    assert beyond.json()['items'] == []
    assert beyond.json()['total'] == 1
    assert unknown.status_code == HTTPStatus.OK
    assert unknown.json() == {
        'items': [],
        'total': 0,
        'page': 1,
        'page_size': 20,
    }
