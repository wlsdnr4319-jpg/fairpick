"""인증·권한 (레퍼런스 13장: 만료 토큰 401, 일반 사용자의 관리자 API 403)."""

from datetime import UTC, datetime, timedelta

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


def test_refresh_rotates_and_detects_reuse(db, client):
    _signup_and_login(client)
    first_cookie = client.cookies.get("refresh_token")

    res = client.post("/api/v1/auth/refresh")
    assert res.status_code == 200 and res.json()["access_token"]
    second_cookie = client.cookies.get("refresh_token")
    assert second_cookie and second_cookie != first_cookie

    # 이미 폐기된 첫 번째 토큰을 다시 쓰면 탈취로 보고 모든 토큰을 폐기한다
    _use_cookie(client, first_cookie)
    assert client.post("/api/v1/auth/refresh").status_code == 401
    _use_cookie(client, second_cookie)
    res = client.post("/api/v1/auth/refresh")
    assert res.status_code == 401 and res.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


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
