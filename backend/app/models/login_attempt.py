from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import utcnow


class LoginAttempt(Base):
    """
    로그인 시도 기록. 비밀번호 대입 공격을 막는 횟수 제한에 쓴다 (app/services/login_guard.py).

    가입하지 않은 이메일도 같은 방식으로 기록·제한한다. 그래야 잠금 여부로 가입 여부를 알아낼 수 없다.
    users 와 FK 로 묶지 않는다. 하루 지난 기록은 워커가 지운다.
    """

    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_email_created_at", "email", "created_at"),
        Index("ix_login_attempts_ip_created_at", "ip", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255))  # 소문자로 정규화한 값
    ip: Mapped[str] = mapped_column(String(45))  # IPv6 최대 길이
    succeeded: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
