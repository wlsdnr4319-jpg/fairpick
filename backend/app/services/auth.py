"""
회원과 토큰 로직 (레퍼런스 10장 '로그인과 재발급 흐름').

리프레시 토큰은 쓸 때마다 새로 발급하고 이전 토큰을 폐기한다(회전).
이미 폐기된 토큰이 다시 들어오면 탈취로 보고 그 사용자의 리프레시 토큰을 모두 폐기한다.
"""

from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.models import RefreshToken, User


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def signup(db: Session, *, email: str, password: str, nickname: str) -> User:
    email = _normalize_email(email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise AppError(409, "EMAIL_TAKEN", "이미 가입된 이메일이에요")
    user = User(email=email, password_hash=hash_password(password), nickname=nickname, role="user")
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # 동시에 같은 이메일로 가입한 경우
        db.rollback()
        raise AppError(409, "EMAIL_TAKEN", "이미 가입된 이메일이에요") from None
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == _normalize_email(email)))
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)  # 응답 시간을 맞춘다
        raise AppError(401, "INVALID_CREDENTIALS", "이메일이나 비밀번호가 맞지 않아요")
    if not verify_password(password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "이메일이나 비밀번호가 맞지 않아요")
    return user


def issue_refresh_token(db: Session, user: User, now: datetime) -> str:
    token = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=now + timedelta(days=get_settings().refresh_token_days),
            created_at=now,
        )
    )
    db.flush()
    return token


def rotate_refresh_token(db: Session, token: str | None, now: datetime) -> tuple[User, str]:
    """유효한 리프레시 토큰이면 폐기하고 새 토큰을 발급한다."""
    if not token:
        raise AppError(401, "INVALID_REFRESH_TOKEN", "다시 로그인해 주세요")

    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    if row is None or row.expires_at <= now:
        raise AppError(401, "INVALID_REFRESH_TOKEN", "다시 로그인해 주세요")

    if row.revoked_at is not None:
        # 폐기된 토큰 재사용 = 탈취 의심 → 이 사용자의 모든 리프레시 토큰 폐기
        revoke_all(db, row.user_id, now)
        db.commit()
        raise AppError(401, "INVALID_REFRESH_TOKEN", "다시 로그인해 주세요")

    row.revoked_at = now
    user = db.get(User, row.user_id)
    new_token = issue_refresh_token(db, user, now)
    return user, new_token


def revoke(db: Session, token: str | None, now: datetime) -> None:
    if not token:
        return
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(token), RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def revoke_all(db: Session, user_id: int, now: datetime) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


# ---------------------------------------------------------------------------
# 비밀번호 재설정 (레퍼런스 10장): 토큰은 30분 유효, 1회용, 해시로 저장한다
# ---------------------------------------------------------------------------

RESET_TTL = timedelta(minutes=30)


def request_password_reset(db: Session, email: str, now: datetime) -> tuple[User, str] | None:
    """가입된 이메일이면 (사용자, 토큰), 아니면 None. 호출한 쪽은 두 경우 모두 같은 응답을 준다."""
    from app.models import PasswordResetToken

    user = db.scalar(select(User).where(User.email == _normalize_email(email)))
    if user is None:
        return None
    token = new_refresh_token()
    db.add(
        PasswordResetToken(user_id=user.id, token_hash=hash_token(token), expires_at=now + RESET_TTL, created_at=now)
    )
    db.flush()
    return user, token


def confirm_password_reset(db: Session, token: str, new_password: str, now: datetime) -> User:
    from app.models import PasswordResetToken

    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token)))
    if row is None or row.used_at is not None or row.expires_at <= now:
        raise AppError(400, "INVALID_RESET_TOKEN", "링크가 만료됐거나 이미 사용했어요. 다시 요청해 주세요")
    user = db.get(User, row.user_id)
    user.password_hash = hash_password(new_password)
    row.used_at = now
    revoke_all(db, user.id, now)  # 다른 기기의 로그인도 끊는다
    return user
