from http import HTTPStatus

from fastapi.testclient import TestClient

from dojoflow.main import app

client = TestClient(app)


def test_health_deve_retornar_status_ok() -> None:
    response = client.get('/health')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'status': 'ok'}
