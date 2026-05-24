from fastapi import FastAPI

from dojoflow.api.exception_handlers import register_exception_handlers
from dojoflow.api.routes.health import router as health_router
from dojoflow.api.routes.onboarding import router as onboarding_router

app = FastAPI(
    title='Dojoflow API',
    description='API for Dojoflow, a workflow automation tool.',
    version='1.0.0',
)

register_exception_handlers(app)

app.include_router(health_router, prefix='')
app.include_router(onboarding_router, prefix='/api/v1')
