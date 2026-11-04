"""웹 푸시: 구독 API, 푸시 서비스 주소 제한(SSRF), 알림 선별·발송. 실제 푸시 서비스에는 보내지 않는다."""

import json
from datetime import date, datetime

import pytest
from pywebpush import WebPushException
from requests import Response
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models import Notification, PushSubscription
from app.scripts.gen_vapid import generate
from app.services import mail, push
from app.services.notifications import ensure_settings, select_targets, send_pending
from tests import factories as f
from tests.conftest import TODAY  # 2026-11-04

NOW = datetime(2026, 11, 4, 0, 0)
BASE = "http://localhost:5173"
FCM = "https://fcm.googleapis.com/fcm/send/abc123"
KEYS = {"p256dh": "B" + "x" * 86, "auth": "a" * 22}


@pytest.fixture
def vapid(monkeypatch):
    public, private = generate()
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", public)
    monkeypatch.setattr(settings, "vapid_private_key", private)
    return public


@pytest.fixture
def sent(monkeypatch):
    """webpush 를 가짜로 바꾼다. endpoint 별로 돌려줄 HTTP 상태를 정할 수 있다."""
    calls = {"list": [], "status": {}}

    def fake_webpush(subscription_info, data, **kwargs):
        endpoint = subscription_info["endpoint"]
        calls["list"].append({"endpoint": endpoint, "data": json.loads(data), **kwargs})
        code = calls["status"].get(endpoint, 201)
        if code >= 400:
            res = Response()
            res.status_code = code
            raise WebPushException(f"HTTP {code}", response=res)
        return "ok"

    monkeypatch.setattr(push, "webpush", fake_webpush)
    mail.outbox.clear()
    return calls


def _subscribe(client, user, endpoint=FCM):
    return client.post(
        "/api/v1/me/push-subscriptions", json={"endpoint": endpoint, "keys": KEYS}, headers=f.auth_header(user)
    )


def _subs(db) -> int:
    return db.scalar(select(func.count()).select_from(PushSubscription))


def test_config(db, client, vapid, monkeypatch):
    assert client.get("/api/v1/push/config").json() == {"enabled": True, "public_key": vapid}
    monkeypatch.setattr(get_settings(), "vapid_private_key", "")
    assert client.get("/api/v1/push/config").json() == {"enabled": False, "public_key": None}
    user = f.user(db)
    assert _subscribe(client, user).status_code == 503


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fcm.googleapis.com/fcm/send/x",  # https 아님
        "https://localhost/push",
        "https://10.0.0.5/internal",
        "https://fcm.googleapis.com.evil.example/x",  # 이름만 비슷한 도메인
        "https://evilfcm.googleapis.com.attacker.io/x",
    ],
)
def test_rejects_non_push_service_endpoints(db, client, vapid, endpoint):
    res = _subscribe(client, f.user(db), endpoint)
    assert res.status_code == 422 and res.json()["error"]["code"] == "INVALID_PUSH_ENDPOINT"


def test_endpoint_allowlist():
    assert push.endpoint_allowed("https://updates.push.services.mozilla.com/wpush/v2/x")
    assert push.endpoint_allowed("https://web.push.apple.com/abc")
    assert push.endpoint_allowed("https://wns2-pn1p.notify.windows.com/w/?token=x")


def test_subscribe_update_move_and_unsubscribe(db, client, vapid):
    me, other = f.user(db), f.user(db)
    assert client.post("/api/v1/me/push-subscriptions", json={"endpoint": FCM, "keys": KEYS}).status_code == 401
    assert _subscribe(client, me).status_code == 201
    assert _subscribe(client, me).status_code == 201  # 같은 기기 → 갱신, 행은 하나
    assert _subs(db) == 1
    # 같은 브라우저에서 다른 계정으로 로그인해 구독하면 그 계정으로 옮긴다
    _subscribe(client, other)
    assert db.scalar(select(PushSubscription.user_id)) == other.id

    res = client.request("DELETE", "/api/v1/me/push-subscriptions", json={"endpoint": FCM}, headers=f.auth_header(me))
    assert res.status_code == 204 and _subs(db) == 1  # 남의 구독은 못 지운다
    client.request("DELETE", "/api/v1/me/push-subscriptions", json={"endpoint": FCM}, headers=f.auth_header(other))
    assert _subs(db) == 0


