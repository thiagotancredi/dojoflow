from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dojoflow.api.exception_handlers import register_exception_handlers
from dojoflow.api.routes.admin import router as admin_router
from dojoflow.api.routes.auth import router as auth_router
from dojoflow.api.routes.belts import router as belts_router
from dojoflow.api.routes.billing import (
    overview_router as billing_overview_router,
)
from dojoflow.api.routes.billing import router as billing_router
from dojoflow.api.routes.billing import (
    settings_router as billing_settings_router,
)
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
from dojoflow.api.routes.public_pay import router as public_pay_router
from dojoflow.api.routes.students import router as students_router
from dojoflow.core.settings import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        'API for Katsuflow — tuition and belt management for martial arts '
        'academies.'
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
app.include_router(modalities_router, prefix=settings.API_V1_PREFIX)
app.include_router(belts_router, prefix=settings.API_V1_PREFIX)
app.include_router(students_router, prefix=settings.API_V1_PREFIX)
app.include_router(enrollment_belts_router, prefix=settings.API_V1_PREFIX)
app.include_router(billing_router, prefix=settings.API_V1_PREFIX)
app.include_router(billing_settings_router, prefix=settings.API_V1_PREFIX)
app.include_router(billing_overview_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(graduation_lists_router, prefix=settings.API_V1_PREFIX)
app.include_router(cep_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
app.include_router(public_pay_router, prefix=settings.API_V1_PREFIX)
