"""
DB 세션. MVP 는 동기 SQLAlchemy 세션 + def 엔드포인트로 만든다 (레퍼런스 5장).
async def 안에서 동기 DB 호출을 하면 이벤트 루프가 막혀 다른 요청까지 느려진다.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,  # 끊긴 연결을 쓰기 전에 확인
    pool_recycle=3600,  # MySQL wait_timeout 보다 먼저 연결을 새로 만든다
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
