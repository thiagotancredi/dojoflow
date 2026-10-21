import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

from dojoflow.core.settings import settings
from dojoflow.shared.exceptions import UnauthorizedError

password_hash = PasswordHash.recommended()

TokenPurpose = Literal[
    'access',
    'telegram_link',
    'telegram_setup',
]

MASTER_ROLE = 'master'


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


def create_access_token(
    master_id: int,
    acting_academy_id: int | None = None,
) -> str:
    claims: dict[str, Any] = {'role': MASTER_ROLE}

    if acting_academy_id is not None:
        # Modo suporte: o administrador vê os dados desta academia
        claims['acting_academy_id'] = acting_academy_id

    token, _ = _create_token(
        subject=str(master_id),
        purpose='access',
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES),
        extra_claims=claims,
    )
    return token


# Sem 0/O, 1/l/I: a senha vai por WhatsApp e é digitada à mão
PASSWORD_ALPHABET = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789'
GENERATED_PASSWORD_LENGTH = 12


def generate_password() -> str:
    return ''.join(
        secrets.choice(PASSWORD_ALPHABET)
        for _ in range(GENERATED_PASSWORD_LENGTH)
    )


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode()).hexdigest()


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
    expected_role: str | None = None,
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

    if expected_role is not None and payload.get('role') != expected_role:
        raise UnauthorizedError('Invalid token role.')

    subject = payload.get('sub')

    if subject is None:
        raise UnauthorizedError('Invalid token subject.')

    return payload


def get_master_id_from_token(
    token: str,
    *,
    expected_purpose: TokenPurpose,
    expected_role: str | None = None,
) -> int:
    payload = decode_token(
        token,
        expected_purpose=expected_purpose,
        expected_role=expected_role,
    )

    try:
        return int(payload['sub'])
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError('Invalid token subject.') from exc
