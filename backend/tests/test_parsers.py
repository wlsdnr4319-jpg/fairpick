"""
파서 테스트는 실제 사이트에 요청하지 않는다. 2026-11-04 에 저장한 목록 HTML(fixtures/html)로 검증한다.
사이트 구조가 바뀌면 fixture 를 새로 저장하고 테스트를 고친다 (레퍼런스 13장).
"""

from datetime import date
from pathlib import Path

import pytest

from app.crawlers import calendar, coexmagok
from app.crawlers.normalize import parse_period
from app.crawlers.registry import get_parser

FIXTURES = Path(__file__).parent / "fixtures" / "html"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _parse(key: str, name: str):
    return get_parser(key)(client=None).parse_list(_read(name))


class FakeClient:
    """요청 내용을 기록하고, 정해 둔 응답을 돌려준다. 없는 요청에는 빈 문자열."""

    def __init__(self, get=None, post=None):
        self._get, self._post = get or (lambda url, params: ""), post or (lambda url, data: "")
        self.calls = []

    def get(self, url, params=None):
        self.calls.append(("GET", url, params))
        return self._get(url, params)

    def post(self, url, data=None):
        self.calls.append(("POST", url, data))
        return self._post(url, data)


def test_coex_list():
    items = _parse("coex", "coex_list.html")
    assert len(items) == 6
    by_title = {i.title: i for i in items}
    baby = by_title["2026 코베 베이비페어"]
    assert baby.period_text == "2026.10.29 - 2026.11.01"
    assert baby.venue_text == "코엑스 Hall A"
    assert baby.external_id.startswith("/exhibitions/") and "?" not in baby.external_id
    assert baby.detail_url.startswith("https://www.coex.co.kr/exhibitions/")
    assert baby.extra["kind"] == "Exhibition"
    # Convention(학회·세미나)은 건너뛴다
    assert all(i.extra["kind"] != "Convention" for i in items)
    # 모든 기간 문자열을 정규화할 수 있어야 한다
    for i in items:
        parse_period(i.period_text)


def test_kintex_list():
    items = _parse("kintex", "kintex_list.html")
    assert len(items) == 8
    hydrogen = next(i for i in items if i.external_id == "26040310")
    assert hydrogen.venue_text == "킨텍스 전시홀 6C, 전시홀 7, 전시홀 8"
    assert hydrogen.detail_url == "https://www.kintex.com/web/ko/event/view.do?seq=26040310"
    assert {i.title for i in items} >= {"코믹월드 339 일산", "2026 로보월드"}
    for i in items:
        parse_period(i.period_text)


def test_kintex_past_list_skips_exhibitor_notice():
    """2026-11-11 저장: 2019년 1~3월 전시 기간 검색 결과 (pageUnit=100)."""
    items = _parse("kintex", "kintex_2019q1.html")
    titles = [i.title for i in items]
    assert len(items) == 16  # 17개 중 '2019서울모터쇼(참가업체용)' 제외
    assert "2019서울모터쇼" in titles and not any("참가업체용" in t for t in titles)
    assert parse_period(items[0].period_text) == (date(2019, 1, 25), date(2019, 1, 27))
    for i in items:
        parse_period(i.period_text)


def test_kintex_fetch_period_pages_until_nothing_new():
    page1 = _read("kintex_2019q1.html")
    client = FakeClient(get=lambda url, params: page1 if params["pageIndex"] == 1 else "")
    items = get_parser("kintex")(client).fetch_period(date(2019, 1, 1), date(2019, 3, 31))
    assert len(items) == 16
    search = {"searchType": "11", "searchStartDt": "2019-01-01", "searchEndDt": "2019-03-31", "pageUnit": 100}
    assert [c[2] for c in client.calls] == [{**search, "pageIndex": p} for p in (1, 2)]


def test_empty_or_changed_markup_returns_nothing():
    assert get_parser("coex")(client=None).parse_list("<html><body>점검 중</body></html>") == []
    assert get_parser("kintex")(client=None).parse_list("") == []
    for key in ("setec", "suwonmesse", "exco", "coexmagok"):
        assert get_parser(key)(client=None).parse_list("<html><body>점검 중</body></html>") == []