def test_test_push_and_gone_subscription(db, client, vapid, sent):
    user = f.user(db)
    _subscribe(client, user)
    res = client.post("/api/v1/me/push-subscriptions/test", headers=f.auth_header(user))
    assert res.status_code == 200 and res.json() == {"delivered": 1}
    call = sent["list"][0]
    assert call["data"]["title"] == "페어픽 알림 테스트"
    assert call["vapid_claims"] == {"sub": get_settings().vapid_subject}

    sent["status"][FCM] = 410  # 브라우저에서 알림을 차단함 → 구독 끝
    res = client.post("/api/v1/me/push-subscriptions/test", headers=f.auth_header(user))
    assert res.status_code == 409 and _subs(db) == 0


@pytest.fixture
def bookmarked(db):
    cat, ven = f.category(db), f.venue(db, name="코엑스")
    user = f.user(db, email="fan@example.com")
    ensure_settings(db, user.id)
    fair = f.fair(db, category=cat, venue=ven, title="개막 3일 전 페어", start=date(2026, 11, 7), end=date(2026, 11, 9))
    f.bookmark(db, user, fair)
    return user, fair


def _by_channel(db) -> dict[str, str]:
    return {n.channel: n.status for n in db.scalars(select(Notification))}


def test_push_and_email_are_selected_and_sent_separately(db, client, vapid, sent, bookmarked):
    user, fair = bookmarked
    _subscribe(client, user)
    assert select_targets(db, today=TODAY, now=NOW)["opening_soon"] == 2  # 메일 1 + 푸시 1
    assert select_targets(db, today=TODAY, now=NOW)["opening_soon"] == 0  # 다시 돌려도 중복 없음

    result = send_pending(db, now=NOW, base_url=BASE)
    assert result["sent"] == 2 and len(mail.outbox) == 1
    payload = sent["list"][0]["data"]
    assert payload == {
        "title": "3일 뒤 개막해요",
        "body": "개막 3일 전 페어 · 11.7 ~ 11.9 · 코엑스",
        "url": f"/fairs/{fair.id}",
        "tag": f"opening_soon-{fair.id}",
    }
    assert _by_channel(db) == {"email": "sent", "push": "sent"}


def test_member_without_email_gets_push_only(db, client, vapid, sent, bookmarked):
    user, _ = bookmarked
    user.email = None
    db.flush()
    _subscribe(client, user)
    select_targets(db, today=TODAY, now=NOW)
    assert set(_by_channel(db)) == {"push"}


def test_no_push_rows_without_subscription_or_keys(db, client, vapid, sent, bookmarked, monkeypatch):
    select_targets(db, today=TODAY, now=NOW)
    assert set(_by_channel(db)) == {"email"}  # 구독한 기기가 없다

    user, _ = bookmarked
    _subscribe(client, user)
    monkeypatch.setattr(get_settings(), "vapid_private_key", "")  # 푸시를 끈 서버
    select_targets(db, today=TODAY, now=NOW)
    assert set(_by_channel(db)) == {"email"}


def test_push_transient_error_retries_and_gone_is_skipped(db, client, vapid, sent, bookmarked):
    user, _ = bookmarked
    db.get(type(user), user.id).email = None  # 메일 행은 만들지 않는다
    db.flush()
    _subscribe(client, user)
    select_targets(db, today=TODAY, now=NOW)

    sent["status"][FCM] = 503  # 푸시 서비스 일시 오류
    assert send_pending(db, now=NOW, base_url=BASE)["retry"] == 1
    n = db.scalar(select(Notification))
    assert (n.status, n.attempts) == ("pending", 1)

    sent["status"][FCM] = 404  # 구독이 끝남
    assert send_pending(db, now=NOW, base_url=BASE)["skipped"] == 1
    assert db.scalar(select(Notification.status)) == "skipped" and _subs(db) == 0
