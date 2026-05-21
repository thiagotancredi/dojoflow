from fastapi import FastAPI

from dojoflow.api.routes.health import router as health_router

app = FastAPI(
    title='Dojoflow API',
    description='API for Dojoflow, a workflow automation tool.',
    version='1.0.0',
)

app.include_router(health_router, prefix='')
