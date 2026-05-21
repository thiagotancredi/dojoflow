from fastapi import APIRouter

router = APIRouter(tags=['Health'])


@router.get(
    '/health',
    summary='Check API health',
    description='Returns the health status of the API.',
)
def health_check():
    return {'status': 'ok'}
