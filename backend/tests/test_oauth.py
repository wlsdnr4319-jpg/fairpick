"""
소셜 로그인 (app/routers/oauth.py, services/oauth.py).
카카오·구글 서버에는 요청하지 않는다. httpx.MockTransport 로 토큰·사용자 정보 응답을 흉내 낸다.
"""

from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models import SocialAccount, User
from app.routers.oauth import get_oauth_http
from tests import factories as f

FRONT = "http://localhost:5173"


def kakao_user(user_id=1001, email="me@example.com", verified=True, nickname="카카오진욱"):
    return {
        "id": user_id,
        "kakao_account": {
            "email": email,
            "is_email_valid": verified,
            "is_email_verified": verified,
            "profile": {"nickname": nickname},
        },
    }


def google_user(sub="g-1", email="me@example.com", verified=True, name="Google Jin"):
    return {"sub": sub, "email": email, "email_verified": verified, "name": name}


@pytest.fixture
def provider_api(app, monkeypatch):
    """제공자 키를 설정하고, 제공자 서버 응답을 테스트가 정할 수 있게 한다."""
    settings = get_settings()
    for key, value in {
        "kakao_client_id": "kakao-id",
        "google_client_id": "google-id",
        "google_client_secret": "google-secret",
        "app_base_url": FRONT,
    }.items():
        monkeypatch.setattr(settings, key, value)

    state = {"userinfo": kakao_user(), "token_status": 200, "requests": []}

    def handler(request: httpx.Request) -> httpx.Response:
        state["requests"].append(request)
        if request.url.path in ("/oauth/token", "/token"):
            if state["token_status"] != 200:
                return httpx.Response(state["token_status"], json={"error": "invalid_grant"})
            return httpx.Response(200, json={"access_token": "provider-access-token"})
        assert request.headers["Authorization"] == "Bearer provider-access-token"
        return httpx.Response(200, json=state["userinfo"])

    def override():
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            yield client

    app.dependency_overrides[get_oauth_http] = override
    return state


def _login(client, provider="kakao", *, signup=False, state=None, code="auth-code"):
    """start → (제공자 로그인) → callback. callback 응답을 돌려준다."""
    res = client.get(f"/api/v1/auth/oauth/{provider}/start", params={"signup": signup}, follow_redirects=False)
    assert res.status_code == 302
    sent_state = parse_qs(urlsplit(res.headers["location"]).query)["state"][0]
    return client.get(
        f"/api/v1/auth/oauth/{provider}/callback",
        params={"code": code, "state": state or sent_state},
        follow_redirects=False,
    )


def _error(res) -> str | None:
    return parse_qs(urlsplit(res.headers["location"]).query).get("oauth_error", [None])[0]


def _users(db) -> int:
    return db.scalar(select(func.count()).select_from(User))


def test_not_configured(db, client):
    assert client.get("/api/v1/auth/oauth/providers").json() == {"providers": []}
    res = client.get("/api/v1/auth/oauth/kakao/start", follow_redirects=False)
    assert res.status_code == 302 and _error(res) == "OAUTH_NOT_CONFIGURED"
    assert client.get("/api/v1/auth/oauth/naver/start", follow_redirects=False).status_code == 422


def test_start_redirects_to_provider_with_state_cookie(db, client, provider_api):
    assert client.get("/api/v1/auth/oauth/providers").json() == {"providers": ["kakao", "google"]}
    res = client.get("/api/v1/auth/oauth/kakao/start", follow_redirects=False)
    url = urlsplit(res.headers["location"])
    query = parse_qs(url.query)
    assert url.netloc == "kauth.kakao.com"
    assert query["client_id"] == ["kakao-id"]
    assert query["redirect_uri"] == [f"{FRONT}/api/v1/auth/oauth/kakao/callback"]
    assert "scope" not in query  # 카카오는 콘솔의 동의항목 설정을 따른다 (설정 안 한 항목을 요청하면 KOE205)
    cookie = res.headers["set-cookie"]
    assert cookie.startswith(f"oauth_state={query['state'][0]}.0") and "HttpOnly" in cookie
    assert "Path=/api/v1/auth/oauth" in cookie


