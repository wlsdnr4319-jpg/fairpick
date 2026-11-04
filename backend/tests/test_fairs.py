"""박람회 목록·상세 API (레퍼런스 13장: 비공개 박람회 404, 페이지네이션)."""

from datetime import date, datetime

from tests import factories as f
from tests.conftest import TODAY


def _setup(db):
    cat = f.category(db)
    ven = f.venue(db, name="코엑스")
    return cat, ven


def test_list_shows_only_published_in_opening_order(db, client):
    cat, ven = _setup(db)
    f.fair(db, category=cat, venue=ven, title="늦게 열림", start=date(2026, 12, 1), end=date(2026, 12, 3))
    f.fair(db, category=cat, venue=ven, title="먼저 열림", start=date(2026, 11, 10), end=date(2026, 11, 12))
    f.fair(db, category=cat, venue=ven, title="임시 저장", status="draft")
    f.fair(db, category=cat, venue=ven, title="숨김", status="hidden")

    res = client.get("/api/v1/fairs")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert [item["title"] for item in body["items"]] == ["먼저 열림", "늦게 열림"]
    assert (body["page"], body["size"]) == (1, 20)


def test_list_card_fields(db, client):
    cat, ven = _setup(db)
    date_tag = f.tag(db, "date", "데이트 추천")
    f.fair(
        db,
        category=cat,
        venue=ven,
        hall="A홀",
        start=date(2026, 11, 19),
        end=date(2026, 11, 22),
        public_access="public",
        price_onsite=20000,
        price_prereg=0,
        prereg_end_at=datetime(2026, 11, 16, 14, 59),  # UTC = 11.16 23:59 KST
        tags=[date_tag],
    )

    item = client.get("/api/v1/fairs").json()["items"][0]
    assert item["category"] == {"code": "food", "name": "식음료"}
    assert item["venue"] == {"id": ven.id, "name": "코엑스", "region": "서울", "hall": "A홀"}
    assert item["progress"] == "upcoming"
    assert item["d_day"] == 15  # 11.19 - 11.04
    assert item["price"] == {"onsite": 20000, "prereg": 0}
    assert item["prereg_end_at"] == "2026-11-16T23:59:00+09:00"
    assert item["tags"] == [{"slug": "date", "name": "데이트 추천"}]


def test_progress_is_computed_from_today(db, client):
    cat, ven = _setup(db)
    f.fair(db, category=cat, venue=ven, title="종료", start=date(2026, 10, 1), end=date(2026, 10, 3))
    f.fair(db, category=cat, venue=ven, title="진행 중", start=date(2026, 11, 1), end=TODAY)
    f.fair(db, category=cat, venue=ven, title="예정", start=date(2026, 11, 5), end=date(2026, 11, 6))

    items = {i["title"]: i for i in client.get("/api/v1/fairs").json()["items"]}
    assert items["종료"]["progress"] == "ended"
    assert items["진행 중"]["progress"] == "ongoing"  # 마지막 날 당일도 진행 중
    assert items["진행 중"]["d_day"] == -3
    assert items["예정"]["progress"] == "upcoming"
    assert items["예정"]["d_day"] == 1


def test_pagination(db, client):
    cat, ven = _setup(db)
    for day in range(1, 6):
        f.fair(db, category=cat, venue=ven, title=f"F{day}", start=date(2026, 12, day), end=date(2026, 12, day))

    body = client.get("/api/v1/fairs?page=2&size=2").json()
    assert body["total"] == 5
    assert [i["title"] for i in body["items"]] == ["F3", "F4"]

    assert client.get("/api/v1/fairs?page=9&size=2").json()["items"] == []


def test_size_is_limited_to_50(client):
    res = client.get("/api/v1/fairs?size=51")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_detail(db, client):
    cat, ven = _setup(db)
    fair = f.fair(
        db,
        category=cat,
        venue=ven,
        title="제25회 서울카페쇼",
        start=date(2026, 11, 11),
        end=date(2026, 11, 14),
        public_access="partial",
        access_note="일반인은 13~14일 퍼블릭데이만",
        hours_note="14일은 16시 종료",
        verified_at=datetime(2026, 11, 1, 5, 0),  # UTC = 14:00 KST
        summary="커피 업계 최대 행사",
    )
    for _ in range(2):
        f.bookmark(db, f.user(db), fair)

    res = client.get(f"/api/v1/fairs/{fair.id}")
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "제25회 서울카페쇼"
    assert body["public_access"] == "partial"
    assert body["access_note"] == "일반인은 13~14일 퍼블릭데이만"
    assert body["hours"] == {"open": None, "close": None, "note": "14일은 16시 종료"}
    assert body["prereg"] == {"start_at": None, "end_at": None, "url": None}
    assert body["verified_at"] == "2026-11-01T14:00:00+09:00"
    assert body["bookmark_count"] == 2
    assert body["is_bookmarked"] is False


def test_detail_unpublished_or_missing_is_not_found(db, client):
    cat, ven = _setup(db)
    hidden = f.fair(db, category=cat, venue=ven, status="hidden")

    for fair_id in (hidden.id, 999999):
        res = client.get(f"/api/v1/fairs/{fair_id}")
        assert res.status_code == 404
        assert res.json() == {"error": {"code": "FAIR_NOT_FOUND", "message": "박람회를 찾을 수 없어요"}}


def test_detail_rejects_non_numeric_id(client):
    assert client.get("/api/v1/fairs/abc").status_code == 422
