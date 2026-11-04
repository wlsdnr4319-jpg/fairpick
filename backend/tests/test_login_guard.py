"""로그인 횟수 제한·재설정 메일 한도 (app/services/login_guard.py, services/auth.py)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.deps import get_now
from app.models import LoginAttempt, PasswordResetToken
from app.services import login_guard

START = datetime(2026, 11, 4, 3, 0, 0)  # UTC
PASSWORD = "password123"


@pytest.fixture
def clock(app):
    """API 가 쓰는 '지금'을 테스트가 움직일 수 있게 한다."""
    state = {"now": START}
    app.dependency_overrides[get_now] = lambda: state["now"]
    return state


def _signup(client, email="me@example.com"):
    body = {"email": email, "password": PASSWORD, "nickname": "진욱", "is_over_14": True}
    assert client.post("/api/v1/auth/signup", json=body).status_code == 201


def _login(client, email="me@example.com", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_locks_after_five_failures_even_with_right_password(db, client, clock):
    _signup(client)
    for _ in range(login_guard.MAX_FAILS_PER_EMAIL):
        assert _login(client, password="wrong-pass").status_code == 401

    res = _login(client)  # 맞는 비밀번호여도 잠금 중이면 막는다
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    assert int(res.headers["Retry-After"]) == 15 * 60
    assert "15분" in res.json()["error"]["message"]

    # 대소문자만 바꾼 이메일도 같은 계정으로 센다
    assert _login(client, email="ME@Example.com").status_code == 429

    clock["now"] = START + login_guard.WINDOW
    assert _login(client).status_code == 200


def test_success_resets_email_counter(db, client, clock):
    _signup(client)
    for _ in range(login_guard.MAX_FAILS_PER_EMAIL - 1):
        _login(client, password="wrong-pass")
    clock["now"] += timedelta(seconds=1)
    assert _login(client).status_code == 200

    clock["now"] += timedelta(seconds=1)
    for _ in range(login_guard.MAX_FAILS_PER_EMAIL - 1):
        assert _login(client, password="wrong-pass").status_code == 401
    clock["now"] += timedelta(seconds=1)
    assert _login(client).status_code == 200


def test_unknown_email_is_limited_the_same_way(db, client, clock):
    """잠금 여부로 가입 여부를 알 수 없어야 한다."""
    for _ in range(login_guard.MAX_FAILS_PER_EMAIL):
        assert _login(client, email="nobody@example.com").status_code == 401
    assert _login(client, email="nobody@example.com").status_code == 429


def test_ip_limit_across_many_emails(db, client, clock):
    _signup(client)
    for i in range(login_guard.MAX_FAILS_PER_IP):
        assert _login(client, email=f"user{i}@example.com").status_code == 401
    # 한 번도 틀린 적 없는 계정이어도 같은 IP 면 막는다
    assert _login(client).status_code == 429


def test_lock_lifts_as_old_failures_leave_window(db, client, clock):
    _signup(client)
    for _ in range(login_guard.MAX_FAILS_PER_EMAIL):
        _login(client, password="wrong-pass")
        clock["now"] += timedelta(minutes=1)
    # 실패 시각: 0,1,2,3,4분. 지금 5분 → 가장 오래된 실패(0분)가 15분에 빠진다
    res = _login(client)
    assert res.status_code == 429 and int(res.headers["Retry-After"]) == 10 * 60

    clock["now"] = START + timedelta(minutes=15)
    assert _login(client).status_code == 200


def test_attempts_are_recorded_and_purged(db, client, clock):
    _signup(client)
    _login(client, password="wrong-pass")
    _login(client)
    rows = db.scalars(select(LoginAttempt).order_by(LoginAttempt.id)).all()
    assert [(r.email, r.succeeded) for r in rows] == [("me@example.com", False), ("me@example.com", True)]

    assert login_guard.purge(db, START + timedelta(hours=23)) == 0
    assert login_guard.purge(db, START + timedelta(days=1, seconds=1)) == 2


def test_password_reset_mail_capped_per_hour(db, client, clock):
    _signup(client)
    for _ in range(5):
        res = client.post("/api/v1/auth/password-reset/request", json={"email": "me@example.com"})
        assert res.status_code == 200  # 한도를 넘어도 응답은 같다
    count = db.scalar(select(func.count()).select_from(PasswordResetToken))
    assert count == 3

    clock["now"] = START + timedelta(hours=1, seconds=1)
    client.post("/api/v1/auth/password-reset/request", json={"email": "me@example.com"})
    assert db.scalar(select(func.count()).select_from(PasswordResetToken)) == 4
