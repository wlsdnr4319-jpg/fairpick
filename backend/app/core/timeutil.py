"""
날짜·시간 규칙 (레퍼런스 6장 설계 원칙, 7장 공통 규칙).

- DB 의 DATETIME 은 시간대 없는 UTC 로 저장한다.
- 응답의 일시는 한국 시간 오프셋을 붙인 ISO 8601 로 보낸다. 예: 2026-11-16T23:59:00+09:00
- '오늘'은 DB 의 CURDATE() 가 아니라 앱에서 한국 시간 기준으로 계산해 넘긴다.
  DB 서버가 UTC 면 자정 무렵 날짜가 하루 어긋나기 때문이다.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def app_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().app_tz)


def today_kst() -> date:
    return datetime.now(app_tz()).date()


def to_local(value: datetime | None) -> datetime | None:
    """DB 의 naive UTC → 한국 시간(+09:00) aware datetime."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC).astimezone(app_tz())


def to_utc_naive(value: datetime) -> datetime:
    """입력 일시(시간대 없으면 한국 시간으로 간주) → DB 저장용 naive UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=app_tz())
    return value.astimezone(UTC).replace(tzinfo=None)


def progress_of(start: date, end: date, today: date) -> str:
    """진행 상태는 저장하지 않고 날짜로 계산한다: upcoming / ongoing / ended"""
    if today < start:
        return "upcoming"
    if today > end:
        return "ended"
    return "ongoing"


def d_day_of(start: date, today: date) -> int:
    """개막까지 남은 일수. DATEDIFF(start_date, today) 와 같다. 진행 중이면 0 이하."""
    return (start - today).days
