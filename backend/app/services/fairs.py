"""
박람회 조회 로직: 공개 박람회 목록(필터·검색·정렬·페이지네이션)과 상세.
필터 조건은 fair_query.py 에 있다.
"""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.timeutil import d_day_of, progress_of, to_local
from app.models import Bookmark, Fair, FairTag
from app.schemas.fair import (
    CategoryOut,
    FairCard,
    FairDetail,
    HoursOut,
    PreregOut,
    PriceOut,
    TagOut,
    VenueOut,
)
from app.services.fair_query import FairFilter, apply_filters, apply_sort

# 카드마다 장소·카테고리·태그를 따로 조회하는 N+1 문제를 막는다 (레퍼런스 6장)
LOAD_RELATIONS = (
    selectinload(Fair.category),
    selectinload(Fair.venue),
    selectinload(Fair.fair_tags).selectinload(FairTag.tag),
)


def list_fairs(
    db: Session, f: FairFilter, *, today: date, now_utc: datetime, page: int, size: int
) -> tuple[list[Fair], int]:
    base = apply_filters(select(Fair), f, today, now_utc)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    fairs = db.scalars(apply_sort(base, f).options(*LOAD_RELATIONS).offset((page - 1) * size).limit(size)).all()
    return list(fairs), total


def bookmarked_ids(db: Session, user_id: int | None, fair_ids: list[int]) -> set[int]:
    """로그인 사용자가 북마크한 박람회 id. 비로그인이면 빈 집합."""
    if user_id is None or not fair_ids:
        return set()
    return set(db.scalars(select(Bookmark.fair_id).where(Bookmark.user_id == user_id, Bookmark.fair_id.in_(fair_ids))))


def get_published_fair(db: Session, fair_id: int) -> Fair | None:
    """비공개(draft, hidden) 박람회는 없는 것과 똑같이 취급한다 (FAIR_NOT_FOUND)."""
    return db.scalar(select(Fair).where(Fair.id == fair_id, Fair.status == "published").options(*LOAD_RELATIONS))


def count_bookmarks(db: Session, fair_id: int) -> int:
    return db.scalar(select(func.count()).where(Bookmark.fair_id == fair_id)) or 0


# ---------------------------------------------------------------------------
# 모델 → 응답 변환
# ---------------------------------------------------------------------------


def _tags(fair: Fair) -> list[TagOut]:
    tags = sorted((ft.tag for ft in fair.fair_tags), key=lambda t: t.id)
    return [TagOut(slug=t.slug, name=t.name) for t in tags]


def _venue(fair: Fair) -> VenueOut:
    return VenueOut(id=fair.venue.id, name=fair.venue.name, region=fair.venue.region, hall=fair.hall)


def to_card(fair: Fair, today: date, *, is_bookmarked: bool = False) -> FairCard:
    return FairCard(
        id=fair.id,
        title=fair.title,
        category=CategoryOut(code=fair.category.code, name=fair.category.name),
        venue=_venue(fair),
        start_date=fair.start_date,
        end_date=fair.end_date,
        progress=progress_of(fair.start_date, fair.end_date, today),
        d_day=d_day_of(fair.start_date, today),
        public_access=fair.public_access,
        price=PriceOut(onsite=fair.price_onsite, prereg=fair.price_prereg),
        prereg_end_at=to_local(fair.prereg_end_at),
        tags=_tags(fair),
        image_url=fair.image_url,
        is_bookmarked=is_bookmarked,
    )


def to_detail(fair: Fair, today: date, *, bookmark_count: int, is_bookmarked: bool) -> FairDetail:
    return FairDetail(
        id=fair.id,
        title=fair.title,
        category=CategoryOut(code=fair.category.code, name=fair.category.name),
        venue=_venue(fair),
        start_date=fair.start_date,
        end_date=fair.end_date,
        progress=progress_of(fair.start_date, fair.end_date, today),
        d_day=d_day_of(fair.start_date, today),
        hours=HoursOut(open=fair.open_time, close=fair.close_time, note=fair.hours_note),
        public_access=fair.public_access,
        access_note=fair.access_note,
        price=PriceOut(onsite=fair.price_onsite, prereg=fair.price_prereg),
        prereg=PreregOut(
            start_at=to_local(fair.prereg_start_at),
            end_at=to_local(fair.prereg_end_at),
            url=fair.prereg_url,
        ),
        tags=_tags(fair),
        summary=fair.summary,
        visit_tip=fair.visit_tip,
        official_url=fair.official_url,
        image_url=fair.image_url,
        verified_at=to_local(fair.verified_at),
        is_bookmarked=is_bookmarked,
        bookmark_count=bookmark_count,
    )
