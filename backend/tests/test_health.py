from sqlalchemy.exc import OperationalError

from app.db.session import get_db


class _FakeSession:
    def __init__(self, fail: bool = False):
        self.fail = fail

    def execute(self, *args, **kwargs):
        if self.fail:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    def close(self):
        pass


def _use_session(app, session):
    def override():
        yield session

    app.dependency_overrides[get_db] = override


def test_health_ok(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_db_ok(app, client):
    _use_session(app, _FakeSession())
    res = client.get("/api/v1/health?db=true")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "db": "ok"}


def test_health_db_unavailable_uses_common_error_format(app, client):
    _use_session(app, _FakeSession(fail=True))
    res = client.get("/api/v1/health?db=true")
    assert res.status_code == 503
    assert res.json() == {"error": {"code": "DB_UNAVAILABLE", "message": "DB에 연결할 수 없어요"}}
