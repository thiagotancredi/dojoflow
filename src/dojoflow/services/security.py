from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

from dojoflow.core.settings import settings
from dojoflow.shared.exceptions import UnauthorizedError

password_hash = PasswordHash.recommended()

TokenPurpose = Literal[
    'access',
    'refresh',
    'telegram_link',
    'telegram_setup',
]


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def _create_token(
    *,
    subject: str,
    purpose: TokenPurpose,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + expires_delta
    payload: dict[str, Any] = {
        'sub': subject,
        'purpose': purpose,
        'exp': expires_at,
        'iat': datetime.now(UTC),
    }

    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    return token, expires_at


def create_access_token(master_id: int) -> str:
    token, _ = _create_token(
        subject=str(master_id),
        purpose='access',
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES),
    )
    return token


def create_refresh_token(master_id: int) -> str:
    token, _ = _create_token(
        subject=str(master_id),
        purpose='refresh',
        expires_delta=timedelta(days=settings.JWT_REFRESH_TTL_DAYS),
    )
    return token


def create_telegram_link_token(master_id: int) -> tuple[str, datetime]:
    return _create_token(
        subject=str(master_id),
        purpose='telegram_link',
        expires_delta=timedelta(
            minutes=settings.JWT_TELEGRAM_LINK_TTL_MINUTES
        ),
    )


def create_telegram_setup_token(master_id: int) -> tuple[str, datetime]:
    return _create_token(
        subject=str(master_id),
        purpose='telegram_setup',
        expires_delta=timedelta(
            minutes=settings.JWT_TELEGRAM_SETUP_TTL_MINUTES
        ),
    )


def decode_token(
    token: str,
    *,
    expected_purpose: TokenPurpose,
) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError('Invalid or expired token.') from exc

    if payload.get('purpose') != expected_purpose:
        raise UnauthorizedError('Invalid token purpose.')

    subject = payload.get('sub')

    if subject is None:
        raise UnauthorizedError('Invalid token subject.')

    return payload


def get_master_id_from_token(
    token: str,
    *,
    expected_purpose: TokenPurpose,
) -> int:
    payload = decode_token(token, expected_purpose=expected_purpose)

    try:
        return int(payload['sub'])
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError('Invalid token subject.') from exc
