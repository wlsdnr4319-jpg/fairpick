"""
참여 기능 API (2단계: F-14 관람 노트, F-15 후기, F-16 태그 투표, F-17 캘린더, F-12 수신 거부).

GET    /api/v1/fairs/calendar?month=2026-11          캘린더용 기간 목록
GET    /api/v1/fairs/{fair_id}/reviews               공개 후기
POST   /api/v1/fairs/{fair_id}/visits                관람 노트 작성 (박람회당 1개)
GET    /api/v1/me/visits                             내 관람 노트
PATCH  /api/v1/visits/{visit_id}                     관람 노트 수정 (작성자)
DELETE /api/v1/visits/{visit_id}                     관람 노트 삭제 (작성자)
PUT    /api/v1/visits/{visit_id}/like                후기 좋아요 (멱등)
DELETE /api/v1/visits/{visit_id}/like                좋아요 취소
GET    /api/v1/fairs/{fair_id}/tag-votes             투표 가능한 태그와 득표
PUT    /api/v1/fairs/{fair_id}/tag-votes/{tag_id}    태그 투표 (멱등)
DELETE /api/v1/fairs/{fair_id}/tag-votes/{tag_id}    투표 취소
POST   /api/v1/notifications/unsubscribe             알림 메일 수신 거부 (로그인 없이 토큰으로)
GET    /api/v1/fairs/{fair_id}/calendar.ics          캘린더 파일 내보내기 (F-24)

/fairs/calendar 는 /fairs/{fair_id} 보다 먼저 등록해야 한다. 이 라우터를 fairs 라우터보다 먼저 include 한다.
"""

import calendar
import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status
from sqlalchemy import delete, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession, OptionalUser
from app.core.errors import AppError
from app.core.timeutil import to_local
from app.models import Fair, FairTag, Tag, TagVote, Visit, VisitLike
from app.schemas.auth import MessageOut, UnsubscribeIn
from app.schemas.engagement import (
    CalendarItem,
    LikeOut,
    ReviewOut,
    ReviewPage,
    TagVoteOut,
    VisitIn,
    VisitOut,
    VisitPatch,
)
from app.services import fairs as fair_service
from app.services import notifications

router = APIRouter(tags=["engagement"])

FairId = Annotated[int, Path(ge=1)]
VisitId = Annotated[int, Path(ge=1)]
VOTE_THRESHOLD = 3  # 이 표 수 이상이면 태그로 반영 (레퍼런스 6장 예시 쿼리)


def _fair_or_404(db, fair_id: int) -> Fair:
    fair = fair_service.get_published_fair(db, fair_id)
    if fair is None:
        raise AppError(404, "FAIR_NOT_FOUND", "박람회를 찾을 수 없어요")
    return fair


# ---------------------------------------------------------------------------
# 캘린더
# ---------------------------------------------------------------------------


@router.get("/fairs/calendar", response_model=list[CalendarItem])
def fair_calendar(db: DbSession, month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]):
    y, m = map(int, month.split("-"))
    first, last = date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
    fairs = db.scalars(
        select(Fair)
        .where(Fair.status == "published", Fair.start_date <= last, Fair.end_date >= first)
        .options(selectinload(Fair.category), selectinload(Fair.venue))
        .order_by(Fair.start_date, Fair.id)
    ).all()
    return [
        CalendarItem(
            id=f.id,
            title=f.title,
            start_date=f.start_date,
            end_date=f.end_date,
            category=f.category.code,
            venue=f.venue.name,
        )
        for f in fairs
    ]


# ---------------------------------------------------------------------------
# 관람 노트·후기
# ---------------------------------------------------------------------------


def _like_counts(db, visit_ids: list[int]) -> dict[int, int]:
    if not visit_ids:
        return {}
    rows = db.execute(
        select(VisitLike.visit_id, func.count()).where(VisitLike.visit_id.in_(visit_ids)).group_by(VisitLike.visit_id)
    )
    return dict(rows.all())


def _visit_out(v: Visit, like_count: int) -> VisitOut:
    return VisitOut(
        id=v.id,
        fair_id=v.fair_id,
        fair_title=v.fair.title,
        visited_on=v.visited_on,
        rating=v.rating,
        memo=v.memo,
        is_public=v.is_public,
        like_count=like_count,
        created_at=to_local(v.created_at),
        updated_at=to_local(v.updated_at),
    )


def _own_visit(db, user, visit_id: int) -> Visit:
    v = db.scalar(select(Visit).where(Visit.id == visit_id).options(selectinload(Visit.fair)))
    if v is None:
        raise AppError(404, "VISIT_NOT_FOUND", "관람 노트를 찾을 수 없어요")
    if v.user_id != user.id:
        raise AppError(403, "NOT_OWNER", "내가 쓴 관람 노트만 고칠 수 있어요")
    return v


