"""관리자 박람회 등록·수정 스키마 (레퍼런스 7장 '관리자', F-08)."""

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.schemas.fair import PublicAccess

FairStatus = Literal["draft", "published", "hidden"]


class _FairFields(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(description="카테고리 code")
    venue_id: int
    hall: str | None = Field(default=None, max_length=100)
    start_date: date
    end_date: date
    open_time: time | None = None
    close_time: time | None = None
    hours_note: str | None = Field(default=None, max_length=255)
    public_access: PublicAccess = "unknown"
    access_note: str | None = Field(default=None, max_length=255)
    price_onsite: int | None = Field(default=None, ge=0)  # 0 = 무료, None = 미확인
    price_prereg: int | None = Field(default=None, ge=0)
    # 시간대가 없으면 한국 시간으로 본다
    prereg_start_at: datetime | None = None
    prereg_end_at: datetime | None = None
    prereg_url: HttpUrl | None = None
    official_url: HttpUrl | None = None
    summary: str | None = None
    visit_tip: str | None = None
    image_url: HttpUrl | None = None
    status: FairStatus = "draft"
    tags: list[str] = Field(default_factory=list, description="태그 slug 목록")


class FairCreate(_FairFields):
    verified: bool = False  # true 면 정보 확인일(verified_at)을 지금으로 기록

    @model_validator(mode="after")
    def check_period(self):
        if self.end_date < self.start_date:
            raise ValueError("끝 날짜가 시작 날짜보다 빨라요")
        return self


class FairUpdate(BaseModel):
    """PATCH: 보낸 필드만 바꾼다."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = None
    venue_id: int | None = None
    hall: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    open_time: time | None = None
    close_time: time | None = None
    hours_note: str | None = Field(default=None, max_length=255)
    public_access: PublicAccess | None = None
    access_note: str | None = Field(default=None, max_length=255)
    price_onsite: int | None = Field(default=None, ge=0)
    price_prereg: int | None = Field(default=None, ge=0)
    prereg_start_at: datetime | None = None
    prereg_end_at: datetime | None = None
    prereg_url: HttpUrl | None = None
    official_url: HttpUrl | None = None
    summary: str | None = None
    visit_tip: str | None = None
    image_url: HttpUrl | None = None
    status: FairStatus | None = None
    tags: list[str] | None = None
    verified: bool | None = None


class AdminFairRow(BaseModel):
    id: int
    title: str
    status: FairStatus
    category: str
    venue: str
    start_date: date
    end_date: date
    source: Literal["manual", "crawler", "api"]
    verified_at: datetime | None
    updated_at: datetime


class AdminFair(_FairFields):
    """수정 화면에 그대로 채울 수 있는 형태."""

    id: int
    source: Literal["manual", "crawler", "api"]
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    prereg_url: str | None = None
    official_url: str | None = None
    image_url: str | None = None
