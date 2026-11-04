"""
테스트 공통 설정.

- DB 테스트는 SQLite 가 아니라 Docker MySQL 의 fairpick_test DB 를 쓴다.
  ENUM, CHECK, INSERT IGNORE 같은 MySQL 문법 차이로 테스트만 통과하는 일을 막는다 (레퍼런스 13장).
- 테스트 DB 는 세션 시작 때 비우고 Alembic 마이그레이션으로 다시 만든다. 마이그레이션도 함께 검증된다.
- 각 테스트는 트랜잭션 안에서 돌고 끝나면 롤백한다. 테스트끼리 데이터가 섞이지 않는다.

DB 주소: TEST_DATABASE_URL 이 있으면 그것을, 없으면 DATABASE_URL 의 DB 이름을 fairpick_test 로 바꿔 쓴다.
"""

import os
from datetime import date

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.core.deps import get_today
from app.db.session import get_db
from app.main import create_app

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 테스트의 '오늘'. 날짜에 따라 결과가 바뀌지 않도록 고정한다.
TODAY = date(2026, 11, 4)


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return url
    return make_url(get_settings().database_url).set(database="fairpick_test").render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def db_engine():
    url = _test_database_url()
    assert make_url(url).database.endswith("_test"), "테스트는 *_test DB 에서만 돌린다"
    engine = create_engine(url)

    # 비우고 마이그레이션으로 다시 만든다
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in inspect(conn).get_table_names():
            conn.execute(text(f"DROP TABLE `{table}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine, app):
    """테스트 하나를 트랜잭션으로 감싸고 끝나면 롤백한다. API 도 같은 세션을 쓰게 한다."""
    conn = db_engine.connect()
    trans = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


@pytest.fixture
def app():
    application = create_app()
    application.dependency_overrides[get_today] = lambda: TODAY
    return application


@pytest.fixture
def client(app):
    # raise_server_exceptions=False: 500 핸들러가 만든 응답을 그대로 검사하려고 끈다
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
