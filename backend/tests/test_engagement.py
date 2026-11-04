"""비밀번호 재설정, 관람 노트·후기·좋아요, 태그 투표, 캘린더, 수집 실패 알림."""

import re
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import CrawlRun, CrawlSource, FairTag, PasswordResetToken
from app.models.mixins import utcnow
from app.services import mail
from app.services.crawl import alert_if_repeated_failures
from tests import factories as f


@pytest.fixture(autouse=True)
def clear_outbox():
    mail.outbox.clear()


def _reset_token():
    body = mail.outbox[-1].get_body(("plain",)).get_content()
    return re.search(r"token=([A-Za-z0-9_\-]+)", body).group(1)


def test_password_reset_flow(db, client):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "me@example.com", "password": "oldpassword", "nickname": "나", "is_over_14": True},
    )
    client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": "oldpassword"})

    same = {"message": "가입된 이메일이면 재설정 링크를 보냈어요. 메일함을 확인해 주세요"}
    assert client.post("/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"}).json() == same
    assert mail.outbox == []  # 없는 이메일에는 보내지 않지만 응답은 같다
    assert client.post("/api/v1/auth/password-reset/request", json={"email": "me@example.com"}).json() == same
    token = _reset_token()

    res = client.post("/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": "newpassword"})
    assert res.status_code == 200
    assert (
        client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": "newpassword"}).status_code
        == 200
    )
    # 1회용
    again = client.post("/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": "another123"})
    assert again.status_code == 400 and again.json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_password_reset_expires_after_30_minutes(db, client):
    user = f.user(db, email="late@example.com")
    client.post("/api/v1/auth/password-reset/request", json={"email": "late@example.com"})
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    row.expires_at = utcnow() - timedelta(minutes=1)  # DB 는 UTC
    db.flush()
    res = client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": _reset_token(), "new_password": "newpassword"}
    )
    assert res.status_code == 400


@pytest.fixture
def fair(db):
    return f.fair(db, category=f.category(db), venue=f.venue(db), start=date(2026, 11, 1), end=date(2026, 11, 3))


def test_visit_notes_reviews_and_likes(db, client, fair):
    alice, bob = f.user(db), f.user(db)
    ha, hb = f.auth_header(alice), f.auth_header(bob)

    res = client.post(
        f"/api/v1/fairs/{fair.id}/visits",
        json={"visited_on": "2026-11-02", "rating": 5, "memo": "좋았어요", "is_public": True},
        headers=ha,
    )
    assert res.status_code == 201
    visit_id = res.json()["id"]
    dup = client.post(f"/api/v1/fairs/{fair.id}/visits", json={}, headers=ha)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "VISIT_EXISTS"
    client.post(f"/api/v1/fairs/{fair.id}/visits", json={"rating": 3, "memo": "비공개 메모"}, headers=hb)

    reviews = client.get(f"/api/v1/fairs/{fair.id}/reviews").json()
    assert reviews["total"] == 1 and reviews["rating_avg"] == 5.0  # 비공개 노트는 후기에 안 보인다
    assert reviews["items"][0]["memo"] == "좋았어요"

    for _ in range(2):
        assert client.put(f"/api/v1/visits/{visit_id}/like", headers=hb).json() == {
            "visit_id": visit_id,
            "liked": True,
            "like_count": 1,
        }
    assert client.get(f"/api/v1/fairs/{fair.id}/reviews", headers=hb).json()["items"][0]["liked_by_me"] is True

    # 작성자만 고치고 지울 수 있다
    assert client.patch(f"/api/v1/visits/{visit_id}", json={"memo": "남의 글"}, headers=hb).status_code == 403
    assert (
        client.patch(f"/api/v1/visits/{visit_id}", json={"is_public": False}, headers=ha).json()["is_public"] is False
    )
    assert client.get(f"/api/v1/fairs/{fair.id}/reviews").json()["total"] == 0
    assert len(client.get("/api/v1/me/visits", headers=ha).json()) == 1
    assert client.delete(f"/api/v1/visits/{visit_id}", headers=ha).status_code == 204

    bad = client.post(f"/api/v1/fairs/{fair.id}/visits", json={"rating": 6}, headers=ha)
    assert bad.status_code == 422


