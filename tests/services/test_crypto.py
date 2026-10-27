import pytest
from pydantic import ValidationError

from dojoflow.core.crypto import decrypt_secret, encrypt_secret
from dojoflow.core.settings import (
    DEFAULT_INFINITEPAY_SECRET_KEY,
    Settings,
)

PROD_JWT = 'a-real-secret-with-enough-length-32'


def test_encrypt_roundtrip() -> None:
    plain = 'inchk_live_abc123SECRET'

    token = encrypt_secret(plain)

    assert plain not in token
    assert 'SECRET' not in token
    assert decrypt_secret(token) == plain


def test_encrypt_is_not_deterministic() -> None:
    # Mesma chave cifrada duas vezes dá textos diferentes (Fernet usa IV)
    assert encrypt_secret('abc') != encrypt_secret('abc')


def test_settings_refuse_default_infinitepay_secret_outside_dev() -> None:
    with pytest.raises(ValidationError, match='INFINITEPAY_SECRET_KEY'):
        Settings(
            _env_file=None,
            ENVIRONMENT='prod',
            JWT_SECRET=PROD_JWT,
            INFINITEPAY_SECRET_KEY=DEFAULT_INFINITEPAY_SECRET_KEY,
        )


def test_settings_accept_custom_infinitepay_secret_in_prod() -> None:
    settings = Settings(
        _env_file=None,
        ENVIRONMENT='prod',
        JWT_SECRET=PROD_JWT,
        INFINITEPAY_SECRET_KEY='x' * 43 + '=',
        EMAIL_BACKEND='ses',
    )

    assert settings.INFINITEPAY_SECRET_KEY == 'x' * 43 + '='
