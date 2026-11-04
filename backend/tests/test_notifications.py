"""알림 선별·발송 (레퍼런스 13장: 같은 날 두 번 실행해도 알림 1건)."""

from datetime import date, datetime

import pytest
from sqlalchemy import func, select

from app.models import Notification, NotificationSetting
from app.services import mail
from app.services.notifications import ensure_settings, select_targets, send_pending
from tests import factories as f
from tests.conftest import TODAY  # 2026-11-04

NOW = datetime(2026, 11, 4, 0, 0)  # = 09:00 KST
BASE = "http://localhost:5173"


@pytest.fixture(autouse=True)
def clear_outbox():
    mail.outbox.clear()


@pytest.fixture
def setup(db):
    cat, ven = f.category(db), f.venue(db, name="코엑스")
    user = f.user(db, email="fan@example.com")
    ensure_settings(db, user.id)
    deadline = f.fair(  # 사전등록이 내일(11.05) 23:59 KST 마감
        db,
        category=cat,
        venue=ven,
        title="마감 임박 페어",
        start=date(2026, 11, 20),
        end=date(2026, 11, 22),
        prereg_end_at=datetime(2026, 11, 5, 14, 59),
        prereg_url="https://example.com/prereg",
    )
    opening = f.fair(
        db, category=cat, venue=ven, title="개막 3일 전 페어", start=date(2026, 11, 7), end=date(2026, 11, 9)
    )
    other = f.fair(
        db, category=cat, venue=ven, title="북마크 안 한 페어", start=date(2026, 11, 7), end=date(2026, 11, 9)
    )
    for fair in (deadline, opening):
        f.bookmark(db, user, fair)
    return {"user": user, "deadline": deadline, "opening": opening, "other": other}


def _count(db):
    return db.scalar(select(func.count()).select_from(Notification))


def test_selects_once_even_if_run_twice(db, setup):
    first = select_targets(db, today=TODAY, now=NOW)
    assert first == {"prereg_deadline": 1, "opening_soon": 1, "fair_updated": 0}
    second = select_targets(db, today=TODAY, now=NOW)
    assert second == {"prereg_deadline": 0, "opening_soon": 0, "fair_updated": 0}
    assert _count(db) == 2


def test_send_marks_sent_with_unsubscribe_link(db, setup):
    select_targets(db, today=TODAY, now=NOW)
    result = send_pending(db, now=NOW, base_url=BASE)
    assert result["sent"] == 2
    subjects = sorted(m["Subject"] for m in mail.outbox)
    assert subjects[0].startswith("[페어픽] 3일 뒤 개막해요")
    assert subjects[1] == "[페어픽] 내일 사전등록이 마감돼요: 마감 임박 페어"
    msg = next(m for m in mail.outbox if "마감" in m["Subject"])
    assert "List-Unsubscribe" in msg
    body = msg.get_body(("plain",)).get_content()
    assert "11.5 23:59" in body and "https://example.com/prereg" in body
    assert send_pending(db, now=NOW, base_url=BASE)["sent"] == 0  # 이미 보낸 건 다시 안 보낸다


def test_disabled_type_is_not_selected(db, setup):
    s = db.get(NotificationSetting, setup["user"].id)
    s.prereg_deadline = False
    db.flush()
    assert select_targets(db, today=TODAY, now=NOW)["prereg_deadline"] == 0


def test_turned_off_before_send_is_skipped(db, setup):
    select_targets(db, today=TODAY, now=NOW)
    db.get(NotificationSetting, setup["user"].id).email_enabled = False
    db.flush()
    assert send_pending(db, now=NOW, base_url=BASE)["skipped"] == 2
    assert mail.outbox == []


def test_member_without_email_is_skipped(db, setup):
    """소셜 로그인으로 가입하고 이메일 제공에 동의하지 않은 회원에게는 보낼 곳이 없다."""
    select_targets(db, today=TODAY, now=NOW)
    setup["user"].email = None
    db.flush()
    assert send_pending(db, now=NOW, base_url=BASE)["skipped"] == 2
    assert mail.outbox == []


def test_extended_deadline_sends_again(db, setup):
    select_targets(db, today=TODAY, now=NOW)
    setup["deadline"].prereg_end_at = datetime(2026, 11, 6, 14, 59)  # 하루 연장
    db.flush()
    # 연장된 마감 전날(11.05)에 다시 선별하면 ref_key(마감 일시)가 달라 한 번 더 나간다
    assert select_targets(db, today=date(2026, 11, 5), now=NOW)["prereg_deadline"] == 1


def test_failed_send_retries_then_fails(db, setup, monkeypatch):
    select_targets(db, today=TODAY, now=NOW)

    def boom(_):
        raise ConnectionError("smtp down")

    monkeypatch.setattr(mail, "send", boom)
    for _ in range(3):
        send_pending(db, now=NOW, base_url=BASE)
    statuses = set(db.scalars(select(Notification.status)))
    assert statuses == {"failed"}


def test_fair_updated_from_admin_change(db, client, setup):
    admin_h = f.auth_header(f.admin(db))
    fair = setup["opening"]
    res = client.patch(f"/api/v1/admin/fairs/{fair.id}", json={"end_date": "2026-11-10"}, headers=admin_h)
    assert res.status_code == 200
    # 변경 다음 날 오전 9시 선별
    from app.models import FairChangeLog

    log = db.scalar(select(FairChangeLog).where(FairChangeLog.fair_id == fair.id))
    assert (log.field_name, log.old_value, log.new_value) == ("end_date", "2026-11-09", "2026-11-10")
    log.created_at = datetime(2026, 11, 3, 5, 0)  # 어제(KST) 변경으로 맞춘다
    db.flush()
    assert select_targets(db, today=TODAY, now=NOW)["fair_updated"] == 1


def test_settings_api_and_unsubscribe(db, client, setup):
    h = f.auth_header(setup["user"])
    assert client.get("/api/v1/me/notification-settings", headers=h).json()["email_enabled"] is True
    res = client.put(
        "/api/v1/me/notification-settings",
        json={"email_enabled": True, "prereg_deadline": False, "opening_soon": True, "fair_updated": True},
        headers=h,
    )
    assert res.json()["prereg_deadline"] is False

    token = db.get(NotificationSetting, setup["user"].id).unsubscribe_token
    res = client.post("/api/v1/notifications/unsubscribe", json={"token": token})  # 로그인 없이
    assert res.status_code == 200
    assert client.get("/api/v1/me/notification-settings", headers=h).json()["email_enabled"] is False
    bad = client.post("/api/v1/notifications/unsubscribe", json={"token": "x" * 20})
    assert bad.status_code == 404


def test_signup_creates_settings(db, client):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "new@example.com", "password": "password123", "nickname": "새회원", "is_over_14": True},
    )
    assert db.scalar(select(func.count()).select_from(NotificationSetting)) == 1
