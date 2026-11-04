"""GET /fairs 필터·검색·정렬 (레퍼런스 13장: 필터 조합). 테스트의 오늘 = 2026-11-04(수)."""

from datetime import date, datetime

import pytest

from app.services.fair_query import month_of, weekend_of
from tests import factories as f


@pytest.fixture
def data(db):
    food = f.category(db, "food", "식음료")
    culture = f.category(db, "culture", "문화·예술")
    seoul = f.venue(db, name="코엑스", region="서울")
    busan = f.venue(db, name="벡스코", region="부산")
    date_tag = f.tag(db, "date", "데이트 추천")
    tasting = f.tag(db, "tasting", "시식·시음 있음")
    fairs = {
        # 이번 주말(11.7~11.8)에 걸친 행사
        "weekend": f.fair(
            db,
            category=food,
            venue=seoul,
            title="커피 위크엔드",
            start=date(2026, 11, 6),
            end=date(2026, 11, 8),
            summary="원두 시음",
            price_onsite=0,
            public_access="public",
            tags=[date_tag, tasting],
        ),
        "ongoing": f.fair(
            db,
            category=culture,
            venue=busan,
            title="부산 아트페어",
            start=date(2026, 11, 1),
            end=date(2026, 11, 5),
            price_prereg=0,
            public_access="partial",
            tags=[date_tag],
        ),
        "december": f.fair(
            db,
            category=food,
            venue=busan,
            title="와인 페스티벌",
            start=date(2026, 12, 10),
            end=date(2026, 12, 12),
            price_onsite=15000,
            public_access="trade_only",
            tags=[tasting],
            prereg_end_at=datetime(2026, 12, 1, 14, 59),
        ),
        "ended": f.fair(
            db,
            category=culture,
            venue=seoul,
            title="지난 전시",
            start=date(2026, 10, 1),
            end=date(2026, 10, 3),
            prereg_end_at=datetime(2026, 9, 30, 14, 59),
        ),
        "soon": f.fair(
            db,
            category=food,
            venue=seoul,
            title="디저트 페어",
            start=date(2026, 11, 20),
            end=date(2026, 11, 22),
            prereg_end_at=datetime(2026, 11, 10, 14, 59),
        ),
    }
    return fairs


def titles(client, query: str, headers=None) -> list[str]:
    res = client.get(f"/api/v1/fairs?{query}", headers=headers)
    assert res.status_code == 200, res.text
    return [i["title"] for i in res.json()["items"]]


def test_weekend_and_month_helpers():
    assert weekend_of(date(2026, 11, 4)) == (date(2026, 11, 7), date(2026, 11, 8))  # 수요일
    assert weekend_of(date(2026, 11, 7)) == (date(2026, 11, 7), date(2026, 11, 8))  # 토요일
    assert weekend_of(date(2026, 11, 8)) == (date(2026, 11, 7), date(2026, 11, 8))  # 일요일
    assert month_of(date(2026, 2, 10)) == (date(2026, 2, 1), date(2026, 2, 28))


def test_period_filters(data, client):
    assert titles(client, "period=this_weekend") == ["커피 위크엔드"]
    assert titles(client, "period=ongoing") == ["부산 아트페어"]
    assert titles(client, "period=upcoming") == ["커피 위크엔드", "디저트 페어", "와인 페스티벌"]
    assert set(titles(client, "period=this_month")) == {"부산 아트페어", "커피 위크엔드", "디저트 페어"}


def test_from_to_overlap(data, client):
    assert titles(client, "from=2026-11-05&to=2026-11-06") == ["부산 아트페어", "커피 위크엔드"]
    assert titles(client, "from=2026-12-01") == ["와인 페스티벌"]


@pytest.mark.parametrize(
    "query",
    ["period=this_month&from=2026-11-01", "from=2026-11-10&to=2026-11-01"],
)
def test_invalid_period(client, query):
    res = client.get(f"/api/v1/fairs?{query}")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_PERIOD"


def test_category_region_tags(data, client):
    assert titles(client, "category=culture") == ["지난 전시", "부산 아트페어"]
    assert titles(client, "region=부산") == ["부산 아트페어", "와인 페스티벌"]
    # 태그를 여러 개 고르면 '모두 포함'
    assert titles(client, "tags=date") == ["부산 아트페어", "커피 위크엔드"]
    assert titles(client, "tags=date,tasting") == ["커피 위크엔드"]
    assert titles(client, "category=food&region=부산&tags=tasting") == ["와인 페스티벌"]


def test_free_and_public_only(data, client):
    # 현장 또는 사전등록 무료. 미확인(NULL)은 무료가 아니다
    assert titles(client, "free=true") == ["부산 아트페어", "커피 위크엔드"]
    assert titles(client, "public_only=true") == ["부산 아트페어", "커피 위크엔드"]


def test_single_char_keyword_uses_like(data, client):
    # 한 글자 검색어는 ngram 토큰(2글자)보다 짧아 LIKE 로 찾는다. 전문 검색은 test_search.py
    assert titles(client, "q=와") == ["와인 페스티벌"]
    assert titles(client, "q=%25") == []  # LIKE 와일드카드는 글자 그대로 찾는다


def test_sort_prereg_deadline_excludes_past_and_null(data, client):
    # 지금(테스트 실행 시각)보다 마감이 뒤인 것만, 마감 빠른 순
    res = client.get("/api/v1/fairs?sort=prereg_deadline")
    got = [i["title"] for i in res.json()["items"]]
    assert "지난 전시" not in got
    assert "커피 위크엔드" not in got  # 사전등록 정보 없음
    assert got == sorted(got, key=lambda t: {"디저트 페어": 1, "와인 페스티벌": 2}[t])


def test_sort_popular(db, data, client):
    for _ in range(2):
        f.bookmark(db, f.user(db), data["december"])
    f.bookmark(db, f.user(db), data["ended"])
    assert titles(client, "sort=popular")[:2] == ["와인 페스티벌", "지난 전시"]


def test_refs(data, client):
    assert [c["code"] for c in client.get("/api/v1/categories").json()] == ["food", "culture"]
    assert {t["slug"] for t in client.get("/api/v1/tags").json()} == {"date", "tasting"}
    assert {v["region"] for v in client.get("/api/v1/venues").json()} == {"서울", "부산"}
