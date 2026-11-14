"""
GET /fairs 의 필터·검색·정렬 조건 (레퍼런스 7장 'GET /fairs 쿼리 파라미터', 6장 예시 쿼리).

날짜 조건은 모두 '기간 겹침'으로 판단한다: start_date <= 범위 끝 AND end_date >= 범위 시작
"""

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Literal

from sqlalchemy import Select, and_, case, func, or_, select, text

from app.core.errors import AppError
from app.core.geo import distance_m_sql
from app.models import Bookmark, Category, Fair, FairTag, Tag, Venue

Period = Literal["this_weekend", "this_month", "ongoing", "upcoming"]
Sort = Literal["start_date", "prereg_deadline", "popular", "distance"]


@dataclass
class FairFilter:
    q: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    region: str | None = None
    period: Period | None = None
    date_from: date | None = None
    date_to: date | None = None
    free: bool = False
    public_only: bool = False
    sort: Sort = "start_date"
    near: tuple[float, float] | None = None  # (위도, 경도). 거리순·반경 필터의 기준 위치
    radius_km: float | None = None


def _venue_distance_m(near: tuple[float, float]):
    return distance_m_sql(Venue.latitude, Venue.longitude, *near)


def weekend_of(today: date) -> tuple[date, date]:
    """'이번 주말' = 이번 주 토·일. 오늘이 토·일이면 오늘이 속한 주말."""
    saturday = today + timedelta(days=(5 - today.weekday()) % 7)
    if today.weekday() == 6:  # 일요일
        saturday = today - timedelta(days=1)
    return saturday, saturday + timedelta(days=1)


def month_of(today: date) -> tuple[date, date]:
    last = calendar.monthrange(today.year, today.month)[1]
    return today.replace(day=1), today.replace(day=last)


def _overlaps(start: date, end: date):
    return and_(Fair.start_date <= end, Fair.end_date >= start)


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return list(dict.fromkeys(t.strip() for t in raw.split(",") if t.strip()))


def validate(f: FairFilter) -> None:
    if f.period and (f.date_from or f.date_to):
        raise AppError(400, "INVALID_PERIOD", "기간(period)과 날짜 직접 지정(from, to)은 함께 쓸 수 없어요")
    if f.date_from and f.date_to and f.date_from > f.date_to:
        raise AppError(400, "INVALID_PERIOD", "시작 날짜가 끝 날짜보다 늦어요")
    if f.near is None and (f.sort == "distance" or f.radius_km is not None):
        raise AppError(400, "LOCATION_REQUIRED", "거리순 정렬과 반경 검색에는 위치(lat, lng)가 필요해요")


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# BOOLEAN MODE 에서 연산자로 쓰이는 글자는 검색어에서 뺀다
_FT_SPECIAL = re.compile(r'[+\-<>()~*"@]')


def _keyword(stmt: Select, q: str) -> Select:
    """
    제목·소개 키워드 검색.
    - 두 글자 이상 단어는 ngram FULLTEXT(MATCH ... AGAINST)로 찾는다. 단어마다 필수(+)로 묶는다.
    - ngram 토큰이 두 글자라 한 글자 검색어는 LIKE 로 찾는다.
    모든 값은 바인딩 파라미터로 넘긴다 (레퍼런스 10장).
    """
    words = [w for w in _FT_SPECIAL.sub(" ", q).split() if w]
    long_words = [w for w in words if len(w) >= 2]
    if long_words:
        boolean_query = " ".join(f'+"{w}"' for w in long_words)
        stmt = stmt.where(
            text("MATCH(fairs.title, fairs.summary) AGAINST(:ftq IN BOOLEAN MODE)").bindparams(ftq=boolean_query)
        )
    for w in [w for w in words if len(w) < 2] or ([] if long_words else [q.strip()]):
        pattern = f"%{_escape_like(w)}%"
        stmt = stmt.where(or_(Fair.title.like(pattern, escape="\\"), Fair.summary.like(pattern, escape="\\")))
    return stmt


