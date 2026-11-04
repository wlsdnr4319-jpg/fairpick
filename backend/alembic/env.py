"""
Alembic 마이그레이션 환경.

스키마 변경은 Alembic 으로만 한다 (레퍼런스 14장 운영 체크리스트).
    alembic revision --autogenerate -m "설명"   # 모델 변경 → 마이그레이션 파일 생성
    alembic upgrade head                        # DB 에 적용

DB 주소는 alembic.ini 가 아니라 .env 의 DATABASE_URL 을 쓴다 (비밀번호를 저장소에 남기지 않기 위해).
테스트처럼 다른 DB 에 적용할 때는 ALEMBIC_DATABASE_URL 로 덮어쓴다.
"""

import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  모든 모델을 Base.metadata 에 등록
from alembic import context
from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    return os.environ.get("ALEMBIC_DATABASE_URL") or get_settings().database_url


def run_migrations_offline() -> None:
    """DB 에 접속하지 않고 SQL 만 출력한다: alembic upgrade head --sql"""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = config.attributes.get("connection")
    if connectable is not None:
        # 테스트에서 연결을 직접 넘긴 경우
        _run(connectable)
        return

    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        _run(connection)


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # 컬럼 타입 변경도 autogenerate 가 감지하게 한다
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
