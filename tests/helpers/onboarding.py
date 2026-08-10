from typing import Any

from httpx import AsyncClient, Response

from devtools.factories.onboarding import OnboardingPayloadFactory
from dojoflow.core.settings import settings


async def register_onboarding(
    client: AsyncClient,
    **overrides: Any,
) -> tuple[Response, dict[str, Any]]:
    payload = OnboardingPayloadFactory(**overrides)

    headers: dict[str, str] = {}

    if settings.INTERNAL_API_KEY:
        headers['X-Internal-Api-Key'] = settings.INTERNAL_API_KEY

    response = await client.post(
        '/api/v1/onboarding',
        json=payload,
        headers=headers,
    )

    return response, payload


async def register_web(
    client: AsyncClient,
    **overrides: Any,
) -> tuple[Response, dict[str, Any]]:
    payload = {
        'academy_name': overrides.pop(
            'academy_name',
            'Academia Web Teste',
        ),
        'master_name': overrides.pop('master_name', 'Mestre Web'),
        'email': overrides.pop('email', 'mestre@dojoflow.test'),
        'password': overrides.pop('password', 'senha-segura'),
        'phone': overrides.pop('phone', '62999990000'),
    }
    payload.update(overrides)

    response = await client.post('/api/v1/auth/register', json=payload)

    return response, payload
