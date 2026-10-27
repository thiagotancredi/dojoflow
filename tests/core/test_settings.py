import pytest
from pydantic import ValidationError

from dojoflow.core.settings import DEFAULT_JWT_SECRET, Settings


def test_prod_refuses_default_jwt_secret() -> None:
    with pytest.raises(ValidationError, match='JWT_SECRET'):
        Settings(
            _env_file=None,
            ENVIRONMENT='prod',
            JWT_SECRET=DEFAULT_JWT_SECRET,
        )


def test_prod_accepts_custom_jwt_secret() -> None:
    settings = Settings(
        _env_file=None,
        ENVIRONMENT='prod',
        JWT_SECRET='a-real-secret-with-enough-length-32',
        INFINITEPAY_SECRET_KEY='x' * 43 + '=',
    )

    assert settings.cookie_secure is True


def test_dev_allows_default_secret_and_insecure_cookie() -> None:
    settings = Settings(
        _env_file=None,
        ENVIRONMENT='dev',
        JWT_SECRET=DEFAULT_JWT_SECRET,
    )

    assert settings.cookie_secure is False
