"""
박람회 응답 스키마 (레퍼런스 7장 'GET /fairs/{fair_id}' 응답 예시).

API 필드명은 레퍼런스 예시대로 snake_case 를 쓴다.
"""

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel

Progress = Literal["upcoming", "ongoing", "ended"]
PublicAccess = Literal["public", "partial", "trade_only", "unknown"]


class CategoryOut(BaseModel):
    code: str
    name: str


class VenueOut(BaseModel):
    id: int
    name: str
    region: str
    hall: str | None = None


class VenueDetailOut(VenueOut):
    """상세 화면용: 주소와 지도 좌표 (레퍼런스 F-20 지도·길찾기). 좌표가 없으면 이름으로 지도 검색."""

    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    parking_note: str | None = None


class TagOut(BaseModel):
    slug: str
    name: str


class PriceOut(BaseModel):
    onsite: int | None  # 0 = 무료, None = 미확인
    prereg: int | None  # 0 = 사전등록 시 무료


class HoursOut(BaseModel):
    open: time | None
    close: time | None
    note: str | None


class PreregOut(BaseModel):
    start_at: datetime | None  # +09:00
    end_at: datetime | None
    url: str | None


class FairCard(BaseModel):
    """목록 카드 (레퍼런스 4장: 대표 이미지, 제목, 기간, 장소, 상태 배지, 태그 칩)."""

    id: int
    title: str
    category: CategoryOut
    venue: VenueOut
    start_date: date
    end_date: date
    progress: Progress
    d_day: int
    public_access: PublicAccess
    price: PriceOut
    prereg_end_at: datetime | None
    tags: list[TagOut]
    image_url: str | None
    is_bookmarked: bool = False  # 로그인 사용자의 북마크 여부


class FairDetail(BaseModel):
    id: int
    title: str
    category: CategoryOut
    venue: VenueDetailOut
    start_date: date
    end_date: date
    progress: Progress
    d_day: int
    hours: HoursOut
    public_access: PublicAccess
    access_note: str | None
    price: PriceOut
    prereg: PreregOut
    tags: list[TagOut]
    summary: str | None
    visit_tip: str | None
    official_url: str | None
    image_url: str | None
    verified_at: datetime | None  # 상세 화면의 '정보 확인일'
    is_bookmarked: bool  # 로그인 기능(4주차) 전까지는 항상 false
    bookmark_count: int


class Page[T](BaseModel):
    """목록 응답은 { items, total, page, size } 로 통일한다 (레퍼런스 7장)."""

    items: list[T]
    total: int
    page: int
    size: int


class RefCategory(BaseModel):
    code: str
    name: str


class RefTag(BaseModel):
    id: int
    slug: str
    name: str
    is_votable: bool


class RefVenue(BaseModel):
    id: int
    name: str
    region: str
    address: str | None
