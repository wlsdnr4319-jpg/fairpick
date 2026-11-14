from datetime import date, datetime

from pydantic import BaseModel, Field


class CalendarItem(BaseModel):
    id: int
    title: str
    start_date: date
    end_date: date
    category: str  # code
    category_name: str
    venue: str
    region: str
    hall: str | None
    bookmark_count: int
    # 행사 규모 점수 (클수록 큰 행사). 캘린더 칸에 큰 행사만 몇 개 보여 줄 때 쓴다 (routers/engagement.calendar_scale)
    scale: int


class VisitIn(BaseModel):
    visited_on: date | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    memo: str | None = Field(default=None, max_length=2000)
    is_public: bool = False


class VisitPatch(BaseModel):
    visited_on: date | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    memo: str | None = Field(default=None, max_length=2000)
    is_public: bool | None = None


class VisitOut(BaseModel):
    id: int
    fair_id: int
    fair_title: str
    visited_on: date | None
    rating: int | None
    memo: str | None
    is_public: bool
    like_count: int
    created_at: datetime
    updated_at: datetime


class ReviewOut(BaseModel):
    id: int
    nickname: str
    visited_on: date | None
    rating: int | None
    memo: str | None
    like_count: int
    liked_by_me: bool
    is_mine: bool
    created_at: datetime


class ReviewPage(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    size: int
    rating_avg: float | None  # 별점을 남긴 공개 후기의 평균
    rating_count: int


class LikeOut(BaseModel):
    visit_id: int
    liked: bool
    like_count: int


class TagVoteOut(BaseModel):
    tag_id: int
    slug: str
    name: str
    vote_count: int
    voted: bool
    applied: bool  # 박람회 태그로 붙어 있는지 (관리자 또는 투표 3표 이상)
