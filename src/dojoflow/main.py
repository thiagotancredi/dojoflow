from fastapi import FastAPI

from dojoflow.api.exception_handlers import register_exception_handlers
from dojoflow.api.routes.health import router as health_router
from dojoflow.api.routes.master import router as master_router
from dojoflow.api.routes.onboarding import router as onboarding_router
from dojoflow.api.routes.telegram import router as telegram_router
from dojoflow.core.settings import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description='API for Dojoflow, a workflow automation tool.',
    version='1.0.0',
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(onboarding_router, prefix=settings.API_V1_PREFIX)
app.include_router(master_router, prefix=settings.API_V1_PREFIX)
app.include_router(telegram_router, prefix=settings.API_V1_PREFIX)
