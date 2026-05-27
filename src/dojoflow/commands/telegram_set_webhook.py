import asyncio
import json

from dojoflow.integrations.telegram.service import TelegramService


async def main() -> None:
    telegram_service = TelegramService()

    response = await telegram_service.set_webhook()

    print(json.dumps(response, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