def apply_filters(stmt: Select, f: FairFilter, today: date, now_utc: datetime) -> Select:
    stmt = stmt.where(Fair.status == "published")

    if f.q:
        stmt = _keyword(stmt, f.q)

    if f.category:
        stmt = stmt.where(Fair.category_id.in_(select(Category.id).where(Category.code == f.category)))

    if f.tags:
        # 선택한 태그를 '모두' 가진 박람회 (GROUP BY + HAVING)
        having_all = (
            select(FairTag.fair_id)
            .join(Tag, Tag.id == FairTag.tag_id)
            .where(Tag.slug.in_(f.tags))
            .group_by(FairTag.fair_id)
            .having(func.count(func.distinct(Tag.slug)) == len(f.tags))
        )
        stmt = stmt.where(Fair.id.in_(having_all))

    if f.region:
        stmt = stmt.where(Fair.venue_id.in_(select(Venue.id).where(Venue.region == f.region)))

    if f.period == "this_weekend":
        stmt = stmt.where(_overlaps(*weekend_of(today)))
    elif f.period == "this_month":
        stmt = stmt.where(_overlaps(*month_of(today)))
    elif f.period == "ongoing":
        stmt = stmt.where(Fair.start_date <= today, Fair.end_date >= today)
    elif f.period == "upcoming":
        stmt = stmt.where(Fair.start_date > today)

    if f.date_from or f.date_to:
        stmt = stmt.where(_overlaps(f.date_from or date.min, f.date_to or date.max))

    if f.free:
        # 현장 또는 사전등록 무료. NULL(미확인)은 무료로 보지 않는다.
        stmt = stmt.where(or_(Fair.price_onsite == 0, Fair.price_prereg == 0))

    if f.public_only:
        # 일반인 관람 가능 = 전체 공개(public) 또는 일부 날짜 공개(partial)
        stmt = stmt.where(Fair.public_access.in_(("public", "partial")))

    if f.near and f.radius_km is not None:
        # 반경 안의 전시장. 좌표가 없는 전시장은 거리가 NULL 이라 빠진다
        within = select(Venue.id).where(_venue_distance_m(f.near) <= f.radius_km * 1000)
        stmt = stmt.where(Fair.venue_id.in_(within))

    if f.sort == "prereg_deadline":
        # 마감 임박순: 아직 마감 전인 사전등록만 (NULL 제외)
        stmt = stmt.where(Fair.prereg_end_at.is_not(None), Fair.prereg_end_at >= now_utc)

    return stmt


def bookmark_count_subquery():
    return select(Bookmark.fair_id, func.count().label("cnt")).group_by(Bookmark.fair_id).subquery("bm")


def apply_sort(stmt: Select, f: FairFilter, today: date) -> Select:
    # 모든 정렬에서 이미 끝난 행사는 맨 뒤로 보낸다. 지우지 않는 이유: 상세·북마크·지난 행사 통계에 쓴다
    ended = Fair.end_date < today
    if f.sort == "prereg_deadline":
        return stmt.order_by(Fair.prereg_end_at, Fair.id)
    if f.sort == "popular":
        bm = bookmark_count_subquery()
        return stmt.outerjoin(bm, bm.c.fair_id == Fair.id).order_by(
            ended, func.coalesce(bm.c.cnt, 0).desc(), Fair.start_date, Fair.id
        )
    if f.sort == "distance" and f.near:
        # 가까운 순. 이미 끝난 행사와 좌표가 없는 전시장은 뒤로, 같은 전시장 안에서는 개막순
        dist = _venue_distance_m(f.near)
        return stmt.join(Venue, Venue.id == Fair.venue_id).order_by(
            ended, dist.is_(None), dist, Fair.start_date, Fair.id
        )
    # 개막순: 진행 중·예정은 개막이 빠른 순, 끝난 행사는 최근에 끝난 순
    return stmt.order_by(
        ended,
        case((ended, None), else_=Fair.start_date),
        case((ended, Fair.end_date), else_=None).desc(),
        Fair.id,
    )
