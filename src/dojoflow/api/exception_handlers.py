from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from dojoflow.shared.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)


async def not_found_error_handler(
    request: Request,
    exc: NotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={'detail': str(exc), 'code': exc.code},
    )


async def conflict_error_handler(
    request: Request,
    exc: ConflictError,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'detail': str(exc), 'code': exc.code},
    )


async def unauthorized_error_handler(
    request: Request,
    exc: UnauthorizedError,
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={'detail': str(exc), 'code': exc.code},
        headers={'WWW-Authenticate': 'Bearer'},
    )


async def forbidden_error_handler(
    request: Request,
    exc: ForbiddenError,
) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={'detail': str(exc), 'code': exc.code},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(ConflictError, conflict_error_handler)
    app.add_exception_handler(UnauthorizedError, unauthorized_error_handler)
    app.add_exception_handler(ForbiddenError, forbidden_error_handler)
