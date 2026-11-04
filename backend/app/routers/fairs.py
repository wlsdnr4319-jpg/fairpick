"""
박람회 API (레퍼런스 7장 '박람회와 참여').

GET /api/v1/fairs              목록 (2주차: 공개 박람회 개막순 + 페이지네이션, 3주차: 필터·검색·정렬)
GET /api/v1/fairs/{fair_id}    상세

/fairs/calendar 같은 고정 경로를 추가할 때는 /fairs/{fair_id} 보다 위에 선언한다.
순서가 바뀌면 FastAPI 가 'calendar' 를 fair_id 로 해석해 422 를 낸다.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.deps import get_today
from app.core.errors import AppError
from app.db.session import get_db
from app.schemas.fair import FairCard, FairDetail, Page
from app.services import fairs as fair_service

router = APIRouter(prefix="/fairs", tags=["fairs"])

DbSession = Annotated[Session, Depends(get_db)]
Today = Annotated[date, Depends(get_today)]


@router.get("", response_model=Page[FairCard])
def list_fairs(
    db: DbSession,
    today: Today,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,  # size 는 최대 50
):
    fairs, total = fair_service.list_fairs(db, page=page, size=size)
    return Page[FairCard](
        items=[fair_service.to_card(f, today) for f in fairs],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{fair_id}", response_model=FairDetail)
def get_fair(db: DbSession, today: Today, fair_id: Annotated[int, Path(ge=1)]):
    fair = fair_service.get_published_fair(db, fair_id)
    if fair is None:
        raise AppError(404, "FAIR_NOT_FOUND", "박람회를 찾을 수 없어요")

    return fair_service.to_detail(
        fair,
        today,
        bookmark_count=fair_service.count_bookmarks(db, fair.id),
        is_bookmarked=False,  # 4주차: 로그인 사용자면 북마크 여부를 채운다
    )
