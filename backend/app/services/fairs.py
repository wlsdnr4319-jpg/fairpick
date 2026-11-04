"""
박람회 조회 로직.

2주차: 공개 박람회 목록(개막순·페이지네이션)과 상세.
3주차: 필터(카테고리·태그·지역·기간·무료·일반인 관람), 검색, 정렬을 list_fairs 에 추가한다.
"""

from datetime import date

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

# 카드마다 장소·카테고리·태그를 따로 조회하는 N+1 문제를 막는다 (레퍼런스 6장)
_LOAD_RELATIONS = (
    selectinload(Fair.category),
    selectinload(Fair.venue),
    selectinload(Fair.fair_tags).selectinload(FairTag.tag),
)


def list_fairs(db: Session, *, page: int, size: int) -> tuple[list[Fair], int]:
    base = select(Fair).where(Fair.status == "published")

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    fairs = db.scalars(
        base.options(*_LOAD_RELATIONS)
        .order_by(Fair.start_date, Fair.id)
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return list(fairs), total


def get_published_fair(db: Session, fair_id: int) -> Fair | None:
    """비공개(draft, hidden) 박람회는 없는 것과 똑같이 취급한다 (FAIR_NOT_FOUND)."""
    return db.scalar(
        select(Fair).where(Fair.id == fair_id, Fair.status == "published").options(*_LOAD_RELATIONS)
    )


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


def to_card(fair: Fair, today: date) -> FairCard:
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
