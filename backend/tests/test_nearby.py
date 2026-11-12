"""'내 주변 박람회': GET /fairs?lat=&lng=&sort=distance&radius_km= (테스트의 오늘 = 2026-11-04)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.geo import distance_km, distance_m_sql
from app.models import Venue
from tests import factories as f

GANGNAM = (37.4979, 127.0276)  # 강남역 (사용자 위치 예시)


def _venue(db, name, region, lat=None, lng=None):
    v = f.venue(db, name=name, region=region)
    if lat is not None:
        v.latitude, v.longitude = Decimal(str(lat)), Decimal(str(lng))
        db.flush()
    return v


@pytest.fixture
def fairs(db):
    food = f.category(db, "food", "식음료")
    coex = _venue(db, "코엑스", "서울", 37.511873, 127.059111)
    kintex = _venue(db, "킨텍스", "경기", 37.669158, 126.745596)
    bexco = _venue(db, "벡스코", "부산", 35.168842, 129.136342)
    nowhere = _venue(db, "좌표 없는 전시장", "서울")
    # 개막순과 거리순이 다르게 나오도록 먼 곳일수록 먼저 연다
    return {
        "bexco": f.fair(
            db, category=food, venue=bexco, title="부산 행사", start=date(2026, 11, 10), end=date(2026, 11, 12)
        ),
        "nowhere": f.fair(
            db, category=food, venue=nowhere, title="좌표 없음", start=date(2026, 11, 11), end=date(2026, 11, 12)
        ),
        "kintex": f.fair(
            db, category=food, venue=kintex, title="일산 행사", start=date(2026, 11, 13), end=date(2026, 11, 15)
        ),
        "coex": f.fair(
            db, category=food, venue=coex, title="강남 행사", start=date(2026, 11, 20), end=date(2026, 11, 22)
        ),
        # 가장 가깝지만 이미 끝난 행사 (오늘 11-04)
        "coex_ended": f.fair(
            db, category=food, venue=coex, title="강남 지난 행사", start=date(2026, 10, 1), end=date(2026, 10, 3)
        ),
        "coex_early": f.fair(
            db, category=food, venue=coex, title="강남 먼저", start=date(2026, 11, 14), end=date(2026, 11, 15)
        ),
    }


def _get(client, **params):
    return client.get("/api/v1/fairs", params=params)


def test_sort_by_distance_puts_unknown_location_last(client, fairs):
    body = _get(client, lat=GANGNAM[0], lng=GANGNAM[1], sort="distance").json()
    # 같은 전시장이면 개막순, 좌표 없는 전시장 다음에 끝난 행사
    assert [i["title"] for i in body["items"]] == [
        "강남 먼저",
        "강남 행사",
        "일산 행사",
        "부산 행사",
        "좌표 없음",
        "강남 지난 행사",
    ]
    dist = [i["distance_km"] for i in body["items"]]
    assert 2.5 < dist[0] < 4 and dist[0] == dist[1]
    assert 25 < dist[2] < 40
    assert 300 < dist[3] < 350
    assert dist[4] is None and dist[5] == dist[0]


def test_radius_filter_excludes_far_and_unknown(client, fairs):
    body = _get(client, lat=GANGNAM[0], lng=GANGNAM[1], radius_km=50, sort="distance").json()
    assert body["total"] == 4
    assert {i["title"] for i in body["items"]} == {"강남 먼저", "강남 행사", "일산 행사", "강남 지난 행사"}


def test_location_with_default_sort_only_adds_distance(client, fairs):
    body = _get(client, lat=GANGNAM[0], lng=GANGNAM[1]).json()
    assert [i["title"] for i in body["items"]][:2] == ["강남 지난 행사", "부산 행사"]  # 개막순 그대로
    assert body["items"][1]["distance_km"] > 300


def test_without_location_distance_is_null(client, fairs):
    items = _get(client).json()["items"]
    assert all(i["distance_km"] is None for i in items)


@pytest.mark.parametrize(
    "params",
    [
        {"sort": "distance"},
        {"radius_km": 10},
        {"lat": 37.5},  # 경도 없이 위도만
        {"lng": 127.0, "sort": "distance"},
    ],
)
def test_location_required(client, fairs, params):
    res = _get(client, **params)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "LOCATION_REQUIRED"


@pytest.mark.parametrize(
    "params", [{"lat": 91, "lng": 127}, {"lat": 37, "lng": 181}, {"lat": 37, "lng": 127, "radius_km": 0}]
)
def test_location_out_of_range(client, params):
    assert _get(client, **params).status_code == 422


def test_python_distance_matches_mysql(db, fairs):
    """카드의 거리(파이썬)와 정렬·반경(MySQL)이 같은 값을 쓰는지."""
    rows = db.execute(
        select(Venue.latitude, Venue.longitude, distance_m_sql(Venue.latitude, Venue.longitude, *GANGNAM)).where(
            Venue.latitude.is_not(None)
        )
    ).all()
    assert len(rows) == 3
    for lat, lng, meters in rows:
        assert distance_km(*GANGNAM, float(lat), float(lng)) == pytest.approx(meters / 1000, abs=0.001)


def test_distance_km_basics():
    assert distance_km(*GANGNAM, *GANGNAM) == 0
    a, b = (37.511873, 127.059111), (35.168842, 129.136342)
    assert distance_km(*a, *b) == pytest.approx(distance_km(*b, *a))
