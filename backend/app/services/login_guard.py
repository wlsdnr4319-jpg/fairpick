"""
로그인 횟수 제한 (비밀번호 대입 공격 방어, 레퍼런스 10장 보안 항목).

- 같은 이메일: 15분 안에 5번 틀리면 잠근다. 로그인에 성공하면 그 전 실패는 세지 않는다.
- 같은 IP: 15분 안에 20번 틀리면 잠근다. 여러 계정을 돌아가며 찔러보는 공격을 막는다.
- 잠긴 동안에는 비밀번호를 검사하지 않는다. 맞는 비밀번호를 넣어도 429 다
  (그렇지 않으면 잠금 중에도 계속 대입해 볼 수 있다).
- 가입하지 않은 이메일도 똑같이 기록·제한한다. 잠금 여부로 가입 여부를 알아낼 수 없게 한다.

창(window) 방식: 최근 15분 안의 실패만 센다. 가장 오래된 실패가 창 밖으로 나가면 다시 시도할 수 있다.
기록은 DB(login_attempts)에 둔다. uvicorn 워커가 여러 개여도 같은 기준으로 센다.
"""

import math
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import LoginAttempt

WINDOW = timedelta(minutes=15)
MAX_FAILS_PER_EMAIL = 5
MAX_FAILS_PER_IP = 20
KEEP = timedelta(days=1)  # 이보다 오래된 기록은 워커가 지운다


def _unlock_at(db: Session, condition, since: datetime, limit: int) -> datetime | None:
    """
    since 이후 실패가 limit 번 이상이면 잠금이 풀리는 시각, 아니면 None.
    최근 limit 번째 실패가 창 밖으로 나가는 순간 실패 수가 limit 아래로 내려간다.
    """
    nth_recent = db.scalar(
        select(LoginAttempt.created_at)
        .where(condition, LoginAttempt.succeeded.is_(False), LoginAttempt.created_at > since)
        .order_by(LoginAttempt.created_at.desc())
        .offset(limit - 1)
        .limit(1)
    )
    return None if nth_recent is None else nth_recent + WINDOW


def check(db: Session, *, email: str, ip: str, now: datetime) -> None:
    """잠겨 있으면 429 TOO_MANY_ATTEMPTS. 비밀번호 검사 전에 부른다."""
    since = now - WINDOW

    # 이메일 기준: 마지막 성공 이후의 실패만 센다
    last_success = db.scalar(
        select(func.max(LoginAttempt.created_at)).where(
            LoginAttempt.email == email, LoginAttempt.succeeded.is_(True), LoginAttempt.created_at > since
        )
    )
    email_since = max(since, last_success) if last_success else since

    candidates = [
        _unlock_at(db, LoginAttempt.email == email, email_since, MAX_FAILS_PER_EMAIL),
        _unlock_at(db, LoginAttempt.ip == ip, since, MAX_FAILS_PER_IP),
    ]
    unlock_at = max((t for t in candidates if t is not None), default=None)
    if unlock_at is None or unlock_at <= now:
        return

    seconds = max(1, math.ceil((unlock_at - now).total_seconds()))
    minutes = math.ceil(seconds / 60)
    raise AppError(
        429,
        "TOO_MANY_ATTEMPTS",
        f"로그인 시도가 너무 많아요. {minutes}분 뒤에 다시 시도해 주세요",
        headers={"Retry-After": str(seconds)},
    )


def record(db: Session, *, email: str, ip: str, succeeded: bool, now: datetime) -> None:
    db.add(LoginAttempt(email=email, ip=ip[:45], succeeded=succeeded, created_at=now))
    db.flush()


def purge(db: Session, now: datetime) -> int:
    """하루 지난 기록을 지운다. 지운 행 수를 돌려준다."""
    result = db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < now - KEEP))
    return result.rowcount
