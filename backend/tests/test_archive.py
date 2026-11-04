"""지난 행사 기록 (services/archive.py, GET /stats/history, scripts/backfill_archive.py)."""

from datetime import date, datetime

import pytest
from sqlalchemy import func, select

from app.crawlers.base import RawFair
from app.crawlers.registry import get_parser
from app.models import FairArchive
from app.services import archive
from tests import factories as f

NOW = datetime(2026, 11, 4, 3, 0)


@pytest.mark.parametrize(
    ("title", "theme"),
    [
        ("2026 코베 베이비페어", "베이비·육아"),
        ("컬러풀대구 웨딩박람회 in 엑스코", "웨딩"),
        ("웨딩&베이비 페어", "베이비·육아"),  # 위에 있는 주제가 먼저
        ("궁디팡팡 캣페스타", "반려동물"),
        ("2026 대구국제커피&카페페스타", "식음료"),
        ("2026 대구 캠페어 (캠핑&레저차량박람회)", "캠핑·레저"),
        ("제 24회 제일창업박람회 in 대구", "취업·창업"),
        ("2026 서울건축박람회 (추계)", "건축·인테리어"),
        ("코믹월드 339 일산", "문화·취미"),
        ("스마트팜 코리아", "기타"),  # '아트' 를 키워드로 쓰면 '스마트' 가 문화로 잘못 분류된다
        ("2026 대구국제기계산업대전", "기타"),
        ("국제 기술 박람회", "기타"),  # '술' 은 '기술' 에 걸린다
    ],
)
def test_theme_of(title, theme):
    assert archive.theme_of(title) == theme


def _raw(external_id, title="웨딩박람회", period="2019-05-18 ~ 2019-05-19"):
    return RawFair(external_id=external_id, title=title, period_text=period, venue_text="엑스코", detail_url="u")


def _rows(db) -> int:
    return db.scalar(select(func.count()).select_from(FairArchive))


def test_upsert_dedupes_and_is_idempotent(db):
    venue = f.venue(db, name="엑스코", region="대구")
    items = [_raw("a"), _raw("a"), _raw("b", period="날짜 미정")]  # 원본 표의 중복 줄, 못 읽는 기간
    assert archive.upsert(db, source="exco", venue_id=venue.id, items=items, now=NOW) == {"saved": 1, "skipped": 1}
    archive.upsert(db, source="exco", venue_id=venue.id, items=[_raw("a", title="웨딩박람회 (변경)")], now=NOW)
    assert _rows(db) == 1
    row = db.scalar(select(FairArchive))
    assert (row.title, row.start_date, row.theme) == ("웨딩박람회 (변경)", date(2019, 5, 18), "웨딩")


def test_retheme(db):
    venue = f.venue(db)
    archive.upsert(db, source="coex", venue_id=venue.id, items=[_raw("x", title="베이비페어")], now=NOW)
    db.scalar(select(FairArchive)).theme = "기타"
    db.flush()
    assert archive.retheme(db) == 1 and db.scalar(select(FairArchive.theme)) == "베이비·육아"


def test_history_stats(db, client):
    coex, exco = f.venue(db, name="코엑스"), f.venue(db, name="엑스코", region="대구")
    rows = [
        ("coex", coex, "c1", "베이비페어", "2019.03.07 - 2019.03.10"),
        ("coex", coex, "c2", "베이비페어", "2019.09.05 - 2019.09.08"),
        ("coex", coex, "c3", "펫쇼", "2021.03.12 - 2021.03.14"),
        ("exco", exco, "e1", "웨딩박람회", "2019-03-02~ 2019-03-03"),
        ("exco", exco, "e2", "기계산업대전", "2021-11-17~ 2021-11-20"),
        ("exco", exco, "e3", "베이비페어", "2018-12-27~ 2019-01-02"),  # 범위 밖(개막 2018)
    ]
    for source, venue, ext, title, period in rows:
        archive.upsert(db, source=source, venue_id=venue.id, items=[_raw(ext, title, period)], now=NOW)

    data = client.get("/api/v1/stats/history", params={"from_year": 2019, "to_year": 2021}).json()
    assert data["total"] == 5 and data["venues"] == ["코엑스", "엑스코"]
    assert [(y["year"], y["total"]) for y in data["by_year"]] == [(2019, 3), (2020, 0), (2021, 2)]  # 없는 해도 0 으로
    assert data["by_year"][0]["by_venue"] == {"코엑스": 2, "엑스코": 1}
    themes = {t["theme"]: t for t in data["themes"]}
    assert themes["베이비·육아"]["by_month"][2] == 1 and themes["베이비·육아"]["by_month"][8] == 1
    assert themes["베이비·육아"]["peak_months"] == [3, 9]  # 같은 수면 모두
    assert themes["캠핑·레저"]["peak_months"] == []  # 0건
    assert data["other_total"] == 1
    assert "기타" not in themes


def test_setec_fetch_period_sends_date_range():
    calls = []

    class Client:
        def get(self, url, params=None):
            calls.append(params)
            return ""

    get_parser("setec")(Client()).fetch_period(date(2023, 5, 1), date(2023, 5, 31))
    assert calls == [{"searchSDate": "2023-05-01", "searchEDate": "2023-05-31", "pageIndex": 1}]
