from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from dojoflow.shared.exceptions import ConflictError, NotFoundError


async def not_found_error_handler(
    request: Request,
    exc: NotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={'detail': str(exc)},
    )


async def conflict_error_handler(
    request: Request,
    exc: ConflictError,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={'detail': str(exc)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(ConflictError, conflict_error_handler)
