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
def update_fair(
    _: CurrentAdmin, db: DbSession, now: Now, fair_id: Annotated[int, Path(ge=1)], body: FairUpdate
):
    admin_fairs.update(db, fair_id, body, now)
    db.commit()
    return admin_fairs.to_admin(db, fair_id)
