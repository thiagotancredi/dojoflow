from typing import Any

from httpx import AsyncClient, Response

from devtools.factories.onboarding import OnboardingPayloadFactory


async def register_onboarding(
    client: AsyncClient,
    **overrides: Any,
) -> tuple[Response, dict[str, Any]]:
    payload = OnboardingPayloadFactory(**overrides)

    response = await client.post(
        '/api/v1/onboarding',
        json=payload,
    )

    return response, payload
