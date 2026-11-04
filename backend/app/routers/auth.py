"""
인증 API (레퍼런스 7장 '인증·회원', 10장).

POST /api/v1/auth/signup   회원가입
POST /api/v1/auth/login    로그인: 본문으로 액세스 토큰, Set-Cookie 로 리프레시 토큰
POST /api/v1/auth/refresh  액세스 토큰 재발급 (리프레시 쿠키, 회전)
POST /api/v1/auth/logout   리프레시 토큰 폐기, 쿠키 삭제
"""

from fastapi import APIRouter, Cookie, Response, status

from app.core.config import get_settings
from app.core.deps import DbSession, Now
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import (
    LoginIn,
    MessageOut,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    SignupIn,
    TokenOut,
    UserOut,
)
from app.services import auth as auth_service
from app.services import mail
from app.services.notifications import ensure_settings

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
# 리프레시 쿠키는 인증 API 에만 실려 가도록 Path 를 제한한다
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_days * 24 * 3600,
        httponly=True,  # 스크립트로 꺼낼 수 없다
        secure=settings.cookie_secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


def _token_out(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id, user.role),
        expires_in=get_settings().access_token_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn, db: DbSession):
    user = auth_service.signup(db, email=body.email, password=body.password, nickname=body.nickname)
    ensure_settings(db, user.id)  # 알림 설정 기본값을 함께 만든다
    db.commit()
    return user


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, response: Response, db: DbSession, now: Now):
    user = auth_service.authenticate(db, email=body.email, password=body.password)
    refresh = auth_service.issue_refresh_token(db, user, now)
    db.commit()
    _set_refresh_cookie(response, refresh)
    return _token_out(user)


@router.post("/refresh", response_model=TokenOut)
def refresh(
    response: Response,
    db: DbSession,
    now: Now,
    refresh_token: str | None = Cookie(default=None),
):
    user, new_refresh = auth_service.rotate_refresh_token(db, refresh_token, now)
    db.commit()
    _set_refresh_cookie(response, new_refresh)
    return _token_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: DbSession,
    now: Now,
    refresh_token: str | None = Cookie(default=None),
):
    auth_service.revoke(db, refresh_token, now)
    db.commit()
    clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/password-reset/request", response_model=MessageOut)
def password_reset_request(body: PasswordResetRequestIn, db: DbSession, now: Now):
    """가입 여부와 관계없이 같은 응답을 준다. 이메일 가입 여부를 알아내는 데 쓰이지 않게 한다 (레퍼런스 10장)."""
    found = auth_service.request_password_reset(db, body.email, now)
    db.commit()
    if found:
        user, token = found
        base = get_settings().app_base_url.rstrip("/")
        try:
            mail.send(
                mail.Mail(
                    to=user.email,
                    subject="[페어픽] 비밀번호 재설정 안내",
                    template="password_reset",
                    context={"reset_url": f"{base}/reset-password?token={token}"},
                )
            )
        except Exception:
            # 메일 실패도 응답을 바꾸지 않는다 (가입 여부 노출 방지). 원인은 로그에만 남긴다
            import logging

            logging.getLogger(__name__).exception("password reset mail failed")
    return MessageOut(message="가입된 이메일이면 재설정 링크를 보냈어요. 메일함을 확인해 주세요")


@router.post("/password-reset/confirm", response_model=MessageOut)
def password_reset_confirm(body: PasswordResetConfirmIn, db: DbSession, now: Now, response: Response):
    auth_service.confirm_password_reset(db, body.token, body.new_password, now)
    db.commit()
    clear_refresh_cookie(response)
    return MessageOut(message="비밀번호를 바꿨어요. 새 비밀번호로 로그인해 주세요")
