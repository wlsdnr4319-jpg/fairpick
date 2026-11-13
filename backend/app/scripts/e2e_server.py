"""
E2E(Playwright) 테스트용 API 서버. 매번 같은 데이터에서 시작하도록 DB 를 비우고 다시 만든다.

실행 (backend/ 폴더에서, Playwright 가 알아서 실행한다):
    python -m app.scripts.e2e_server --port 8001

- DB: E2E_DATABASE_URL 이 있으면 그것을, 없으면 DATABASE_URL 의 DB 이름을 fairpick_e2e 로 바꿔 쓴다.
  개발 DB(fairpick)·단위 테스트 DB(fairpick_test)와 섞이지 않게 이름이 _e2e 로 끝나는 DB 만 비운다.
- 순서: 테이블 전부 삭제 → Alembic 마이그레이션 → 시드(카테고리·태그·전시장·박람회 30건) → uvicorn
"""

import argparse
import os

from sqlalchemy.engine import make_url

from app.core.config import get_settings

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def e2e_database_url() -> str:
    url = os.environ.get("E2E_DATABASE_URL")
    if not url:
        url = make_url(get_settings().database_url).set(database="fairpick_e2e").render_as_string(hide_password=False)
    if not make_url(url).database.endswith("_e2e"):
        raise SystemExit("E2E 서버는 이름이 _e2e 로 끝나는 DB 만 쓴다 (DB 를 비우기 때문)")
    return url


def reset_database(url: str) -> None:
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text

    from alembic import command

    engine = create_engine(url)
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
    engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    url = e2e_database_url()
    # 앱의 DB 엔진은 import 할 때 설정을 읽어 만들어지므로, 앱을 import 하기 전에 주소를 바꿔 둔다
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()

    reset_database(url)

    from app.scripts import seed

    seed.main()

    import uvicorn

    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
