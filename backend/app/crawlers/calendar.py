"""
달력형 일정 페이지 공통 처리 (수원메쎄, 코엑스 마곡).

달력은 행사가 열리는 날짜 칸마다 같은 행사를 반복해서 보여준다.
칸에서 (행사 ID, 날짜)를 모아 가장 이른 날 ~ 가장 늦은 날을 기간으로 만든다.
달을 넘기는 행사가 잘리지 않도록 여러 달을 받아 merge 로 합친다.
"""

from dataclasses import dataclass, field
from datetime import date

from app.crawlers.base import RawFair

# 지난달 + 이번 달 + 앞으로 2달. 지난달은 이번 달까지 이어지는 행사의 시작일을 얻으려고 받는다
MONTH_OFFSETS = (-1, 0, 1, 2)


@dataclass
class CalendarEvent:
    title: str
    kind: str
    detail_url: str
    venue_text: str
    days: set[date] = field(default_factory=set)


def shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + offset
    return index // 12, index % 12 + 1


def merge(into: dict[str, CalendarEvent], events: dict[str, CalendarEvent]) -> None:
    for key, event in events.items():
        if key in into:
            into[key].days |= event.days
        else:
            into[key] = event


def to_raw(events: dict[str, CalendarEvent], since: date | None = None) -> list[RawFair]:
    """since 를 주면 그 전에 끝난 행사는 뺀다 (지난달 달력은 시작일을 얻으려고 받을 뿐, 끝난 행사는 필요 없다)."""
    out = []
    for key, event in events.items():
        start, end = min(event.days), max(event.days)
        if since and end < since:
            continue
        out.append(
            RawFair(
                external_id=key,
                title=event.title,
                period_text=f"{start:%Y.%m.%d} ~ {end:%Y.%m.%d}",
                venue_text=event.venue_text,
                detail_url=event.detail_url,
                extra={"kind": event.kind},
            )
        )
    return sorted(out, key=lambda r: (r.period_text, r.external_id))
