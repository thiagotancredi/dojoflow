from datetime import UTC, datetime, timedelta

import jwt
import pytest

from dojoflow.core.settings import settings
from dojoflow.services.security import (
    MASTER_ROLE,
    create_access_token,
    get_master_id_from_token,
)
from dojoflow.shared.exceptions import UnauthorizedError

TEST_MASTER_ID = 42


def test_access_token_carries_master_role() -> None:
    token = create_access_token(TEST_MASTER_ID)

    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )

    assert payload['role'] == MASTER_ROLE
    assert (
        get_master_id_from_token(
            token,
            expected_purpose='access',
            expected_role=MASTER_ROLE,
        )
        == TEST_MASTER_ID
    )


def test_token_without_role_is_rejected() -> None:
    token = jwt.encode(
        {
            'sub': str(TEST_MASTER_ID),
            'purpose': 'access',
            'exp': datetime.now(UTC) + timedelta(minutes=5),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(UnauthorizedError):
        get_master_id_from_token(
            token,
            expected_purpose='access',
            expected_role=MASTER_ROLE,
        )