@router.get("/fairs/{fair_id}/reviews", response_model=ReviewPage)
def reviews(
    db: DbSession,
    user: OptionalUser,
    fair_id: FairId,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 10,
):
    _fair_or_404(db, fair_id)
    base = select(Visit).where(Visit.fair_id == fair_id, Visit.is_public.is_(True))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    avg, rated = db.execute(
        select(func.avg(Visit.rating), func.count(Visit.rating)).where(
            Visit.fair_id == fair_id, Visit.is_public.is_(True), Visit.rating.is_not(None)
        )
    ).one()
    visits = db.scalars(
        base.options(selectinload(Visit.user))
        .order_by(Visit.created_at.desc(), Visit.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    counts = _like_counts(db, [v.id for v in visits])
    mine = set()
    if user and visits:
        mine = set(
            db.scalars(
                select(VisitLike.visit_id).where(
                    VisitLike.user_id == user.id, VisitLike.visit_id.in_([v.id for v in visits])
                )
            )
        )
    return ReviewPage(
        items=[
            ReviewOut(
                id=v.id,
                nickname=v.user.nickname,
                visited_on=v.visited_on,
                rating=v.rating,
                memo=v.memo,
                like_count=counts.get(v.id, 0),
                liked_by_me=v.id in mine,
                is_mine=bool(user and v.user_id == user.id),
                created_at=to_local(v.created_at),
            )
            for v in visits
        ],
        total=total,
        page=page,
        size=size,
        rating_avg=round(float(avg), 1) if avg is not None else None,
        rating_count=rated,
    )


@router.post("/fairs/{fair_id}/visits", response_model=VisitOut, status_code=status.HTTP_201_CREATED)
def create_visit(db: DbSession, user: CurrentUser, fair_id: FairId, body: VisitIn):
    _fair_or_404(db, fair_id)
    visit = Visit(user_id=user.id, fair_id=fair_id, **body.model_dump())
    db.add(visit)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "VISIT_EXISTS", "이 박람회의 관람 노트가 이미 있어요. 기존 노트를 고쳐 주세요") from None
    db.refresh(visit, ["fair"])
    return _visit_out(visit, 0)


@router.get("/me/visits", response_model=list[VisitOut])
def my_visits(db: DbSession, user: CurrentUser):
    visits = db.scalars(
        select(Visit)
        .where(Visit.user_id == user.id)
        .options(selectinload(Visit.fair))
        .order_by(Visit.visited_on.desc(), Visit.id.desc())
    ).all()
    counts = _like_counts(db, [v.id for v in visits])
    return [_visit_out(v, counts.get(v.id, 0)) for v in visits]


@router.patch("/visits/{visit_id}", response_model=VisitOut)
def update_visit(db: DbSession, user: CurrentUser, visit_id: VisitId, body: VisitPatch):
    v = _own_visit(db, user, visit_id)
    for k, val in body.model_dump(exclude_unset=True).items():
        if k == "is_public" and val is None:
            continue
        setattr(v, k, val)
    db.commit()
    return _visit_out(v, _like_counts(db, [v.id]).get(v.id, 0))


@router.delete("/visits/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visit(db: DbSession, user: CurrentUser, visit_id: VisitId):
    db.delete(_own_visit(db, user, visit_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _public_visit(db, visit_id: int) -> Visit:
    v = db.get(Visit, visit_id)
    if v is None or not v.is_public:
        raise AppError(404, "VISIT_NOT_FOUND", "후기를 찾을 수 없어요")
    return v


@router.put("/visits/{visit_id}/like", response_model=LikeOut)
def like(db: DbSession, user: CurrentUser, visit_id: VisitId):
    _public_visit(db, visit_id)
    db.execute(insert(VisitLike).prefix_with("IGNORE").values(user_id=user.id, visit_id=visit_id))
    db.commit()
    return LikeOut(visit_id=visit_id, liked=True, like_count=_like_counts(db, [visit_id]).get(visit_id, 0))


@router.delete("/visits/{visit_id}/like", response_model=LikeOut)
def unlike(db: DbSession, user: CurrentUser, visit_id: VisitId):
    db.execute(delete(VisitLike).where(VisitLike.user_id == user.id, VisitLike.visit_id == visit_id))
    db.commit()
    return LikeOut(visit_id=visit_id, liked=False, like_count=_like_counts(db, [visit_id]).get(visit_id, 0))


# ---------------------------------------------------------------------------
# 태그 투표 (2단계, 3표 이상이면 태그로 추가)
# ---------------------------------------------------------------------------


def apply_tag_votes(db, fair_id: int, tag_id: int) -> None:
    """득표가 기준 이상이면 fair_tags 에 source='vote' 로 붙이고, 기준 아래로 내려가면 투표로 붙은 태그만 뗀다."""
    count = db.scalar(select(func.count()).where(TagVote.fair_id == fair_id, TagVote.tag_id == tag_id)) or 0
    if count >= VOTE_THRESHOLD:
        db.execute(insert(FairTag).prefix_with("IGNORE").values(fair_id=fair_id, tag_id=tag_id, source="vote"))
    else:
        db.execute(
            delete(FairTag).where(FairTag.fair_id == fair_id, FairTag.tag_id == tag_id, FairTag.source == "vote")
        )


def _vote_rows(db, fair_id: int, user) -> list[TagVoteOut]:
    tags = db.scalars(select(Tag).where(Tag.is_votable.is_(True)).order_by(Tag.id)).all()
    counts = dict(
        db.execute(
            select(TagVote.tag_id, func.count()).where(TagVote.fair_id == fair_id).group_by(TagVote.tag_id)
        ).all()
    )
    applied = set(db.scalars(select(FairTag.tag_id).where(FairTag.fair_id == fair_id)))
    mine = set()
    if user:
        mine = set(db.scalars(select(TagVote.tag_id).where(TagVote.fair_id == fair_id, TagVote.user_id == user.id)))
    return [
        TagVoteOut(
            tag_id=t.id,
            slug=t.slug,
            name=t.name,
            vote_count=counts.get(t.id, 0),
            voted=t.id in mine,
            applied=t.id in applied,
        )
        for t in tags
    ]


@router.get("/fairs/{fair_id}/tag-votes", response_model=list[TagVoteOut])
def tag_votes(db: DbSession, user: OptionalUser, fair_id: FairId):
    _fair_or_404(db, fair_id)
    return _vote_rows(db, fair_id, user)


def _votable(db, tag_id: int) -> Tag:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise AppError(404, "TAG_NOT_FOUND", "태그를 찾을 수 없어요")
    if not tag.is_votable:
        # 시식·체험·반려동물 동반 같은 사실 정보는 투표로 바꾸지 않는다
        raise AppError(422, "TAG_NOT_VOTABLE", "이 태그는 투표할 수 없어요")
    return tag


@router.put("/fairs/{fair_id}/tag-votes/{tag_id}", response_model=list[TagVoteOut])
def vote(db: DbSession, user: CurrentUser, fair_id: FairId, tag_id: Annotated[int, Path(ge=1)]):
    _fair_or_404(db, fair_id)
    _votable(db, tag_id)
    db.execute(insert(TagVote).prefix_with("IGNORE").values(user_id=user.id, fair_id=fair_id, tag_id=tag_id))
    apply_tag_votes(db, fair_id, tag_id)
    db.commit()
    return _vote_rows(db, fair_id, user)


@router.delete("/fairs/{fair_id}/tag-votes/{tag_id}", response_model=list[TagVoteOut])
def unvote(db: DbSession, user: CurrentUser, fair_id: FairId, tag_id: Annotated[int, Path(ge=1)]):
    _fair_or_404(db, fair_id)
    _votable(db, tag_id)
    db.execute(delete(TagVote).where(TagVote.user_id == user.id, TagVote.fair_id == fair_id, TagVote.tag_id == tag_id))
    apply_tag_votes(db, fair_id, tag_id)
    db.commit()
    return _vote_rows(db, fair_id, user)


# ---------------------------------------------------------------------------
# 수신 거부
# ---------------------------------------------------------------------------


@router.post("/notifications/unsubscribe", response_model=MessageOut)
def unsubscribe(db: DbSession, body: UnsubscribeIn):
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", body.token) or not notifications.unsubscribe(db, body.token):
        raise AppError(404, "INVALID_UNSUBSCRIBE_TOKEN", "수신 거부 링크가 올바르지 않아요")
    return MessageOut(message="알림 메일 수신을 거부했어요. 마이페이지에서 다시 켤 수 있어요")


# ---------------------------------------------------------------------------
# 캘린더 파일 내보내기 (F-24)
# ---------------------------------------------------------------------------


_ICS_ESCAPES = {"\\": "\\\\", ";": "\\;", ",": "\\,", "\n": "\\n"}


def _ics_escape(value: str) -> str:
    """iCalendar TEXT 값 이스케이프: 역슬래시, 세미콜론, 쉼표, 줄바꿈"""
    return "".join(_ICS_ESCAPES.get(ch, ch) for ch in value)


@router.get("/fairs/{fair_id}/calendar.ics")
def fair_ics(db: DbSession, fair_id: FairId):
    from datetime import UTC, datetime, timedelta

    from app.core.config import get_settings

    f = _fair_or_404(db, fair_id)
    base = get_settings().app_base_url.rstrip("/")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    location = f"{f.venue.name} {f.hall}".strip() if f.hall else f.venue.name
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FairPick//KO",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:fair-{f.id}@fairpick",
        f"DTSTAMP:{stamp}",
        # 종일 일정: 끝 날짜는 다음 날로 적는다 (iCalendar 규칙)
        f"DTSTART;VALUE=DATE:{f.start_date:%Y%m%d}",
        f"DTEND;VALUE=DATE:{f.end_date + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{_ics_escape(f.title)}",
        f"LOCATION:{_ics_escape(location)}",
        f"URL:{base}/fairs/{f.id}",
        f"DESCRIPTION:{_ics_escape('일정과 입장 조건은 주최 측 공식 사이트에서 최종 확인하세요.')}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return Response(
        content="\r\n".join(lines) + "\r\n",  # iCalendar 는 줄 끝이 CRLF
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="fairpick-{f.id}.ics"'},
    )
