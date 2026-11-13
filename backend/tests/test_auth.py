"""인증·권한 (레퍼런스 13장: 만료 토큰 401, 일반 사용자의 관리자 API 403)."""

from datetime import UTC, datetime, timedelta

from app.core.deps import get_now
from app.core.security import create_access_token
from tests import factories as f

SIGNUP = {"email": "Me@Example.com", "password": "password123", "nickname": "진욱", "is_over_14": True}


def _use_cookie(client, token):
    client.cookies.clear()
    client.cookies.set("refresh_token", token)


def _signup_and_login(client):
    assert client.post("/api/v1/auth/signup", json=SIGNUP).status_code == 201
    return client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": "password123"})


def test_signup_validation(db, client):
    res = client.post("/api/v1/auth/signup", json={**SIGNUP, "password": "short"})
    assert res.status_code == 422 and res.json()["error"]["code"] == "VALIDATION_ERROR"
    res = client.post("/api/v1/auth/signup", json={**SIGNUP, "is_over_14": False})
    assert res.status_code == 422

    assert client.post("/api/v1/auth/signup", json=SIGNUP).status_code == 201
    res = client.post("/api/v1/auth/signup", json={**SIGNUP, "email": "ME@example.com"})
    assert res.status_code == 409 and res.json()["error"]["code"] == "EMAIL_TAKEN"


def test_login_sets_httponly_refresh_cookie(db, client):
    res = _signup_and_login(client)
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["email"] == "me@example.com"
    assert body["expires_in"] == 30 * 60
    cookie = res.headers["set-cookie"]
    assert "refresh_token=" in cookie and "HttpOnly" in cookie and "Path=/api/v1/auth" in cookie

    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200 and me.json()["nickname"] == "진욱"


def test_wrong_password(db, client):
    _signup_and_login(client)
    res = client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": "wrong-pass"})
    assert res.status_code == 401 and res.json()["error"]["code"] == "INVALID_CREDENTIALS"
    res = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-pass"})
    assert res.status_code == 401 and res.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_expired_and_invalid_access_token(db, client):
    user = f.user(db)
    old = create_access_token(user.id, user.role, now=datetime.now(UTC) - timedelta(hours=1))
    res = client.get("/api/v1/me", headers={"Authorization": f"Bearer {old}"})
    assert res.status_code == 401 and res.json()["error"]["code"] == "TOKEN_EXPIRED"

    res = client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401 and res.json()["error"]["code"] == "INVALID_TOKEN"

    res = client.get("/api/v1/me")
    assert res.status_code == 401 and res.json()["error"]["code"] == "UNAUTHORIZED"


class Clock:
    """요청마다 쓰는 '지금'을 테스트에서 옮긴다 (리프레시 재사용 유예 시간 확인용)."""

    def __init__(self, app):
        self.now = datetime(2026, 11, 13, 3, 0)
        app.dependency_overrides[get_now] = lambda: self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


def test_refresh_rotates_and_detects_reuse(db, client, app):
    clock = Clock(app)
    _signup_and_login(client)
    first_cookie = client.cookies.get("refresh_token")

    res = client.post("/api/v1/auth/refresh")
    assert res.status_code == 200 and res.json()["access_token"]
    second_cookie = client.cookies.get("refresh_token")
    assert second_cookie and second_cookie != first_cookie

    # 유예 시간(30초)이 지난 뒤 폐기된 첫 번째 토큰을 다시 쓰면 탈취로 보고 모든 토큰을 폐기한다
    clock.advance(31)
    _use_cookie(client, first_cookie)
    assert client.post("/api/v1/auth/refresh").status_code == 401
    _use_cookie(client, second_cookie)
    res = client.post("/api/v1/auth/refresh")
    assert res.status_code == 401 and res.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


def _refresh_with(client, token):
    """그 토큰으로 재발급을 요청하고 (응답, 새 토큰)을 돌려준다. 쿠키 저장소 대신 응답의 Set-Cookie 를 읽는다."""
    _use_cookie(client, token)
    res = client.post("/api/v1/auth/refresh")
    client.cookies.clear()
    return res, res.cookies.get("refresh_token")


def test_refresh_response_lost_is_tolerated_within_grace(db, client, app):
    """재발급 중 페이지를 옮겨 새 쿠키를 못 받은 브라우저가 이전 토큰을 다시 보내는 경우 (E2E 로 발견)."""
    clock = Clock(app)
    first = _signup_and_login(client).cookies.get("refresh_token")
    res, lost = _refresh_with(client, first)  # 브라우저는 이 응답(새 쿠키)을 받지 못했다고 가정
    assert res.status_code == 200

    clock.advance(5)
    res, third = _refresh_with(client, first)
    assert res.status_code == 200, res.text
    assert third not in (first, lost)

    # 받지 못한 토큰(lost)은 그때 폐기됐다. 유예 시간이 지나 그걸 쓰면 다시 탈취 의심으로 모두 폐기한다
    clock.advance(31)
    assert _refresh_with(client, lost)[0].status_code == 401
    assert _refresh_with(client, third)[0].status_code == 401


def test_refresh_grace_chain_keeps_working(db, client, app):
    """끊긴 뒤 다시 받은 토큰으로 계속 재발급할 수 있다."""
    clock = Clock(app)
    first = _signup_and_login(client).cookies.get("refresh_token")
    _refresh_with(client, first)
    clock.advance(5)
    _, third = _refresh_with(client, first)
    clock.advance(60)
    res, fourth = _refresh_with(client, third)
    assert res.status_code == 200 and fourth


def test_refresh_grace_does_not_undo_logout(db, client, app):
    """로그아웃한 뒤에는 유예 시간 안이라도 이전 토큰으로 다시 로그인되지 않는다."""
    Clock(app)
    first = _signup_and_login(client).cookies.get("refresh_token")
    _, second = _refresh_with(client, first)
    _use_cookie(client, second)
    assert client.post("/api/v1/auth/logout").status_code == 204

    assert _refresh_with(client, first)[0].status_code == 401


def test_logout_revokes_refresh_token(db, client):
    _signup_and_login(client)
    token = client.cookies.get("refresh_token")
    assert client.post("/api/v1/auth/logout").status_code == 204
    _use_cookie(client, token)
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_without_cookie(client):
    res = client.post("/api/v1/auth/refresh")
    assert res.status_code == 401 and res.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


def test_withdraw_deletes_user_and_bookmarks(db, client):
    user = f.user(db)
    fair = f.fair(db, category=f.category(db), venue=f.venue(db))
    f.bookmark(db, user, fair)
    headers = f.auth_header(user)

    assert client.delete("/api/v1/me", headers=headers).status_code == 204
    assert client.get("/api/v1/me", headers=headers).json()["error"]["code"] == "INVALID_TOKEN"
    assert client.get(f"/api/v1/fairs/{fair.id}").json()["bookmark_count"] == 0


def test_admin_api_forbidden_for_normal_user(db, client):
    res = client.get("/api/v1/admin/fairs", headers=f.auth_header(f.user(db)))
    assert res.status_code == 403 and res.json()["error"]["code"] == "ADMIN_ONLY"
    assert client.get("/api/v1/admin/fairs").status_code == 401
