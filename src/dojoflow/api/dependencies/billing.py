from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.services.billing import BillingService


def _get_billing_service(db_session_dep: DbSessionDep) -> BillingService:
    return BillingService(db_session=db_session_dep)


BillingServiceDep = Annotated[BillingService, Depends(_get_billing_service)]
