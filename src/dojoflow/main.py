from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dojoflow.api.exception_handlers import register_exception_handlers
from dojoflow.api.routes.auth import router as auth_router
from dojoflow.api.routes.belts import router as belts_router
from dojoflow.api.routes.cep import router as cep_router
from dojoflow.api.routes.dashboard import router as dashboard_router
from dojoflow.api.routes.enrollment_belts import (
    router as enrollment_belts_router,
)
from dojoflow.api.routes.graduation_lists import (
    router as graduation_lists_router,
)
from dojoflow.api.routes.health import router as health_router
from dojoflow.api.routes.modalities import router as modalities_router
from dojoflow.api.routes.onboarding import router as onboarding_router
from dojoflow.api.routes.students import router as students_router
from dojoflow.api.routes.telegram import router as telegram_router
from dojoflow.core.settings import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        'API for DojoFlow — academy tuition management via Telegram and web.'
    ),
    version='1.0.0',
)

if settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(onboarding_router, prefix=settings.API_V1_PREFIX)
app.include_router(modalities_router, prefix=settings.API_V1_PREFIX)
app.include_router(belts_router, prefix=settings.API_V1_PREFIX)
app.include_router(students_router, prefix=settings.API_V1_PREFIX)
app.include_router(enrollment_belts_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(graduation_lists_router, prefix=settings.API_V1_PREFIX)
app.include_router(cep_router, prefix=settings.API_V1_PREFIX)
app.include_router(telegram_router, prefix=settings.API_V1_PREFIX)
