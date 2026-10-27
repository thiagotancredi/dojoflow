import time
from collections import deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    """Limite simples de acessos por IP, na memória de cada processo.

    Basta para frear quem tenta adivinhar links públicos; não é
    compartilhado entre os workers do uvicorn.
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}

    async def __call__(self, request: Request) -> None:
        ip = request.client.host if request.client else 'unknown'
        now = time.monotonic()
        hits = self._hits.setdefault(ip, deque())
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Muitas tentativas. Tente de novo em instantes.',
            )
        hits.append(now)

    def reset(self) -> None:
        self._hits.clear()


public_pay_limiter = RateLimiter(limit=30, window_seconds=60)
# Avisos da InfinitePay chegam de poucos endereços, para todas as
# academias: limite mais folgado
webhook_limiter = RateLimiter(limit=300, window_seconds=60)
