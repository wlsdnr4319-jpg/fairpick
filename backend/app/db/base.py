from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 SQLAlchemy 모델의 부모 클래스. 모델은 2주차에 app/models/ 에 추가한다."""