def test_signup_then_login_with_kakao(db, client, provider_api):
    res = _login(client, signup=True)
    assert res.status_code == 302 and res.headers["location"] == f"{FRONT}/oauth/callback"
    cookies = res.headers.get_list("set-cookie")
    assert any(c.startswith("refresh_token=") and "HttpOnly" in c for c in cookies)
    assert any(c.startswith("oauth_state=") and "Max-Age=0" in c for c in cookies)  # state 는 한 번만 쓴다

    user = db.scalar(select(User))
    assert (user.email, user.nickname, user.password_hash) == ("me@example.com", "카카오진욱", None)
    link = db.scalar(select(SocialAccount))
    assert (link.provider, link.provider_user_id, link.user_id) == ("kakao", "1001", user.id)

    # 돌아온 프론트는 기존처럼 /auth/refresh 로 액세스 토큰을 받는다
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200 and refreshed.json()["user"]["id"] == user.id

    # 다음부터는 로그인 화면(가입 확인 없음)에서 들어와도 같은 회원
    client.cookies.clear()
    assert _login(client).headers["location"] == f"{FRONT}/oauth/callback"
    assert _users(db) == 1

    # 비밀번호가 없는 회원은 이메일 로그인이 안 된다
    res = client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": "anything"})
    assert res.status_code == 401


def test_first_login_from_login_page_requires_signup_consent(db, client, provider_api):
    res = _login(client, signup=False)
    assert res.headers["location"].startswith(f"{FRONT}/signup?") and _error(res) == "OAUTH_SIGNUP_REQUIRED"
    assert _users(db) == 0


def test_verified_email_links_existing_member(db, client, provider_api):
    member = f.user(db, email="me@example.com")
    provider_api["userinfo"] = google_user()
    start = client.get("/api/v1/auth/oauth/google/start", follow_redirects=False)
    assert parse_qs(urlsplit(start.headers["location"]).query)["scope"] == ["openid email profile"]
    res = _login(client, "google")  # 로그인 화면에서 와도 기존 회원이면 연결된다
    assert res.headers["location"] == f"{FRONT}/oauth/callback"
    assert _users(db) == 1
    assert db.scalar(select(SocialAccount.user_id)) == member.id
    # 구글 토큰 요청에는 client secret 이 들어간다
    token_request = provider_api["requests"][0]
    assert b"client_secret=google-secret" in token_request.content


def test_unverified_email_never_links_existing_member(db, client, provider_api):
    """확인되지 않은 이메일로 연결하면 남의 계정에 들어갈 수 있다."""
    member = f.user(db, email="victim@example.com")
    provider_api["userinfo"] = kakao_user(email="victim@example.com", verified=False)
    assert _error(_login(client)) == "OAUTH_SIGNUP_REQUIRED"

    res = _login(client, signup=True)
    assert res.headers["location"] == f"{FRONT}/oauth/callback"
    new_user = db.scalar(select(User).where(User.id != member.id))
    assert new_user.email is None  # 이메일 없이 새 회원
    assert db.scalar(select(SocialAccount.user_id)) == new_user.id


def test_state_mismatch_and_cancel(db, client, provider_api):
    res = _login(client, signup=True, state="forged-state")
    assert _error(res) == "OAUTH_STATE_MISMATCH"
    # 쿠키 없이 콜백만 호출해도 거부
    client.cookies.clear()
    res = client.get("/api/v1/auth/oauth/kakao/callback", params={"code": "c", "state": "s"}, follow_redirects=False)
    assert _error(res) == "OAUTH_STATE_MISMATCH"

    client.get("/api/v1/auth/oauth/kakao/start", follow_redirects=False)
    state = client.cookies.get("oauth_state").split(".")[0]
    res = client.get(
        "/api/v1/auth/oauth/kakao/callback",
        params={"error": "access_denied", "state": state},
        follow_redirects=False,
    )
    assert _error(res) == "OAUTH_CANCELLED"
    assert _users(db) == 0 and provider_api["requests"] == []


def test_provider_error(db, client, provider_api):
    provider_api["token_status"] = 400
    assert _error(_login(client, signup=True)) == "OAUTH_PROVIDER_ERROR"
    assert _users(db) == 0


def test_nickname_fallback_and_truncate(db, client, provider_api):
    provider_api["userinfo"] = {"id": 7, "kakao_account": {}}  # 닉네임·이메일 제공에 모두 동의하지 않음
    _login(client, signup=True)
    assert db.scalar(select(User.nickname)) == "페어픽 회원"
