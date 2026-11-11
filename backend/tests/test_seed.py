"""시드 스크립트는 여러 번 실행해도 결과가 같아야 한다 (멱등성)."""

from sqlalchemy import func, select

from app.models import Category, Fair, FairTag, Tag, Venue, VenueAlias
from app.scripts import seed
from app.scripts.seed_data import FAIRS


def _counts(db):
    return {
        m.__name__: db.scalar(select(func.count()).select_from(m))
        for m in (Category, Tag, Venue, VenueAlias, Fair, FairTag)
    }


def test_seed_is_idempotent(db):
    first = seed.run(db)
    after_first = _counts(db)
    second = seed.run(db)
    after_second = _counts(db)

    assert first["fairs_created"] == len(FAIRS) == 30
    assert second == {**first, "fairs_created": 0, "fairs_updated": 30}
    assert after_first == after_second
    assert after_first["Category"] == 7
    assert after_first["Tag"] == 7
    assert after_first["Venue"] == 8


# 시·도별 대략의 범위 (위도, 경도). 좌표를 잘못 옮겨 적으면(위·경도 뒤바뀜, 다른 도시) 걸린다
REGION_BOUNDS = {
    "서울": ((37.41, 37.72), (126.76, 127.19)),
    "경기": ((36.89, 38.30), (126.37, 127.86)),
    "부산": ((34.87, 35.40), (128.76, 129.32)),
    "대구": ((35.60, 36.03), (128.35, 128.78)),
}


def test_seeded_venues_have_location(db):
    seed.run(db)
    for v in db.scalars(select(Venue)):
        (lat_lo, lat_hi), (lng_lo, lng_hi) = REGION_BOUNDS[v.region]
        assert v.address and v.address.startswith(v.region), v.name
        assert lat_lo < v.latitude < lat_hi and lng_lo < v.longitude < lng_hi, v.name


def test_seeded_fairs_are_listed(db, client):
    seed.run(db)
    body = client.get("/api/v1/fairs?size=50").json()
    assert body["total"] == 30

    cafe_show = next(i for i in body["items"] if i["title"] == "제25회 서울카페쇼")
    detail = client.get(f"/api/v1/fairs/{cafe_show['id']}").json()
    assert detail["public_access"] == "partial"
    assert detail["access_note"].startswith("일반인은 13~14일")
    assert detail["verified_at"] == "2026-11-04T14:00:00+09:00"
    assert {t["slug"] for t in detail["tags"]} == {"tasting", "date", "shopping"}
