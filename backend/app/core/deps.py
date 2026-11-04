"""공통 의존성. 테스트에서 app.dependency_overrides 로 바꿔 끼울 수 있다."""

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.core.timeutil import today_kst
from app.db.session import get_db
from app.models import User


def get_today() -> date:
    """
    오늘(한국 시간). 시간에 따라 결과가 바뀌는 로직은 today 를 인자로 받아,
    테스트에서 날짜를 고정할 수 있게 한다 (레퍼런스 13장 테스트 환경).
    """
    return today_kst()


def get_now() -> datetime:
    """현재 시각 (UTC, 시간대 없음 = DB 저장 형식)."""
    return datetime.now(UTC).replace(tzinfo=None)


_bearer = HTTPBearer(auto_error=False)


def get_current_user_optional(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    """로그인하지 않았으면 None. 토큰이 있는데 만료·위조면 401 (프론트가 재발급 후 재시도)."""
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise AppError(401, "INVALID_TOKEN", "로그인 정보가 올바르지 않아요")
    return user


def get_current_user(user: Annotated[User | None, Depends(get_current_user_optional)]) -> User:
    if user is None:
        raise AppError(401, "UNAUTHORIZED", "로그인이 필요해요")
    return user


def get_current_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise AppError(403, "ADMIN_ONLY", "관리자만 이용할 수 있어요")
    return user


DbSession = Annotated[Session, Depends(get_db)]
Today = Annotated[date, Depends(get_today)]
Now = Annotated[datetime, Depends(get_now)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
