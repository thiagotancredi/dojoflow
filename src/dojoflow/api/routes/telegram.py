from typing import Any

from fastapi import APIRouter, status

from dojoflow.api.dependencies.telegram import (
    TelegramServiceDep,
    TelegramWebhookServiceDep,
)
from dojoflow.integrations.telegram.schemas import TelegramUpdate

router = APIRouter(prefix='/telegram', tags=['Telegram'])


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
) -> dict[str, str]:
    return await telegram_webhook_service_dep.process_update(payload)
