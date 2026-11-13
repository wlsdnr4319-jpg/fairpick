"""
E2E(Playwright) 테스트용 API 서버. 매번 같은 데이터에서 시작하도록 DB 를 비우고 다시 만든다.

실행 (backend/ 폴더에서, Playwright 가 알아서 실행한다):
    python -m app.scripts.e2e_server --port 8001

- DB: E2E_DATABASE_URL 이 있으면 그것을, 없으면 DATABASE_URL 의 DB 이름을 fairpick_e2e 로 바꿔 쓴다.
  개발 DB(fairpick)·단위 테스트 DB(fairpick_test)와 섞이지 않게 이름이 _e2e 로 끝나는 DB 만 비운다.
- 순서: 테이블 전부 삭제 → Alembic 마이그레이션 → 시드(카테고리·태그·전시장·박람회 30건)
  → E2E 데이터(관리자 1명, 검수 대기 수집 항목 6건) → uvicorn
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


# E2E 에서만 쓰는 관리자 계정. 이 DB 는 매번 지워지고 로컬·CI 에서만 뜬다 (frontend/e2e/fixtures.js 와 같은 값)
E2E_ADMIN_EMAIL = "admin@e2e.example.com"
E2E_ADMIN_PASSWORD = "e2e-admin-password"

# 검수 큐에 넣어 둘 수집 항목 (실제 사이트에 요청하지 않는다).
# 승인용·반려용·장소 미확인을 화면 크기(Playwright 프로젝트)마다 1건씩.
# 데스크톱·모바일 테스트가 같은 DB 를 쓰므로 서로의 항목을 처리하지 않게 제목에 프로젝트 이름을 붙인다
E2E_PROJECTS = ("desktop", "mobile")
E2E_CRAWLED = [
    ("approve", "E2E 수집 디저트 페어", "2027.03.05 ~ 2027.03.07", (3, 5), (3, 7)),
    ("reject", "E2E 수집 반려할 행사", "2027.04.01 ~ 2027.04.02", (4, 1), (4, 2)),
    ("unmatched", "E2E 수집 장소 미확인 행사", "2027.05.10 ~ 2027.05.11", (5, 10), (5, 11)),
]


def seed_e2e_fixtures() -> None:
    """시드 다음에 E2E 전용 데이터(관리자 1명, 코엑스 수집 항목 6건)를 넣는다."""
    import hashlib
    from datetime import date

    from sqlalchemy import select

    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models import CrawledItem, CrawlSource, User

    with SessionLocal() as db:
        admin_hash = hash_password(E2E_ADMIN_PASSWORD)
        db.add(User(email=E2E_ADMIN_EMAIL, password_hash=admin_hash, nickname="E2E관리자", role="admin"))
        source = db.scalar(select(CrawlSource).where(CrawlSource.parser_key == "coex"))
        crawled = [(p, kind, f"{title} ({p})", *rest) for p in E2E_PROJECTS for kind, title, *rest in E2E_CRAWLED]
        for project, kind, title, period, (sm, sd), (em, ed) in crawled:
            # 'unmatched' 는 장소를 못 맞춘 항목: 관리자가 전시장을 골라 승인한다
            unmatched = kind == "unmatched"
            venue_text = f"E2E 컨벤션홀 {project}" if unmatched else "코엑스 C홀"
            db.add(
                CrawledItem(
                    source_id=source.id,
                    external_id=f"e2e-{kind}-{project}",
                    raw_title=title,
                    raw_period=period,
                    raw_venue=venue_text,
                    # 코엑스 파서가 남기는 모양 (RawFair.to_payload). 승인 화면이 전시홀을 extra.hall 에서 채운다
                    raw_payload={
                        "external_id": f"e2e-{kind}-{project}",
                        "title": title,
                        "period_text": period,
                        "venue_text": venue_text,
                        "detail_url": "",
                        "extra": {"kind": "전시", "hall": None if unmatched else "C홀"},
                    },
                    parsed_start_date=date(2027, sm, sd),
                    parsed_end_date=date(2027, em, ed),
                    parsed_venue_id=None if unmatched else source.venue_id,
                    content_hash=hashlib.sha256(f"{title}|{period}|{venue_text}".encode()).hexdigest(),
                    change_status="new",
                )
            )
        db.commit()


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
    seed_e2e_fixtures()

    import uvicorn

    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
