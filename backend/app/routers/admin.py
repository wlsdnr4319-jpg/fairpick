"""
관리자 API (레퍼런스 7장 '관리자'). role = 'admin' 이 아니면 403 ADMIN_ONLY.

GET   /api/v1/admin/fairs             전체 박람회(초안·공개·숨김) 목록
GET   /api/v1/admin/fairs/{fair_id}   수정 화면용 상세
POST  /api/v1/admin/fairs             등록
PATCH /api/v1/admin/fairs/{fair_id}   수정, 공개·숨김

수집 검수(crawled-items) API 는 app/routers/admin_crawl.py 에 있다.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.core.deps import CurrentAdmin, DbSession, Now
from app.schemas.admin import AdminFair, AdminFairRow, FairCreate, FairStatus, FairUpdate
from app.schemas.fair import Page
from app.services import admin_fairs

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/fairs", response_model=Page[AdminFairRow])
def list_fairs(
    _: CurrentAdmin,
    db: DbSession,
    fair_status: Annotated[FairStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 50,
):
    rows, total = admin_fairs.list_all(db, status=fair_status, q=q, page=page, size=size)
    return Page[AdminFairRow](items=rows, total=total, page=page, size=size)


@router.get("/fairs/{fair_id}", response_model=AdminFair)
def get_fair(_: CurrentAdmin, db: DbSession, fair_id: Annotated[int, Path(ge=1)]):
    return admin_fairs.to_admin(db, fair_id)


@router.post("/fairs", response_model=AdminFair, status_code=status.HTTP_201_CREATED)
def create_fair(_: CurrentAdmin, db: DbSession, now: Now, body: FairCreate):
    fair = admin_fairs.create(db, body, now)
    db.commit()
    return admin_fairs.to_admin(db, fair.id)


@router.patch("/fairs/{fair_id}", response_model=AdminFair)
def update_fair(admin: CurrentAdmin, db: DbSession, now: Now, fair_id: Annotated[int, Path(ge=1)], body: FairUpdate):
    admin_fairs.update(db, fair_id, body, now, actor_id=admin.id)
    db.commit()
    return admin_fairs.to_admin(db, fair_id)


# ---------------------------------------------------------------------------
# 엑셀 내보내기 (F-23)
# ---------------------------------------------------------------------------

_EXPORT_COLUMNS = [
    ("id", "ID"),
    ("status", "상태"),
    ("title", "박람회명"),
    ("category", "카테고리"),
    ("venue", "전시장"),
    ("hall", "홀"),
    ("start_date", "시작일"),
    ("end_date", "종료일"),
    ("public_access", "일반인 관람"),
    ("price_onsite", "현장 입장료"),
    ("price_prereg", "사전등록 입장료"),
    ("prereg_end_at", "사전등록 마감(KST)"),
    ("official_url", "공식 사이트"),
    ("source", "출처"),
    ("verified_at", "정보 확인일(KST)"),
    ("bookmarks", "북마크 수"),
]


@router.get("/export/fairs.xlsx")
def export_fairs(_: CurrentAdmin, db: DbSession):
    from io import BytesIO

    from fastapi.responses import StreamingResponse
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    from app.core.timeutil import to_local
    from app.models import Bookmark, Fair

    counts = dict(db.execute(select(Bookmark.fair_id, func.count()).group_by(Bookmark.fair_id)).all())
    fairs = db.scalars(
        select(Fair).options(selectinload(Fair.category), selectinload(Fair.venue)).order_by(Fair.start_date, Fair.id)
    ).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "박람회"
    ws.append([label for _, label in _EXPORT_COLUMNS])
    for f in fairs:
        local = lambda dt: to_local(dt).replace(tzinfo=None) if dt else None  # noqa: E731  엑셀은 시간대를 모른다
        ws.append(
            [
                f.id,
                f.status,
                f.title,
                f.category.name,
                f.venue.name,
                f.hall,
                f.start_date,
                f.end_date,
                f.public_access,
                f.price_onsite,
                f.price_prereg,
                local(f.prereg_end_at),
                f.official_url,
                f.source,
                local(f.verified_at),
                counts.get(f.id, 0),
            ]
        )
    ws.freeze_panes = "A2"
    for i, (key, _) in enumerate(_EXPORT_COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = {"title": 40, "official_url": 40}.get(key, 14)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="fairpick-fairs.xlsx"'},
    )
