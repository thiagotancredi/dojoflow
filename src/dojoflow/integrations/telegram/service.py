from typing import Any

import httpx

from dojoflow.core.settings import settings


class TelegramService:
    def __init__(self) -> None:
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f'https://api.telegram.org/bot{self.bot_token}'

    async def get_me(self) -> dict[str, Any]:
        if not self.bot_token:
            raise ValueError('TELEGRAM_BOT_TOKEN is not configured.')

        url = f'{self.base_url}/getMe'

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            return response.json()

    async def send_message(
        self,
        chat_id: int,
        text: str,
    ) -> None:
        if not self.bot_token:
            raise ValueError('TELEGRAM_BOT_TOKEN is not configured.')

        url = f'{self.base_url}/sendMessage'

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    'chat_id': chat_id,
                    'text': text,
                },
            )

            response.raise_for_status()
