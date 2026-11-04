"""
파서 테스트는 실제 사이트에 요청하지 않는다. 2026-11-04 에 저장한 목록 HTML(fixtures/html)로 검증한다.
사이트 구조가 바뀌면 fixture 를 새로 저장하고 테스트를 고친다 (레퍼런스 13장).
"""

from pathlib import Path

from app.crawlers.normalize import parse_period
from app.crawlers.registry import get_parser

FIXTURES = Path(__file__).parent / "fixtures" / "html"


def _parse(key: str, name: str):
    return get_parser(key)(client=None).parse_list((FIXTURES / name).read_text(encoding="utf-8"))


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


def test_empty_or_changed_markup_returns_nothing():
    assert get_parser("coex")(client=None).parse_list("<html><body>점검 중</body></html>") == []
    assert get_parser("kintex")(client=None).parse_list("") == []
