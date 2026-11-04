"""
소셜 로그인 API (app/services/oauth.py 의 흐름).

GET /api/v1/auth/oauth/providers            키가 설정된 제공자 목록 (프론트가 버튼을 보일지 정한다)
GET /api/v1/auth/oauth/{provider}/start     제공자 로그인 화면으로 이동.
                                            ?signup=true 는 가입 화면(만 14세 확인)에서 왔다는 뜻
GET /api/v1/auth/oauth/{provider}/callback  제공자가 돌려보내는 주소.
                                            성공하면 리프레시 쿠키를 심고 프론트 /oauth/callback 으로

브라우저가 직접 오가는 주소라 JSON 대신 리다이렉트로 응답한다. 실패는 /login?oauth_error=코드 로 보낸다.
액세스 토큰은 주소에 싣지 않는다. 프론트가 돌아온 뒤 기존처럼 /auth/refresh 로 받는다
(주소는 서버 기록·Referer 로 샐 수 있다).
"""

import hmac
import logging
import secrets
from collections.abc import Iterator
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Cookie, Depends
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.deps import DbSession, Now
from app.routers.auth import set_refresh_cookie
from app.services import auth as auth_service
from app.services import oauth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/oauth", tags=["auth"])

STATE_COOKIE = "oauth_state"
STATE_COOKIE_PATH = "/api/v1/auth/oauth"
STATE_TTL_SECONDS = 600  # 제공자 로그인 화면에서 10분 안에 돌아와야 한다

ProviderName = Literal["kakao", "google"]


def get_oauth_http() -> Iterator[httpx.Client]:
    """제공자 서버와 통신하는 클라이언트. 테스트에서 가짜 응답을 주는 클라이언트로 바꾼다."""
    with httpx.Client(timeout=10.0) as client:
        yield client


OAuthHttp = Annotated[httpx.Client, Depends(get_oauth_http)]


def _front(path: str) -> str:
    return f"{get_settings().app_base_url.rstrip('/')}{path}"


def _fail(code: str, *, signup: bool = False) -> RedirectResponse:
    page = "/signup" if signup else "/login"
    res = RedirectResponse(_front(f"{page}?oauth_error={code}"), status_code=302)
    res.delete_cookie(STATE_COOKIE, path=STATE_COOKIE_PATH)
    return res


@router.get("/providers")
def providers() -> dict[str, list[str]]:
    return {"providers": list(oauth.configured_providers())}


@router.get("/{provider}/start")
def start(provider: ProviderName, signup: bool = False):
    found = oauth.configured_providers().get(provider)
    if found is None:
        return _fail("OAUTH_NOT_CONFIGURED", signup=signup)
    state = secrets.token_urlsafe(32)
    res = RedirectResponse(oauth.authorize_url(found, state), status_code=302)
    # 쿠키 값: state.가입여부. 콜백 때 주소의 state 와 비교한다
    res.set_cookie(
        STATE_COOKIE,
        f"{state}.{int(signup)}",
        max_age=STATE_TTL_SECONDS,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",  # 제공자에서 돌아오는 최상위 GET 이동에는 쿠키가 실린다
        path=STATE_COOKIE_PATH,
    )
    return res


@router.get("/{provider}/callback")
def callback(
    provider: ProviderName,
    db: DbSession,
    now: Now,
    http: OAuthHttp,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None),
):
    expected, _, signup_flag = (oauth_state or "").partition(".")
    signup = signup_flag == "1"
    # state 가 없거나 다르면 우리가 시작한 로그인이 아니다 (CSRF: 공격자의 code 로 피해자를 로그인시키는 공격)
    if not (state and expected and hmac.compare_digest(state, expected)):
        return _fail("OAUTH_STATE_MISMATCH", signup=signup)
    if error or not code:
        # 사용자가 제공자 화면에서 '취소'를 누르면 error=access_denied 로 온다
        return _fail("OAUTH_CANCELLED", signup=signup)
    found = oauth.configured_providers().get(provider)
    if found is None:
        return _fail("OAUTH_NOT_CONFIGURED", signup=signup)

    try:
        profile = oauth.fetch_profile(http, found, code)
        user = oauth.resolve_user(db, profile, allow_signup=signup, now=now)
        refresh = auth_service.issue_refresh_token(db, user, now)
        db.commit()
    except oauth.OAuthError as exc:
        db.rollback()
        logger.warning("oauth %s failed: %s", provider, exc)
        return _fail(exc.code, signup=signup or exc.code == "OAUTH_SIGNUP_REQUIRED")

    res = RedirectResponse(_front("/oauth/callback"), status_code=302)
    res.delete_cookie(STATE_COOKIE, path=STATE_COOKIE_PATH)  # state 는 한 번만 쓴다
    set_refresh_cookie(res, refresh)
    return res
