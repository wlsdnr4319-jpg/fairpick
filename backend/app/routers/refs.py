"""필터용 참조 데이터: GET /api/v1/categories, /tags, /venues (레퍼런스 7장)."""

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import DbSession
from app.models import Category, Tag, Venue
from app.schemas.fair import RefCategory, RefTag, RefVenue

router = APIRouter(tags=["refs"])


@router.get("/categories", response_model=list[RefCategory])
def categories(db: DbSession):
    return [
        RefCategory(code=c.code, name=c.name)
        for c in db.scalars(select(Category).order_by(Category.sort_order, Category.id))
    ]


@router.get("/tags", response_model=list[RefTag])
def tags(db: DbSession):
    return [RefTag(slug=t.slug, name=t.name, is_votable=t.is_votable) for t in db.scalars(select(Tag).order_by(Tag.id))]


@router.get("/venues", response_model=list[RefVenue])
def venues(db: DbSession):
    return [
        RefVenue(id=v.id, name=v.name, region=v.region, address=v.address)
        for v in db.scalars(select(Venue).order_by(Venue.id))
    ]
