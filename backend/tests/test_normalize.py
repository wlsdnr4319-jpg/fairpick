"""정규화 순수 함수 (레퍼런스 13장: 날짜·장소 정규화는 단위 테스트를 촘촘히)."""

from datetime import date

import pytest

from app.crawlers.base import clean_text, venue_text
from app.crawlers.normalize import PeriodParseError, content_hash, match_venue, parse_period


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026.11.19(목) ~ 11.22(일)", (date(2026, 11, 19), date(2026, 11, 22))),
        ("2026-11-19 ~ 2026-11-22", (date(2026, 11, 19), date(2026, 11, 22))),
        ("2026.10.29 - 2026.11.01", (date(2026, 10, 29), date(2026, 11, 1))),  # 코엑스 목록 형식
        ("2026.11.03~2026.11.05", (date(2026, 11, 3), date(2026, 11, 5))),  # 킨텍스 목록 형식
        ("2026.11.19(목) ~ 22(일)", (date(2026, 11, 19), date(2026, 11, 22))),  # 끝 월 생략
        ("2026.12.30 ~ 1.2", (date(2026, 12, 30), date(2027, 1, 2))),  # 해 넘김
        ("2026년 11월 19일 ~ 11월 22일", (date(2026, 11, 19), date(2026, 11, 22))),
        ("2026.11.05 - 2026.11.05", (date(2026, 11, 5), date(2026, 11, 5))),
        ("2026-11-19", (date(2026, 11, 19), date(2026, 11, 19))),  # 하루짜리
        ("2026. 11. 19 (THU) ~ 11. 22 (SUN)", (date(2026, 11, 19), date(2026, 11, 22))),
    ],
)
def test_parse_period(text, expected):
    assert parse_period(text) == expected


def test_parse_period_uses_ref_year_when_missing():
    assert parse_period("11월 19일~22일", ref_year=2026) == (date(2026, 11, 19), date(2026, 11, 22))


@pytest.mark.parametrize("text", ["", "미정", "11월 19일~22일", "2026.13.40 ~ 2026.13.41", "2026.11.22 ~ 2026.11.19"])
def test_parse_period_failures(text):
    with pytest.raises(PeriodParseError):
        parse_period(text)


ALIASES = {"코엑스": 1, "COEX": 1, "서울 코엑스": 1, "코엑스 마곡": 2, "킨텍스": 3, "KINTEX": 3}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("코엑스 A홀", (1, "A홀")),
        ("COEX Hall B", (1, "Hall B")),
        ("서울 코엑스 C홀", (1, "C홀")),
        ("코엑스 마곡 1층 전시장", (2, "1층 전시장")),  # 더 긴 별칭이 이긴다
        ("킨텍스", (3, None)),
        ("kintex 전시홀 7", (3, "전시홀 7")),  # 대소문자 무시
        ("벡스코 1홀", (None, None)),
        ("", (None, None)),
    ],
)
def test_match_venue(text, expected):
    assert match_venue(text, ALIASES) == expected


def test_content_hash_ignores_whitespace_but_not_content():
    a = content_hash("서울카페쇼", "2026.11.11 - 2026.11.14", "코엑스 전관")
    assert a == content_hash("서울카페쇼 ", "2026.11.11  -  2026.11.14", "코엑스  전관")
    assert a != content_hash("서울카페쇼", "2026.11.11 - 2026.11.15", "코엑스 전관")
    assert len(a) == 64


def test_text_helpers():
    assert clean_text("전시홀 6C\n\t\t ,\n 전시홀 7") == "전시홀 6C, 전시홀 7"
    assert venue_text("코엑스", "Hall A") == "코엑스 Hall A"
    assert venue_text("코엑스", "코엑스 광장") == "코엑스 광장"
    assert venue_text("코엑스", "") == "코엑스"
