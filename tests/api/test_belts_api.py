from http import HTTPStatus

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.auth import (
    auth_headers,
    create_modality,
    other_academy_headers,
)
from tests.helpers.graduation import (
    create_belt,
    enable_modality,
    toggle_modality,
)

TAEKWONDO_BELT_COUNT = 19
KICKBOXING_BELT_COUNT = 15


def _belts_url(modality_id: str) -> str:
    return f'/api/v1/academy/modalities/{modality_id}/belts'


async def _list(
    client: AsyncClient, headers: dict[str, str], modality_id: str
) -> list[dict]:
    response = await client.get(_belts_url(modality_id), headers=headers)
    assert response.status_code == HTTPStatus.OK, response.text

    return response.json()


@pytest.mark.asyncio
async def test_create_and_list_belts_in_order(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')

    await create_belt(
        client,
        headers,
        taekwondo,
        'Branca',
        primary_color='#F8FAFC',
        min_time_amount=3,
        min_time_unit='months',
    )
    await create_belt(
        client, headers, taekwondo, 'Amarela', primary_color='#facc15'
    )

    belts = await _list(client, headers, taekwondo)

    assert [belt['name'] for belt in belts] == ['Branca', 'Amarela']
    assert [belt['position'] for belt in belts] == [1, 2]
    assert belts[0]['primary_color'] == '#f8fafc'
    assert belts[0]['marks'] == 0
    assert belts[0]['marks_color'] == '#d4a017'
    assert belts[0]['stripe_color'] is None
    assert belts[0]['tip_color'] is None
    assert belts[0]['min_time_amount'] == 3  # noqa: PLR2004
    assert belts[0]['min_time_unit'] == 'months'
    assert belts[1]['min_time_amount'] is None


@pytest.mark.asyncio
async def test_belt_name_unique_within_modality(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    jiu_jitsu = await enable_modality(client, db_session, headers, 'Jiu-jitsu')
    await create_belt(client, headers, taekwondo, 'Branca')

    duplicated = await client.post(
        _belts_url(taekwondo),
        headers=headers,
        json={'name': ' branca ', 'primary_color': '#f8fafc'},
    )

    assert duplicated.status_code == HTTPStatus.CONFLICT
    assert duplicated.json()['code'] == 'BELT_NAME_TAKEN'

    await create_belt(client, headers, jiu_jitsu, 'Branca')


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'bad',
    [
        {'min_time_amount': 3},
        {'min_time_unit': 'months'},
        {'min_time_amount': 0, 'min_time_unit': 'months'},
        {'marks': 11},
        {'min_time_amount': 1201, 'min_time_unit': 'days'},
        {'primary_color': 'red'},
        {'name': '   '},
    ],
)
async def test_invalid_belt_payload_is_422(
    client: AsyncClient,
    db_session: AsyncSession,
    bad: dict,
) -> None:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')

    response = await client.post(
        _belts_url(taekwondo),
        headers=headers,
        json={'name': 'Branca', 'primary_color': '#f8fafc', **bad},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_update_belt_replaces_fields(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    await create_belt(client, headers, taekwondo, 'Branca')
    belt = await create_belt(
        client, headers, taekwondo, 'Verde e azul', stripe_color='#1d4ed8'
    )

    response = await client.put(
        f'/api/v1/academy/belts/{belt["id"]}',
        headers=headers,
        json={
            'name': 'Verde',
            'primary_color': '#16a34a',
            'stripe_color': None,
        },
    )

    assert response.status_code == HTTPStatus.OK, response.text
    updated = response.json()
    assert updated['id'] == belt['id']
    assert updated['name'] == 'Verde'
    assert updated['stripe_color'] is None
    assert updated['position'] == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_reorder_belts(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    ids = [
        (await create_belt(client, headers, taekwondo, name))['id']
        for name in ('A', 'B', 'C')
    ]

    reordered = await client.put(
        f'{_belts_url(taekwondo)}/order',
        headers=headers,
        json={'belt_ids': list(reversed(ids))},
    )

    assert reordered.status_code == HTTPStatus.NO_CONTENT
    belts = await _list(client, headers, taekwondo)
    assert [belt['name'] for belt in belts] == ['C', 'B', 'A']
    assert [belt['position'] for belt in belts] == [1, 2, 3]

    for wrong in (ids[:2], [*ids, ids[0]]):
        mismatch = await client.put(
            f'{_belts_url(taekwondo)}/order',
            headers=headers,
            json={'belt_ids': wrong},
        )
        assert mismatch.status_code == HTTPStatus.CONFLICT
        assert mismatch.json()['code'] == 'BELT_ORDER_MISMATCH'


@pytest.mark.asyncio
async def test_delete_unused_belt_renumbers(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    await create_belt(client, headers, taekwondo, 'A')
    middle = await create_belt(client, headers, taekwondo, 'B')
    await create_belt(client, headers, taekwondo, 'C')

    response = await client.delete(
        f'/api/v1/academy/belts/{middle["id"]}', headers=headers
    )

    assert response.status_code == HTTPStatus.NO_CONTENT
    belts = await _list(client, headers, taekwondo)
    assert [(belt['name'], belt['position']) for belt in belts] == [
        ('A', 1),
        ('C', 2),
    ]


@pytest.mark.asyncio
async def test_taekwondo_preset(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    judo = await enable_modality(client, db_session, headers, 'Judô')
    preset_url = f'{_belts_url(taekwondo)}/preset'

    response = await client.post(preset_url, headers=headers)

    assert response.status_code == HTTPStatus.CREATED, response.text
    belts = response.json()
    assert len(belts) == TAEKWONDO_BELT_COUNT
    assert belts[0]['name'] == 'Branca'
    assert belts[5]['name'] == 'Verde e azul'
    assert belts[5]['stripe_color'] == '#1d4ed8'
    assert [belt['min_time_amount'] for belt in belts[:9]] == [
        3,
        2,
        4,
        4,
        4,
        5,
        8,
        6,
        8,
    ]
    assert {belt['min_time_unit'] for belt in belts[:9]} == {'months'}
    assert belts[9]['name'] == 'Vermelha e preta'
    assert (belts[9]['min_time_amount'], belts[9]['min_time_unit']) == (
        1,
        'years',
    )
    assert belts[10]['name'] == 'Preta 1º Dan'
    assert belts[10]['marks'] == 1
    assert (belts[10]['min_time_amount'], belts[10]['min_time_unit']) == (
        1,
        'years',
    )
    assert belts[16]['name'] == 'Preta 7º Dan'
    assert belts[16]['min_time_amount'] == 8  # noqa: PLR2004
    assert belts[18]['name'] == 'Preta 9º Dan'
    assert belts[18]['marks'] == 9  # noqa: PLR2004
    assert belts[18]['min_time_amount'] is None
    assert [belt['position'] for belt in belts] == list(range(1, 20))
    assert await _list(client, headers, taekwondo) == belts

    again = await client.post(preset_url, headers=headers)
    assert again.status_code == HTTPStatus.CONFLICT
    assert again.json()['code'] == 'BELTS_ALREADY_EXIST'

    other = await client.post(f'{_belts_url(judo)}/preset', headers=headers)
    assert other.status_code == HTTPStatus.CONFLICT
    assert other.json()['code'] == 'PRESET_NOT_AVAILABLE'


@pytest.mark.asyncio
async def test_kickboxing_preset(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    kickboxing = await enable_modality(
        client, db_session, headers, 'Kickboxing'
    )

    response = await client.post(
        f'{_belts_url(kickboxing)}/preset', headers=headers
    )

    assert response.status_code == HTTPStatus.CREATED, response.text
    belts = response.json()
    assert len(belts) == KICKBOXING_BELT_COUNT
    assert [
        (belt['name'], belt['min_time_amount'], belt['min_time_unit'])
        for belt in belts[:6]
    ] == [
        ('Branca', 4, 'months'),
        ('Amarela', 6, 'months'),
        ('Laranja', 6, 'months'),
        ('Verde', 8, 'months'),
        ('Azul', 10, 'months'),
        ('Marrom', 1, 'years'),
    ]
    # Pretas iguais às do Taekwondo
    assert belts[6]['name'] == 'Preta 1º Dan'
    assert belts[14]['name'] == 'Preta 9º Dan'
    assert belts[14]['min_time_amount'] is None


@pytest.mark.asyncio
async def test_belts_require_enabled_modality(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    modality = await create_modality(db_session, 'Taekwondo')

    response = await client.get(
        _belts_url(str(modality.public_id)), headers=headers
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['code'] == 'MODALITY_NOT_ENABLED'


@pytest.mark.asyncio
async def test_belts_survive_modality_toggle(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    await create_belt(client, headers, taekwondo, 'Branca')

    await toggle_modality(client, headers, taekwondo)
    await toggle_modality(client, headers, taekwondo)

    belts = await _list(client, headers, taekwondo)
    assert [belt['name'] for belt in belts] == ['Branca']


@pytest.mark.asyncio
async def test_other_academy_cannot_touch_belt(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    belt = await create_belt(client, headers, taekwondo, 'Branca')
    other = await other_academy_headers(db_session)

    update = await client.put(
        f'/api/v1/academy/belts/{belt["id"]}',
        headers=other,
        json={'name': 'Roubada', 'primary_color': '#111827'},
    )
    delete = await client.delete(
        f'/api/v1/academy/belts/{belt["id"]}', headers=other
    )

    assert update.status_code == HTTPStatus.NOT_FOUND
    assert update.json()['code'] == 'BELT_NOT_FOUND'
    assert delete.status_code == HTTPStatus.NOT_FOUND
    assert delete.json()['code'] == 'BELT_NOT_FOUND'


@pytest.mark.asyncio
async def test_modality_options_report_has_belts(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await auth_headers(client)
    taekwondo = await enable_modality(client, db_session, headers, 'Taekwondo')
    await enable_modality(client, db_session, headers, 'Boxe')
    await create_belt(client, headers, taekwondo, 'Branca')

    response = await client.get('/api/v1/academy/modalities', headers=headers)

    has_belts = {item['name']: item['has_belts'] for item in response.json()}
    assert has_belts == {'Taekwondo': True, 'Boxe': False}
