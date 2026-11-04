from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.services.email_billing import EmailBillingService


def _get_email_billing_service(
    db_session_dep: DbSessionDep,
) -> EmailBillingService:
    return EmailBillingService(db_session=db_session_dep)


EmailBillingServiceDep = Annotated[
    EmailBillingService, Depends(_get_email_billing_service)
]