def test_setec_list():
    items = _parse("setec", "setec_list.html")
    assert len(items) == 12
    first = items[0]
    assert (first.external_id, first.title) == ("2255", "2026 서울건축박람회 (추계)")
    assert first.period_text == "2026-11-05 ~ 2026-11-08"
    assert first.venue_text == "SETEC 제1전시실, 제2전시실, 제3전시실"
    assert first.detail_url == "https://www.setec.or.kr/front/schedule/view.do?sIdx=2255"
    for i in items:
        parse_period(i.period_text)


def test_setec_fetch_stops_when_page_has_nothing_new():
    pages = {1: _read("setec_list.html")}
    client = FakeClient(get=lambda url, params: pages.get(params["pageIndex"], ""))
    items = get_parser("setec")(client=client).fetch_list(2026, 11)
    assert len(items) == 12 and len(client.calls) == 2


def test_suwonmesse_calendar_collects_days_into_period():
    items = {i.external_id: i for i in _parse("suwonmesse", "suwonmesse_2026_11.html")}
    assert len(items) == 8
    assert items["704"].title == "2026 수원 우수중소기업 & 밀리언쇼"
    assert items["704"].period_text == "2026.11.12 ~ 2026.11.16"  # 5개 칸 → 하나의 기간
    assert items["704"].venue_text == "수원메쎄"
    assert items["704"].detail_url.endswith("?uid=704&mod=document")
    # 12월 달력의 앞뒤 칸(11월 29·30일, 1월 1·2일)은 건너뛰므로 11월 행사가 섞이지 않는다
    assert [i.external_id for i in _parse("suwonmesse", "suwonmesse_2026_12.html")] == ["702"]


def test_suwonmesse_fetch_merges_four_months():
    pages = {(2026, 11): _read("suwonmesse_2026_11.html"), (2026, 12): _read("suwonmesse_2026_12.html")}
    client = FakeClient(get=lambda url, p: pages.get((p["kboard_calendar_year"], p["kboard_calendar_month"]), ""))
    items = get_parser("suwonmesse")(client=client).fetch_list(2026, 11)
    assert [(c[2]["kboard_calendar_year"], c[2]["kboard_calendar_month"]) for c in client.calls] == [
        (2026, 10),
        (2026, 11),
        (2026, 12),
        (2027, 1),
    ]
    assert len(items) == 9


def test_suwonmesse_skips_meetings_and_placeholders():
    html = _read("suwonmesse_2026_11.html")
    assert get_parser("suwonmesse")(client=None).parse_list(html.replace('btn-fair">전시<', 'btn-fair">회의<')) == []
    renamed = html.replace("2026 수원 우수중소기업 &amp; 밀리언쇼", "비공개행사")
    assert "704" not in {i.external_id for i in get_parser("suwonmesse")(client=None).parse_list(renamed)}


def test_backfill_calendar_year_starts_from_last_december():
    from app.scripts.backfill_archive import calendar_year

    pages = {(2026, 11): _read("suwonmesse_2026_11.html"), (2026, 12): _read("suwonmesse_2026_12.html")}
    client = FakeClient(get=lambda url, p: pages.get((p["kboard_calendar_year"], p["kboard_calendar_month"]), ""))
    items = calendar_year(get_parser("suwonmesse")(client=client), 2026)
    months = [(c[2]["kboard_calendar_year"], c[2]["kboard_calendar_month"]) for c in client.calls]
    assert len(months) == 13 and months[0] == (2025, 12) and months[-1] == (2026, 12)
    assert len(items) == 9


def test_coexmagok_fetch_month_asks_next_of_previous_month():
    december = _read("coexmagok_ajax_2026_12.txt")
    client = FakeClient(post=lambda url, data: december)
    events = get_parser("coexmagok")(client=client).fetch_month(2027, 1)
    ((_, _, data),) = client.calls
    assert (data["change_flag"], data["current_year"], data["current_month"]) == ("NEXT", 2026, 12)
    assert events  # 응답을 그대로 파싱한다


