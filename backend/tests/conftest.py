import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    # raise_server_exceptions=False: 500 핸들러가 만든 응답을 그대로 검사하려고 끈다
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