def test_tag_votes_apply_at_three(db, client, fair):
    date_tag = f.tag(db, "date", "데이트 추천")
    date_tag.is_votable = True
    fact = f.tag(db, "tasting", "시식·시음 있음")  # 투표 불가
    db.flush()
    users = [f.user(db) for _ in range(3)]

    for i, u in enumerate(users, start=1):
        rows = client.put(f"/api/v1/fairs/{fair.id}/tag-votes/{date_tag.id}", headers=f.auth_header(u)).json()
        row = next(r for r in rows if r["slug"] == "date")
        assert row["vote_count"] == i and row["voted"] is True
        assert row["applied"] is (i >= 3)

    assert db.scalar(select(FairTag.source).where(FairTag.fair_id == fair.id, FairTag.tag_id == date_tag.id)) == "vote"
    # 표가 기준 아래로 내려가면 투표로 붙은 태그는 뗀다
    client.delete(f"/api/v1/fairs/{fair.id}/tag-votes/{date_tag.id}", headers=f.auth_header(users[0]))
    assert db.scalar(select(FairTag).where(FairTag.fair_id == fair.id, FairTag.tag_id == date_tag.id)) is None

    res = client.put(f"/api/v1/fairs/{fair.id}/tag-votes/{fact.id}", headers=f.auth_header(users[0]))
    assert res.status_code == 422 and res.json()["error"]["code"] == "TAG_NOT_VOTABLE"


def test_calendar_month(db, client):
    cat, ven = f.category(db), f.venue(db)
    f.fair(db, category=cat, venue=ven, title="10월말~11월초", start=date(2026, 10, 30), end=date(2026, 11, 2))
    f.fair(db, category=cat, venue=ven, title="12월", start=date(2026, 12, 1), end=date(2026, 12, 2))
    f.fair(db, category=cat, venue=ven, title="숨김", start=date(2026, 11, 5), end=date(2026, 11, 6), status="hidden")
    res = client.get("/api/v1/fairs/calendar?month=2026-11")
    assert res.status_code == 200
    assert [i["title"] for i in res.json()] == ["10월말~11월초"]
    assert client.get("/api/v1/fairs/calendar?month=2026-13").status_code == 422


def test_crawl_alert_after_two_failures(db):
    f.admin(db)
    src = CrawlSource(venue_id=f.venue(db).id, parser_key="x", list_url="https://x")
    db.add(src)
    db.flush()
    db.add(CrawlRun(source_id=src.id, status="failed", error_message="e1", started_at=datetime(2026, 11, 3)))
    db.flush()
    assert alert_if_repeated_failures(db, src) is False  # 한 번 실패로는 보내지 않는다
    db.add(CrawlRun(source_id=src.id, status="failed", error_message="e2", started_at=datetime(2026, 11, 4)))
    db.flush()
    assert alert_if_repeated_failures(db, src) is True
    assert "수집 연속 실패" in mail.outbox[-1]["Subject"]


def test_ics_export(db, client):
    fair = f.fair(
        db,
        category=f.category(db),
        venue=f.venue(db, name="코엑스"),
        title="서울카페쇼, 2026; 커피",
        hall="A홀",
        start=date(2026, 11, 11),
        end=date(2026, 11, 14),
    )
    res = client.get(f"/api/v1/fairs/{fair.id}/calendar.ics")
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/calendar")
    body = res.text
    assert "DTSTART;VALUE=DATE:20261111\r\n" in body
    assert "DTEND;VALUE=DATE:20261115\r\n" in body  # 종일 일정은 다음 날로 끝난다
    assert "SUMMARY:서울카페쇼\, 2026\; 커피\r\n" in body
    assert "LOCATION:코엑스 A홀\r\n" in body


def test_admin_excel_export(db, client):
    from io import BytesIO

    from openpyxl import load_workbook

    fair = f.fair(db, category=f.category(db), venue=f.venue(db), title="엑셀 테스트")
    f.bookmark(db, f.user(db), fair)
    res = client.get("/api/v1/admin/export/fairs.xlsx", headers=f.auth_header(f.admin(db)))
    assert res.status_code == 200
    ws = load_workbook(BytesIO(res.content)).active
    assert ws["C1"].value == "박람회명" and ws["C2"].value == "엑셀 테스트"
    assert ws["P2"].value == 1  # 북마크 수
    assert client.get("/api/v1/admin/export/fairs.xlsx", headers=f.auth_header(f.user(db))).status_code == 403
