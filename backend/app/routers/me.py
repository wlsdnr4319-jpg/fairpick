"""
내 정보 API.

GET    /api/v1/me             내 정보
DELETE /api/v1/me             회원 탈퇴. 북마크·토큰은 ON DELETE CASCADE 로 함께 지운다 (레퍼런스 10장)
GET    /api/v1/me/bookmarks   내 북마크 목록 (최근 북마크 순)
"""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, Today
from app.models import Bookmark, Fair
from app.routers.auth import clear_refresh_cookie
from app.schemas.auth import NotificationSettingsIO, UserOut
from app.schemas.fair import FairCard, Page
from app.services import fairs as fair_service
from app.services.notifications import ensure_settings

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def withdraw(user: CurrentUser, db: DbSession, response: Response):
    db.delete(user)
    db.commit()
    clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/bookmarks", response_model=Page[FairCard])
def my_bookmarks(
    user: CurrentUser,
    db: DbSession,
    today: Today,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
):
    base = (
        select(Fair)
        .join(Bookmark, Bookmark.fair_id == Fair.id)
        .where(Bookmark.user_id == user.id, Fair.status == "published")
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    fairs = db.scalars(
        base.options(*fair_service.LOAD_RELATIONS)
        .order_by(Bookmark.created_at.desc(), Fair.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return Page[FairCard](
        items=[fair_service.to_card(f, today, is_bookmarked=True) for f in fairs],
        total=total,
        page=page,
        size=size,
    )


@router.get("/notification-settings", response_model=NotificationSettingsIO)
def get_notification_settings(user: CurrentUser, db: DbSession):
    s = ensure_settings(db, user.id)
    db.commit()
    return s


@router.put("/notification-settings", response_model=NotificationSettingsIO)
def put_notification_settings(user: CurrentUser, db: DbSession, body: NotificationSettingsIO):
    s = ensure_settings(db, user.id)
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    return s
