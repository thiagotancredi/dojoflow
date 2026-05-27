from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status

from dojoflow.api.dependencies.telegram import (
    TelegramServiceDep,
    TelegramWebhookServiceDep,
)
from dojoflow.core.settings import settings
from dojoflow.integrations.telegram.schemas import TelegramUpdate

router = APIRouter(prefix='/telegram', tags=['Telegram'])

TELEGRAM_SECRET_HEADER = 'X-Telegram-Bot-Api-Secret-Token'


@router.get(
    path='/me',
    status_code=status.HTTP_200_OK,
)
async def get_telegram_bot_info(
    telegram_service_dep: TelegramServiceDep,
) -> dict[str, Any]:
    return await telegram_service_dep.get_me()


@router.post(
    path='/webhook',
    status_code=status.HTTP_200_OK,
)
async def receive_telegram_webhook(
    payload: TelegramUpdate,
    telegram_webhook_service_dep: TelegramWebhookServiceDep,
    telegram_secret_token: Annotated[
        str | None,
        Header(alias=TELEGRAM_SECRET_HEADER),
    ] = None,
) -> dict[str, str]:
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Telegram webhook secret is not configured.',
        )

    if telegram_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid Telegram webhook secret.',
        )

    return await telegram_webhook_service_dep.process_update(payload)
