from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# 제약조건 이름 규칙. 이름이 정해져 있어야 Alembic 이 나중에 제약을 지우거나 바꿀 수 있다.
# CHECK 제약은 모델에서 이름을 직접 지정한다 (예: ck_fairs_period).
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """모든 SQLAlchemy 모델의 부모 클래스. 모델은 app/models/ 에 있다."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
