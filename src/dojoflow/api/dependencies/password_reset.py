from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.services.password_reset import PasswordResetService


def _get_password_reset_service(
    db_session_dep: DbSessionDep,
) -> PasswordResetService:
    return PasswordResetService(db_session=db_session_dep)


PasswordResetServiceDep = Annotated[
    PasswordResetService, Depends(_get_password_reset_service)
]
