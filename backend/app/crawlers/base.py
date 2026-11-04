"""
수집 파서의 공통 틀 (레퍼런스 8장 파서 구조).

전시장마다 파서 클래스 하나를 만들고 parser_key 로 등록한다.
새 전시장을 추가할 때는 클래스 하나와 crawl_sources 행 하나만 늘어난다.

크롤링은 이름·기간·장소 같은 뼈대만 가져온다. 일반인 관람 여부·태그·관람 팁은 검수 단계에서 사람이 채운다.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any

from app.crawlers.http import PoliteClient


@dataclass
class RawFair:
    external_id: str  # 원본 사이트의 행사 ID 또는 상세 URL
    title: str
    period_text: str  # 예: "2026.11.19(목) ~ 11.22(일)"
    venue_text: str  # 예: "코엑스 A홀"
    detail_url: str
    extra: dict[str, Any] = field(default_factory=dict)  # 행사 구분 등 사이트별 추가 정보

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


class BaseParser(ABC):
    parser_key: str
    # True 면 fetch_list(year, month) 를 달마다 부른다. False 면 한 번만 부른다 (사이트가 월 지정을 지원하지 않을 때)
    monthly: bool = True

    def __init__(self, client: PoliteClient):
        self.client = client

    @abstractmethod
    def fetch_list(self, year: int, month: int) -> list[RawFair]:
        """해당 월의 목록 페이지를 가져와 RawFair 목록으로 바꾼다."""

    @abstractmethod
    def parse_list(self, html: str) -> list[RawFair]:
        """목록 HTML 한 페이지를 파싱한다. 네트워크 없이 테스트할 수 있게 분리한다."""


def clean_text(value: str) -> str:
    """줄바꿈·연속 공백을 한 칸으로, 쉼표 앞 공백을 없앤다."""
    return re.sub(r"\s+,", ",", re.sub(r"\s+", " ", value or "")).strip()


def venue_text(venue_name: str, hall: str) -> str:
    """'코엑스' + 'Hall A' → '코엑스 Hall A'. 홀 이름이 이미 전시장 이름으로 시작하면 붙이지 않는다."""
    hall = clean_text(hall)
    if not hall:
        return venue_name
    return hall if hall.startswith(venue_name) else f"{venue_name} {hall}"