def test_calendar_merge_joins_days_across_months():
    nov = {"a": calendar.CalendarEvent("행사", "전시", "u", "수원메쎄", {date(2026, 11, 29), date(2026, 11, 30)})}
    dec = {"a": calendar.CalendarEvent("행사", "전시", "u", "수원메쎄", {date(2026, 12, 1), date(2026, 12, 2)})}
    merged: dict = {}
    calendar.merge(merged, nov)
    calendar.merge(merged, dec)
    (raw,) = calendar.to_raw(merged)
    assert raw.period_text == "2026.11.29 ~ 2026.12.02"
    # 지난달 달력에서 온, 이미 끝난 행사는 뺀다
    assert calendar.to_raw(merged, since=date(2026, 12, 1)) != []
    assert calendar.to_raw(merged, since=date(2026, 12, 3)) == []
    assert parse_period(raw.period_text) == (date(2026, 11, 29), date(2026, 12, 2))
    assert calendar.shift_month(2026, 1, -1) == (2025, 12) and calendar.shift_month(2026, 11, 2) == (2027, 1)


def test_exco_yearly_table():
    items = _parse("exco", "exco_2026.html")
    assert len(items) == 88
    assert len({i.external_id for i in items}) == 88  # 같은 이름이 한 해에 여러 번 열려도 겹치지 않는다
    wedding = items[0]
    assert wedding.external_id == "2026-01-03:컬러풀대구 웨딩박람회 in 엑스코"
    assert wedding.venue_text == "엑스코"
    assert "1644" not in str(wedding.to_payload())  # 주최자 전화번호는 저장하지 않는다
    for i in items:
        parse_period(i.period_text)


def test_exco_fetch_keeps_only_events_ending_this_month_or_later():
    tables = {2026: _read("exco_2026.html")}
    client = FakeClient(get=lambda url, p: tables.get(p["syear"], ""))
    items = get_parser("exco")(client=client).fetch_list(2026, 11)
    assert [c[2] for c in client.calls] == [{"syear": 2026, "ex_cate": "1"}, {"syear": 2027, "ex_cate": "1"}]
    assert len(items) == 10
    assert all(parse_period(i.period_text)[1] >= date(2026, 11, 1) for i in items)


def test_coexmagok_page_and_ajax_months():
    page, december = _read("coexmagok_2026_11.html"), _read("coexmagok_ajax_2026_12.txt")

    def post(url, data):
        if (data["change_flag"], data["current_month"]) == ("NEXT", 11):
            return december
        return "OK^2026^10^^2026-09-27^2026-11-07"  # 칸이 없는 달

    client = FakeClient(get=lambda url, p: page, post=post)
    items = {i.title: i for i in get_parser("coexmagok")(client=client).fetch_list(2026, 11)}
    assert [c[0] for c in client.calls] == ["GET", "POST", "POST", "POST"]
    assert "2026 코리아더마" in items  # 12월 AJAX 응답에서 온 행사
    assert "2026 서울머니쇼 플러스" not in items  # 10월 31일에 끝난 행사 (달력 앞쪽 칸)
    baby = items["마곡 베페 베이비페어"]
    assert baby.period_text == "2026.11.12 ~ 2026.11.15"
    assert baby.external_id == "/exhibitions/마곡-베페-베이비페어/"
    assert baby.detail_url.startswith("https://coexmagok.co.kr/exhibitions/") and "?" not in baby.detail_url
    # 컨벤션(학회·면접 등)은 건너뛴다
    assert not any("학술대회" in t or "면접" in t for t in items)


def test_coexmagok_layout_change_is_an_error():
    # 칸 순서로 계산한 날짜와 화면의 일(日) 숫자가 다르면 구조가 바뀐 것 → 수집 실패로 기록
    html = _read("coexmagok_2026_11.html").replace('value="2026-10-25"', 'value="2026-10-26"')
    with pytest.raises(coexmagok.CalendarLayoutError):
        coexmagok.collect_page(html)
    with pytest.raises(coexmagok.CalendarLayoutError):
        coexmagok.collect_ajax("NO_PARAMETERS")
