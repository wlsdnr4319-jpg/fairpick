"""관리자 박람회 등록·수정·숨김 (F-08). 박람회는 지우지 않고 status='hidden' 으로 숨긴다."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.timeutil import to_local, to_utc_naive
from app.models import Category, Fair, FairTag, Tag, Venue
from app.schemas.admin import AdminFair, AdminFairRow, FairCreate, FairUpdate

_URL_FIELDS = ("prereg_url", "official_url", "image_url")
_DT_FIELDS = ("prereg_start_at", "prereg_end_at")
_META = {"category", "tags", "verified"}


def _load(db: Session, fair_id: int) -> Fair:
    fair = db.scalar(
        select(Fair)
        .where(Fair.id == fair_id)
        .options(
            selectinload(Fair.category),
            selectinload(Fair.venue),
            selectinload(Fair.fair_tags).selectinload(FairTag.tag),
        )
    )
    if fair is None:
        raise AppError(404, "FAIR_NOT_FOUND", "박람회를 찾을 수 없어요")
    return fair


def _category_id(db: Session, code: str) -> int:
    cid = db.scalar(select(Category.id).where(Category.code == code))
    if cid is None:
        raise AppError(422, "VALIDATION_ERROR", f"없는 카테고리예요 ({code})")
    return cid


def _check_venue(db: Session, venue_id: int) -> None:
    if db.get(Venue, venue_id) is None:
        raise AppError(422, "VALIDATION_ERROR", f"없는 전시장이에요 ({venue_id})")


def _set_tags(db: Session, fair: Fair, slugs: list[str]) -> None:
    slugs = list(dict.fromkeys(slugs))
    tags = {t.slug: t for t in db.scalars(select(Tag).where(Tag.slug.in_(slugs)))} if slugs else {}
    missing = [s for s in slugs if s not in tags]
    if missing:
        raise AppError(422, "VALIDATION_ERROR", f"없는 태그예요 ({', '.join(missing)})")
    wanted = {tags[s].id for s in slugs}
    # 관리자 태그만 바꾼다. 사용자 투표로 붙은 태그(source='vote')는 그대로 둔다
    for ft in list(fair.fair_tags):
        if ft.source == "admin" and ft.tag_id not in wanted:
            db.delete(ft)
    existing = {ft.tag_id for ft in fair.fair_tags}
    for tag_id in wanted - existing:
        db.add(FairTag(fair_id=fair.id, tag_id=tag_id, source="admin"))


def _normalize(field: str, value):
    if value is None:
        return None
    if field in _URL_FIELDS:
        return str(value)
    if field in _DT_FIELDS:
        return to_utc_naive(value)
    return value


def create(db: Session, body: FairCreate, now: datetime) -> Fair:
    _check_venue(db, body.venue_id)
    fair = Fair(source="manual", category_id=_category_id(db, body.category))
    for field, value in body.model_dump(exclude=_META).items():
        setattr(fair, field, _normalize(field, value))
    if body.verified:
        fair.verified_at = now
    db.add(fair)
    db.flush()
    db.refresh(fair, ["fair_tags"])
    _set_tags(db, fair, body.tags)
    db.flush()
    return fair


def update(db: Session, fair_id: int, body: FairUpdate, now: datetime) -> Fair:
    fair = _load(db, fair_id)
    data = body.model_dump(exclude_unset=True)

    if "category" in data:
        fair.category_id = _category_id(db, data["category"])
    if data.get("venue_id") is not None:
        _check_venue(db, data["venue_id"])
    for field, value in data.items():
        if field in _META:
            continue
        if field in ("title", "venue_id", "start_date", "end_date", "public_access", "status") and value is None:
            raise AppError(422, "VALIDATION_ERROR", f"{field} 는 비울 수 없어요")
        setattr(fair, field, _normalize(field, value))

    if fair.end_date < fair.start_date:
        raise AppError(422, "VALIDATION_ERROR", "끝 날짜가 시작 날짜보다 빨라요")
    if "tags" in data and data["tags"] is not None:
        _set_tags(db, fair, data["tags"])
    if data.get("verified"):
        fair.verified_at = now
    db.flush()
    return fair


def list_all(db: Session, *, status: str | None, q: str | None, page: int, size: int) -> tuple[list[AdminFairRow], int]:
    stmt = select(Fair)
    if status:
        stmt = stmt.where(Fair.status == status)
    if q:
        stmt = stmt.where(Fair.title.like(f"%{q.replace('%', '').replace('_', '')}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(Fair.category), selectinload(Fair.venue))
        .order_by(Fair.updated_at.desc(), Fair.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return [
        AdminFairRow(
            id=f.id,
            title=f.title,
            status=f.status,
            category=f.category.code,
            venue=f.venue.name,
            start_date=f.start_date,
            end_date=f.end_date,
            source=f.source,
            verified_at=to_local(f.verified_at),
            updated_at=to_local(f.updated_at),
        )
        for f in rows
    ], total


def to_admin(db: Session, fair_id: int) -> AdminFair:
    db.expire_all()  # 방금 바꾼 태그·수정 시각을 다시 읽는다
    f = _load(db, fair_id)
    return AdminFair(
        id=f.id,
        title=f.title,
        category=f.category.code,
        venue_id=f.venue_id,
        hall=f.hall,
        start_date=f.start_date,
        end_date=f.end_date,
        open_time=f.open_time,
        close_time=f.close_time,
        hours_note=f.hours_note,
        public_access=f.public_access,
        access_note=f.access_note,
        price_onsite=f.price_onsite,
        price_prereg=f.price_prereg,
        prereg_start_at=to_local(f.prereg_start_at),
        prereg_end_at=to_local(f.prereg_end_at),
        prereg_url=f.prereg_url,
        official_url=f.official_url,
        summary=f.summary,
        visit_tip=f.visit_tip,
        image_url=f.image_url,
        status=f.status,
        tags=sorted(ft.tag.slug for ft in f.fair_tags),
        source=f.source,
        verified_at=to_local(f.verified_at),
        created_at=to_local(f.created_at),
        updated_at=to_local(f.updated_at),
    )
