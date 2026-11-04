"""
통계 리포트 API (레퍼런스 12장, F-19). '언제, 어디서, 어떤 박람회가 많이 열리는가'.

GET /api/v1/stats/monthly?year=2026   월별·카테고리별 개최 수
GET /api/v1/stats/categories          카테고리별 개최 수, 평균 기간, 무료 비율
GET /api/v1/stats/venues              전시장별 개최 수와 가장 많은 카테고리

공개(published)와 숨김(hidden) 박람회를 함께 센다. 지난 행사를 hidden 으로 넣어 분석에만 쓰기 때문이다.
초안(draft)은 검수 전이라 뺀다.
"""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select

from app.core.deps import DbSession
from app.models import Category, Fair, Venue

router = APIRouter(prefix="/stats", tags=["stats"])

COUNTED = ("published", "hidden")
_days = func.datediff(Fair.end_date, Fair.start_date) + 1
_free = case(((Fair.price_onsite == 0) | (Fair.price_prereg == 0), 1), else_=0)


class MonthRow(BaseModel):
    month: str  # YYYY-MM
    total: int
    by_category: dict[str, int]


class CategoryRow(BaseModel):
    code: str
    name: str
    count: int
    avg_days: float
    free_ratio: float  # 현장 또는 사전등록 무료 비율 (0~1)


class VenueRow(BaseModel):
    venue: str
    region: str
    count: int
    top_category: str | None


class Overview(BaseModel):
    total: int
    free_ratio: float
    avg_days: float


@router.get("/overview", response_model=Overview)
def overview(db: DbSession):
    total, free, avg = db.execute(
        select(func.count(), func.coalesce(func.sum(_free), 0), func.coalesce(func.avg(_days), 0)).where(
            Fair.status.in_(COUNTED)
        )
    ).one()
    return Overview(total=total, free_ratio=round(free / total, 3) if total else 0.0, avg_days=round(float(avg), 1))


@router.get("/monthly", response_model=list[MonthRow])
def monthly(db: DbSession, year: Annotated[int, Query(ge=2000, le=2100)]):
    month = func.date_format(Fair.start_date, "%Y-%m")
    rows = db.execute(
        select(month.label("m"), Category.code, func.count())
        .join(Category, Category.id == Fair.category_id)
        .where(Fair.status.in_(COUNTED), func.year(Fair.start_date) == year)
        .group_by("m", Category.code)
    ).all()
    out = {f"{year}-{m:02d}": MonthRow(month=f"{year}-{m:02d}", total=0, by_category={}) for m in range(1, 13)}
    for m, code, cnt in rows:
        out[m].by_category[code] = cnt
        out[m].total += cnt
    return list(out.values())


@router.get("/categories", response_model=list[CategoryRow])
def categories(db: DbSession):
    rows = db.execute(
        select(
            Category.code,
            Category.name,
            func.count(Fair.id),
            func.coalesce(func.avg(_days), 0),
            func.coalesce(func.sum(_free), 0),
        )
        .join(Fair, (Fair.category_id == Category.id) & Fair.status.in_(COUNTED), isouter=True)
        .group_by(Category.id, Category.code, Category.name)
        .order_by(func.count(Fair.id).desc(), Category.sort_order)
    ).all()
    return [
        CategoryRow(
            code=code,
            name=name,
            count=cnt,
            avg_days=round(float(avg), 1),
            free_ratio=round(free / cnt, 3) if cnt else 0.0,
        )
        for code, name, cnt, avg, free in rows
    ]


@router.get("/venues", response_model=list[VenueRow])
def venues(db: DbSession):
    rows = db.execute(
        select(Venue.name, Venue.region, Category.name, func.count())
        .join(Fair, Fair.venue_id == Venue.id)
        .join(Category, Category.id == Fair.category_id)
        .where(Fair.status.in_(COUNTED))
        .group_by(Venue.id, Venue.name, Venue.region, Category.id, Category.name)
    ).all()
    by_venue: dict[str, dict] = {}
    for venue, region, cat, cnt in rows:
        v = by_venue.setdefault(venue, {"region": region, "count": 0, "cats": {}})
        v["count"] += cnt
        v["cats"][cat] = cnt
    out = [
        VenueRow(venue=name, region=v["region"], count=v["count"], top_category=max(v["cats"], key=v["cats"].get))
        for name, v in by_venue.items()
    ]
    return sorted(out, key=lambda r: -r.count)
