from typing import Annotated

from fastapi import Depends

from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.integrations.infinitepay.client import InfinitePayClient
from dojoflow.services.infinitepay import InfinitePayService


def get_infinitepay_client() -> InfinitePayClient:
    """Trocado nos testes por uma InfinitePay simulada."""
    return InfinitePayClient()


InfinitePayClientDep = Annotated[
    InfinitePayClient, Depends(get_infinitepay_client)
]


def _get_infinitepay_service(
    db_session_dep: DbSessionDep, client: InfinitePayClientDep
) -> InfinitePayService:
    return InfinitePayService(db_session=db_session_dep, client=client)


InfinitePayServiceDep = Annotated[
    InfinitePayService, Depends(_get_infinitepay_service)
]
