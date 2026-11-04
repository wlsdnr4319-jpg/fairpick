"""
박람회 API (레퍼런스 7장 '박람회와 참여').

GET    /api/v1/fairs                     목록·필터·검색·정렬 (로그인 시 북마크 여부 포함)
GET    /api/v1/fairs/{fair_id}           상세
PUT    /api/v1/fairs/{fair_id}/bookmark  북마크 추가 (두 번 해도 결과가 같다)
DELETE /api/v1/fairs/{fair_id}/bookmark  북마크 해제

/fairs/calendar 같은 고정 경로를 추가할 때는 /fairs/{fair_id} 보다 위에 선언한다.
순서가 바뀌면 FastAPI 가 'calendar' 를 fair_id 로 해석해 422 를 낸다.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession, Now, OptionalUser, Today
from app.core.errors import AppError
from app.models import Bookmark, Fair
from app.schemas.auth import BookmarkOut
from app.schemas.fair import FairCard, FairDetail, Page
from app.services import fairs as fair_service
from app.services.fair_query import FairFilter, Period, Sort, parse_tags, validate

router = APIRouter(prefix="/fairs", tags=["fairs"])

FairId = Annotated[int, Path(ge=1)]


@router.get("", response_model=Page[FairCard])
def list_fairs(
    db: DbSession,
    today: Today,
    now: Now,
    user: OptionalUser,
    q: Annotated[str | None, Query(max_length=100, description="제목·소개 키워드")] = None,
    category: Annotated[str | None, Query(description="카테고리 code. 예: food")] = None,
    tags: Annotated[str | None, Query(description="태그 slug, 쉼표로 여러 개. 모두 포함")] = None,
    region: Annotated[str | None, Query(description="시·도. 예: 서울")] = None,
    period: Annotated[Period | None, Query()] = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    free: bool = False,
    public_only: bool = False,
    sort: Sort = "start_date",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,  # size 는 최대 50
):
    f = FairFilter(
        q=q or None,
        category=category or None,
        tags=parse_tags(tags),
        region=region or None,
        period=period,
        date_from=date_from,
        date_to=date_to,
        free=free,
        public_only=public_only,
        sort=sort,
    )
    validate(f)
    fairs, total = fair_service.list_fairs(db, f, today=today, now_utc=now, page=page, size=size)
    marked = fair_service.bookmarked_ids(db, user.id if user else None, [x.id for x in fairs])
    return Page[FairCard](
        items=[fair_service.to_card(x, today, is_bookmarked=x.id in marked) for x in fairs],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{fair_id}", response_model=FairDetail)
def get_fair(db: DbSession, today: Today, user: OptionalUser, fair_id: FairId):
    fair = _published_or_404(db, fair_id)
    return fair_service.to_detail(
        fair,
        today,
        bookmark_count=fair_service.count_bookmarks(db, fair.id),
        is_bookmarked=bool(fair_service.bookmarked_ids(db, user.id if user else None, [fair.id])),
    )


@router.put("/{fair_id}/bookmark", response_model=BookmarkOut)
def add_bookmark(db: DbSession, user: CurrentUser, fair_id: FairId):
    _published_or_404(db, fair_id)
    exists = db.scalar(select(Bookmark).where(Bookmark.user_id == user.id, Bookmark.fair_id == fair_id))
    if exists is None:
        db.add(Bookmark(user_id=user.id, fair_id=fair_id))
        try:
            db.commit()
        except IntegrityError:  # 같은 요청이 동시에 두 번 온 경우. PK 가 중복을 막는다
            db.rollback()
    return BookmarkOut(
        fair_id=fair_id, bookmarked=True, bookmark_count=fair_service.count_bookmarks(db, fair_id)
    )


@router.delete("/{fair_id}/bookmark", response_model=BookmarkOut)
def remove_bookmark(db: DbSession, user: CurrentUser, fair_id: FairId):
    row = db.scalar(select(Bookmark).where(Bookmark.user_id == user.id, Bookmark.fair_id == fair_id))
    if row is not None:
        db.delete(row)
        db.commit()
    return BookmarkOut(
        fair_id=fair_id, bookmarked=False, bookmark_count=fair_service.count_bookmarks(db, fair_id)
    )


def _published_or_404(db, fair_id: int) -> Fair:
    fair = fair_service.get_published_fair(db, fair_id)
    if fair is None:
        raise AppError(404, "FAIR_NOT_FOUND", "박람회를 찾을 수 없어요")
    return fair
