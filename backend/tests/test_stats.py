"""통계 리포트 API (F-19). 초안은 빼고 공개·숨김은 센다."""

from datetime import date

from tests import factories as f


def test_stats(db, client):
    food, culture = f.category(db, "food", "식음료"), f.category(db, "culture", "문화·예술")
    coex, kintex = f.venue(db, name="코엑스"), f.venue(db, name="킨텍스", region="경기")
    f.fair(db, category=food, venue=coex, start=date(2026, 11, 11), end=date(2026, 11, 14), price_prereg=0)
    f.fair(db, category=food, venue=kintex, start=date(2026, 11, 20), end=date(2026, 11, 21), status="hidden")
    f.fair(db, category=culture, venue=coex, start=date(2026, 12, 1), end=date(2026, 12, 1))
    f.fair(db, category=culture, venue=coex, start=date(2026, 12, 5), end=date(2026, 12, 6), status="draft")

    over = client.get("/api/v1/stats/overview").json()
    assert over == {"total": 3, "free_ratio": 0.333, "avg_days": 2.3}  # (4 + 2 + 1) / 3

    months = {m["month"]: m for m in client.get("/api/v1/stats/monthly?year=2026").json()}
    assert len(months) == 12
    assert months["2026-11"]["total"] == 2 and months["2026-11"]["by_category"] == {"food": 2}
    assert months["2026-12"]["by_category"] == {"culture": 1}
    assert months["2026-01"]["total"] == 0

    cats = {c["code"]: c for c in client.get("/api/v1/stats/categories").json()}
    assert cats["food"] == {"code": "food", "name": "식음료", "count": 2, "avg_days": 3.0, "free_ratio": 0.5}
    assert cats["culture"]["count"] == 1

    venues = client.get("/api/v1/stats/venues").json()
    assert venues[0] == {"venue": "코엑스", "region": "서울", "count": 2, "top_category": venues[0]["top_category"]}
    assert {v["venue"] for v in venues} == {"코엑스", "킨텍스"}
