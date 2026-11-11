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
        # 새 주제
        ("2025학년도 수시 대학입학정보박람회", "교육·유학"),
        ("2024 서울머니쇼", "재테크·부동산"),
        ("서울네일엑스포 SINAIL 2024", "뷰티·건강"),
        ("2025 올댓트래블", "여행"),
        ("설맞이 명절 선물전", "쇼핑·생활"),
        ("2026 대구국제기계산업대전", "산업·학술"),
        # 박람회가 아닌 것
        ("힐스테이트 초월역 2차 입주박람회", "입주박람회"),
        ("하남호반써밋 에듀파크 입주 박람회", "입주박람회"),  # '에듀'(교육)보다 먼저
        ("제22대 국회의원선거 개표", "박람회 아님"),
        ("롯데면세점 코엑스점 3월 전관행사", "박람회 아님"),
        # 순서
        ("대한미용성형레이저의학회 미용의료기기 박람회 및 춘계학술대회", "산업·학술"),  # 학술대회 > 미용
        ("대한치과교정학회 정기총회 및 국제학술대회", "산업·학술"),  # 학술대회 > 정기총회
        ("2019 서울국제화장품·미용산업박람회, 국제건강산업박람회", "뷰티·건강"),  # 일반인 주제 > '산업'
        ("제11회 외국인유학생 채용박람회", "취업·창업"),  # 채용 > 유학
        ("제1회 농식품 테크 스타트업 창업박람회", "취업·창업"),  # 창업 > 식품
        # 다른 낱말 속 짧은 말
        ("스마트팜 코리아", "산업·학술"),  # '아트' 를 키워드로 쓰면 '스마트' 가 문화로 잘못 분류된다
        ("국제 기술 박람회", "산업·학술"),  # '술' 을 쓰면 식음료로 간다
        ("한국건축산업대전", "건축·인테리어"),  # '축산' 을 쓰면 '건축산업' 이 식음료로 간다
        ("2023 인터내셔널 뷰티 아트페어", "뷰티·건강"),  # '티아트' 를 쓰면 '뷰티아트' 가 식음료로 간다
        ("(사) 한국민화협회 회원전", "기타"),  # '원전' 을 쓰면 '회원전' 이 산업으로 간다
        ("2019 코리아 프리미어 도그쇼", "반려동물"),  # '프리미어'(호텔 이름)를 쓰면 박람회 아님으로 간다
        ("2025 드론 · 도심항공모빌리티 박람회", "산업·학술"),  # '공모' 를 쓰면 '항공모빌리티' 가 걸린다
        ("청년미술프로젝트 2019", "문화·취미"),  # '청년' 을 쓰면 취업·창업으로 간다
        # 킨텍스
        ("2019서울모터쇼", "캠핑·레저"),
        ("2025 플레이엑스포", "문화·취미"),
        ("K-PRINT 2025", "산업·학술"),
        # 띄어쓰기·대소문자
        ("설맞이 명절선물전", "쇼핑·생활"),
        ("K-FOOD EXPO 2024", "식음료"),
    ],
)
def test_theme_of(title, theme):
    assert archive.theme_of(title) == theme


def test_keywords_are_normalized():
    """제목은 소문자·띄어쓰기 없이 비교하므로 키워드도 그래야 맞는다."""
    for _, words in archive.RULES:
        for w in words:
            assert w == "".join(w.casefold().split()), w


def test_theme_lists():
    rule_names = {name for name, _ in archive.RULES}
    assert set(archive.THEMES) | set(archive.EXCLUDED) == rule_names
    assert archive.THEMES[-1] == archive.B2B  # 화면에서 일반인 주제 다음, 맨 아래
    assert archive.OTHER not in rule_names


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
        ("exco", exco, "e4", "범어W 입주박람회", "2020-01-10~ 2020-01-12"),
        ("coex", coex, "c4", "제22대 국회의원선거 개표", "2020.04.10 - 2020.04.11"),
    ]
    for source, venue, ext, title, period in rows:
        archive.upsert(db, source=source, venue_id=venue.id, items=[_raw(ext, title, period)], now=NOW)

    data = client.get("/api/v1/stats/history", params={"from_year": 2019, "to_year": 2021}).json()
    assert data["total"] == 7 and data["venues"] == ["코엑스", "엑스코"]
    assert [(y["year"], y["total"]) for y in data["by_year"]] == [(2019, 3), (2020, 2), (2021, 2)]
    assert data["by_year"][0]["by_venue"] == {"코엑스": 2, "엑스코": 1}
    themes = {t["theme"]: t for t in data["themes"]}
    assert themes["베이비·육아"]["by_month"][2] == 1 and themes["베이비·육아"]["by_month"][8] == 1
    assert themes["베이비·육아"]["peak_months"] == [3, 9]  # 같은 수면 모두
    assert themes["캠핑·레저"]["peak_months"] == []  # 0건
    assert themes["산업·학술"]["total"] == 1  # 기계산업대전 (전에는 기타)
    assert data["other_total"] == 0
    assert data["excluded"] == {"입주박람회": 1, "박람회 아님": 1}
    assert {"기타", "입주박람회", "박람회 아님"}.isdisjoint(themes)


def test_setec_fetch_period_sends_date_range():
    calls = []

    class Client:
        def get(self, url, params=None):
            calls.append(params)
            return ""

    get_parser("setec")(Client()).fetch_period(date(2023, 5, 1), date(2023, 5, 31))
    assert calls == [{"searchSDate": "2023-05-01", "searchEDate": "2023-05-31", "pageIndex": 1}]
