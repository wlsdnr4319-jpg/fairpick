from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.admin import FairCreate


class MergeCandidate(BaseModel):
    fair_id: int
    title: str
    start_date: date
    end_date: date
    similarity: float


class CrawledItemOut(BaseModel):
    id: int
    source: str  # parser_key
    external_id: str
    raw_title: str
    raw_period: str | None
    raw_venue: str | None
    detail_url: str | None
    raw_payload: dict[str, Any] | None
    parsed_start_date: date | None
    parsed_end_date: date | None
    parsed_venue_id: int | None
    parsed_venue_name: str | None
    change_status: Literal["new", "changed", "unchanged"]
    review_status: Literal["pending", "approved", "rejected", "merged"]
    fair_id: int | None
    first_seen_at: datetime
    last_seen_at: datetime
    merge_candidates: list[MergeCandidate] = []


class ApproveIn(FairCreate):
    """승인: 관리자가 일반인 관람 여부·입장료·태그·관람 팁을 채운 뒤 새 박람회를 만든다."""

    # 장소를 못 맞춘 항목에서 관리자가 전시장을 골랐을 때, 원본 장소 문자열을 그 전시장의 별칭으로 저장한다
    venue_alias: str | None = Field(default=None, min_length=1, max_length=100)

    def fair_fields(self) -> FairCreate:
        return FairCreate.model_validate(self.model_dump(exclude={"venue_alias"}))


class MergeIn(BaseModel):
    fair_id: int


class CrawlSourceOut(BaseModel):
    id: int
    parser_key: str
    venue: str
    list_url: str
    is_active: bool
    policy_checked_at: datetime | None
    policy_note: str | None
    last_run_status: str | None
    last_run_at: datetime | None


class CrawlRunOut(BaseModel):
    id: int
    source: str
    status: Literal["running", "succeeded", "failed"]
    found_count: int
    new_count: int
    changed_count: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None
