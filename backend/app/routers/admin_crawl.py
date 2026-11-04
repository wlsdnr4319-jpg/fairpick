"""
수집 검수 관리자 API (레퍼런스 7장 '관리자', F-09·F-10·F-18).

GET  /api/v1/admin/crawled-items?review_status=pending   검수 큐 (병합 후보 포함)
POST /api/v1/admin/crawled-items/{item_id}/approve       승인해 새 박람회 생성
POST /api/v1/admin/crawled-items/{item_id}/merge         기존 박람회에 병합 (body: fair_id)
POST /api/v1/admin/crawled-items/{item_id}/reject        반려
GET  /api/v1/admin/crawl-sources                         수집 소스
POST /api/v1/admin/crawl-sources/{source_id}/run         수동 수집 실행
GET  /api/v1/admin/crawl-runs                            수집 실행 이력
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentAdmin, DbSession, Now, Today
from app.core.errors import AppError
from app.core.timeutil import to_local
from app.models import CrawledItem, CrawlRun, CrawlSource, Fair, Venue
from app.schemas.admin import AdminFair
from app.schemas.crawl import ApproveIn, CrawledItemOut, CrawlRunOut, CrawlSourceOut, MergeCandidate, MergeIn
from app.schemas.fair import Page
from app.services import admin_fairs
from app.services.crawl import merge_candidates, run_source

router = APIRouter(prefix="/admin", tags=["admin-crawl"])
ItemId = Annotated[int, Path(ge=1)]


def _item_out(db, item: CrawledItem, with_candidates: bool = True) -> CrawledItemOut:
    venue = db.get(Venue, item.parsed_venue_id) if item.parsed_venue_id else None
    candidates = []
    if with_candidates and item.review_status == "pending":
        candidates = [
            MergeCandidate(
                fair_id=f.id,
                title=f.title,
                start_date=f.start_date,
                end_date=f.end_date,
                similarity=round(s, 2),
            )
            for f, s in merge_candidates(db, item)
        ]
    return CrawledItemOut(
        id=item.id,
        source=item.source.parser_key,
        external_id=item.external_id,
        raw_title=item.raw_title,
        raw_period=item.raw_period,
        raw_venue=item.raw_venue,
        detail_url=item.detail_url,
        raw_payload=item.raw_payload,
        parsed_start_date=item.parsed_start_date,
        parsed_end_date=item.parsed_end_date,
        parsed_venue_id=item.parsed_venue_id,
        parsed_venue_name=venue.name if venue else None,
        change_status=item.change_status,
        review_status=item.review_status,
        fair_id=item.fair_id,
        first_seen_at=to_local(item.first_seen_at),
        last_seen_at=to_local(item.last_seen_at),
        merge_candidates=candidates,
    )


def _pending_item(db, item_id: int) -> CrawledItem:
    item = db.scalar(select(CrawledItem).where(CrawledItem.id == item_id).options(selectinload(CrawledItem.source)))
    if item is None:
        raise AppError(404, "CRAWLED_ITEM_NOT_FOUND", "수집 항목을 찾을 수 없어요")
    if item.review_status != "pending":
        raise AppError(409, "ALREADY_REVIEWED", "이미 검수한 항목이에요")
    return item


@router.get("/crawled-items", response_model=Page[CrawledItemOut])
def list_items(
    _: CurrentAdmin,
    db: DbSession,
    review_status: Literal["pending", "approved", "rejected", "merged"] | None = "pending",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    stmt = select(CrawledItem)
    if review_status:
        stmt = stmt.where(CrawledItem.review_status == review_status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.options(selectinload(CrawledItem.source))
        .order_by(CrawledItem.parsed_start_date.is_(None), CrawledItem.parsed_start_date, CrawledItem.id)
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return Page[CrawledItemOut](items=[_item_out(db, i) for i in items], total=total, page=page, size=size)


@router.post("/crawled-items/{item_id}/approve", response_model=AdminFair)
def approve(_: CurrentAdmin, db: DbSession, now: Now, item_id: ItemId, body: ApproveIn | None = None):
    item = _pending_item(db, item_id)
    if item.fair_id is not None:
        # 이미 박람회와 연결된 항목이 바뀐 경우(changed): 관리자가 박람회를 직접 고친 뒤 확인만 한다
        item.review_status = "approved"
        db.commit()
        return admin_fairs.to_admin(db, item.fair_id)
    if body is None:
        raise AppError(422, "VALIDATION_ERROR", "새 박람회로 승인하려면 박람회 정보가 필요해요")
    fair = admin_fairs.create(db, body, now)
    fair.source = "crawler"
    item.fair_id = fair.id
    item.review_status = "approved"
    db.commit()
    return admin_fairs.to_admin(db, fair.id)


@router.post("/crawled-items/{item_id}/merge", response_model=CrawledItemOut)
def merge(_: CurrentAdmin, db: DbSession, item_id: ItemId, body: MergeIn):
    item = _pending_item(db, item_id)
    if db.get(Fair, body.fair_id) is None:
        raise AppError(404, "FAIR_NOT_FOUND", "박람회를 찾을 수 없어요")
    item.fair_id = body.fair_id
    item.review_status = "merged"
    db.commit()
    return _item_out(db, item, with_candidates=False)


@router.post("/crawled-items/{item_id}/reject", response_model=CrawledItemOut)
def reject(_: CurrentAdmin, db: DbSession, item_id: ItemId):
    item = _pending_item(db, item_id)
    item.review_status = "rejected"
    db.commit()
    return _item_out(db, item, with_candidates=False)


@router.get("/crawl-sources", response_model=list[CrawlSourceOut])
def list_sources(_: CurrentAdmin, db: DbSession):
    out = []
    for s in db.scalars(select(CrawlSource).options(selectinload(CrawlSource.runs)).order_by(CrawlSource.id)):
        last = max(s.runs, key=lambda r: r.started_at, default=None)
        venue = db.get(Venue, s.venue_id)
        out.append(
            CrawlSourceOut(
                id=s.id,
                parser_key=s.parser_key,
                venue=venue.name if venue else "",
                list_url=s.list_url,
                is_active=s.is_active,
                policy_checked_at=to_local(s.policy_checked_at),
                policy_note=s.policy_note,
                last_run_status=last.status if last else None,
                last_run_at=to_local(last.started_at) if last else None,
            )
        )
    return out


@router.post("/crawl-sources/{source_id}/run", response_model=CrawlRunOut)
def run_now(_: CurrentAdmin, db: DbSession, today: Today, now: Now, source_id: Annotated[int, Path(ge=1)]):
    source = db.get(CrawlSource, source_id)
    if source is None:
        raise AppError(404, "CRAWL_SOURCE_NOT_FOUND", "수집 소스를 찾을 수 없어요")
    run = run_source(db, source, today=today, now=now)
    return _run_out(run, source.parser_key)


@router.get("/crawl-runs", response_model=Page[CrawlRunOut])
def list_runs(
    _: CurrentAdmin,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 30,
):
    total = db.scalar(select(func.count()).select_from(CrawlRun)) or 0
    runs = db.scalars(
        select(CrawlRun)
        .options(selectinload(CrawlRun.source))
        .order_by(CrawlRun.started_at.desc(), CrawlRun.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return Page[CrawlRunOut](items=[_run_out(r, r.source.parser_key) for r in runs], total=total, page=page, size=size)


def _run_out(run: CrawlRun, key: str) -> CrawlRunOut:
    return CrawlRunOut(
        id=run.id,
        source=key,
        status=run.status,
        found_count=run.found_count,
        new_count=run.new_count,
        changed_count=run.changed_count,
        error_message=run.error_message,
        started_at=to_local(run.started_at),
        finished_at=to_local(run.finished_at),
    )
