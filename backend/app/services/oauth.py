"""
소셜 로그인 (카카오·구글, OAuth 2.0 Authorization Code 방식).

흐름
1. /auth/oauth/{provider}/start: state(위조 방지용 무작위 값)를 httpOnly 쿠키에 넣고 제공자 로그인 화면으로 보낸다.
2. 제공자가 /callback?code=…&state=… 로 돌려보낸다. 쿠키의 state 와 같아야 한다 (CSRF 방지).
3. code 를 액세스 토큰으로 바꾸고(서버 간 요청, client secret 사용) 사용자 정보를 받는다.
4. 회원을 찾거나 연결하거나 만든다 (resolve_user). 이후는 이메일 로그인과 같다: 리프레시 쿠키 발급.

회원 연결 규칙
- 이미 연결된 소셜 계정 → 그 회원
- 제공자가 '확인된' 이메일을 주고 같은 이메일 회원이 있으면 → 그 회원에 연결.
  확인되지 않은 이메일로 연결하면 남의 이메일로 소셜 계정을 만들어 그 회원 계정에 들어갈 수 있다.
- 그 밖에는 새 회원. 확인된 이메일이 없으면 이메일 없이 만든다 (알림 메일은 받을 수 없다).
- 새 회원은 만 14세 이상 확인(가입 화면 체크박스)을 거친 경우에만 만든다.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import SocialAccount, User
from app.services.notifications import ensure_settings

logger = logging.getLogger(__name__)

DEFAULT_NICKNAME = "페어픽 회원"


class OAuthError(Exception):
    """code 는 프론트로 돌려보내는 오류 코드다 (/login?oauth_error=CODE)."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


@dataclass(frozen=True)
class Provider:
    name: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str
    client_id: str
    client_secret: str


@dataclass(frozen=True)
class OAuthProfile:
    provider: str
    provider_user_id: str
    email: str | None  # 제공자가 확인했다고 밝힌 이메일만. 아니면 None
    nickname: str


def configured_providers() -> dict[str, Provider]:
    """키가 설정된 제공자만 돌려준다."""
    s = get_settings()
    candidates = [
        Provider(
            name="kakao",
            authorize_url="https://kauth.kakao.com/oauth/authorize",
            token_url="https://kauth.kakao.com/oauth/token",
            userinfo_url="https://kapi.kakao.com/v2/user/me",
            # 카카오는 scope 를 비우면 콘솔에서 설정한 동의항목을 묻는다. 설정하지 않은 항목(예: 이메일)을
            # scope 로 요청하면 KOE205 오류가 나므로, 무엇을 받을지는 콘솔 설정에 맡긴다
            scope="",
            client_id=s.kakao_client_id,
            client_secret=s.kakao_client_secret,
        ),
        Provider(
            name="google",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            scope="openid email profile",
            client_id=s.google_client_id,
            client_secret=s.google_client_secret,
        ),
    ]
    return {p.name: p for p in candidates if p.client_id}


def redirect_uri(provider: str) -> str:
    """제공자 콘솔에 등록하는 주소와 글자 하나까지 같아야 한다."""
    return f"{get_settings().app_base_url.rstrip('/')}/api/v1/auth/oauth/{provider}/callback"


def authorize_url(provider: Provider, state: str) -> str:
    params = {
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri(provider.name),
        "response_type": "code",
        "state": state,
    }
    if provider.scope:
        params["scope"] = provider.scope
    if provider.name == "google":
        params["prompt"] = "select_account"  # 여러 구글 계정 중 고르게 한다
    return f"{provider.authorize_url}?{urlencode(params)}"


def fetch_profile(http: httpx.Client, provider: Provider, code: str) -> OAuthProfile:
    """code → 액세스 토큰 → 사용자 정보. 실패하면 OAuthError('OAUTH_PROVIDER_ERROR')."""
    data = {
        "grant_type": "authorization_code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri(provider.name),
        "code": code,
    }
    if provider.client_secret:
        data["client_secret"] = provider.client_secret
    try:
        token_res = http.post(provider.token_url, data=data)
        if token_res.status_code != 200:
            raise OAuthError("OAUTH_PROVIDER_ERROR", f"token {token_res.status_code}: {token_res.text[:200]}")
        access_token = token_res.json().get("access_token")
        if not access_token:
            raise OAuthError("OAUTH_PROVIDER_ERROR", "token response has no access_token")
        info_res = http.get(provider.userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
        if info_res.status_code != 200:
            raise OAuthError("OAUTH_PROVIDER_ERROR", f"userinfo {info_res.status_code}")
        info = info_res.json()
    except (httpx.HTTPError, ValueError) as exc:  # 네트워크 오류, JSON 아님
        raise OAuthError("OAUTH_PROVIDER_ERROR", f"{type(exc).__name__}: {exc}") from exc
    return _parse_profile(provider.name, info)


def _parse_profile(provider: str, info: dict) -> OAuthProfile:
    if provider == "kakao":
        account = info.get("kakao_account") or {}
        verified = account.get("is_email_valid") and account.get("is_email_verified")
        email = account.get("email") if verified else None
        nickname = (account.get("profile") or {}).get("nickname") or (info.get("properties") or {}).get("nickname")
        user_id = info.get("id")
    else:  # google (OpenID Connect userinfo)
        email = info.get("email") if info.get("email_verified") is True else None
        nickname = info.get("name")
        user_id = info.get("sub")
    if user_id in (None, ""):
        raise OAuthError("OAUTH_PROVIDER_ERROR", "userinfo has no user id")
    nickname = (nickname or "").strip()[:30] or DEFAULT_NICKNAME
    return OAuthProfile(
        provider=provider,
        provider_user_id=str(user_id),
        email=email.strip().lower() if email else None,
        nickname=nickname,
    )


def resolve_user(db: Session, profile: OAuthProfile, *, allow_signup: bool, now: datetime) -> User:
    """연결된 회원을 찾거나, 확인된 이메일로 연결하거나, 새로 만든다. 위 모듈 설명의 규칙을 따른다."""
    linked = db.scalar(
        select(SocialAccount).where(
            SocialAccount.provider == profile.provider, SocialAccount.provider_user_id == profile.provider_user_id
        )
    )
    if linked is not None:
        return linked.user

    user = db.scalar(select(User).where(User.email == profile.email)) if profile.email else None
    if user is None:
        if not allow_signup:
            # 로그인 화면에서 처음 온 사람. 가입 화면에서 만 14세 이상 확인 후 다시 시도한다
            raise OAuthError("OAUTH_SIGNUP_REQUIRED")
        user = User(email=profile.email, password_hash=None, nickname=profile.nickname, role="user")
        db.add(user)
        db.flush()
        ensure_settings(db, user.id)

    db.add(
        SocialAccount(
            user_id=user.id,
            provider=profile.provider,
            provider_user_id=profile.provider_user_id,
            email=profile.email,
            created_at=now,
        )
    )
    try:
        db.flush()
    except IntegrityError:  # 같은 계정으로 동시에 두 번 콜백이 온 경우
        db.rollback()
        raise OAuthError("OAUTH_RETRY", "concurrent link") from None
    return user
