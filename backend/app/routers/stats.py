"""
통계 리포트 API (레퍼런스 12장, F-19). '언제, 어디서, 어떤 박람회가 많이 열리는가'.

GET /api/v1/stats/monthly?year=2026   월별·카테고리별 개최 수
GET /api/v1/stats/categories          카테고리별 개최 수, 평균 기간, 무료 비율
GET /api/v1/stats/venues              전시장별 개최 수와 가장 많은 카테고리
GET /api/v1/stats/history?from_year=2019&to_year=2025
                                      지난 행사 기록(fair_archive): 연도별·전시장별 수, 주제별로 많이 열리는 달

공개(published)와 숨김(hidden) 박람회를 함께 센다. 지난 행사를 hidden 으로 넣어 분석에만 쓰기 때문이다.
초안(draft)은 검수 전이라 뺀다.
"""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select

from app.core.deps import DbSession
from app.models import Category, Fair, FairArchive, Venue
from app.services.archive import EXCLUDED, OTHER, THEMES

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


class HistoryYear(BaseModel):
    year: int
    total: int
    by_venue: dict[str, int]


class ThemeMonths(BaseModel):
    theme: str
    total: int
    by_month: list[int]  # 1월~12월 (개막일 기준, 여러 해 합계)
    peak_months: list[int]  # 가장 많은 달 (같은 수면 모두)


class History(BaseModel):
    from_year: int
    to_year: int
    total: int
    venues: list[str]  # 전시장 id 순서
    # 전시장별로 기록이 처음 나오는 해. from_year 보다 늦으면 그 전 해는 '0건'이 아니라 '기록 없음'이다
    # (수원메쎄 달력은 2020년 7월부터, 코엑스 마곡은 2024년 개관). 연도 비교는 from_year 부터 있는 곳끼리 한다
    venue_since: dict[str, int]
    by_year: list[HistoryYear]
    themes: list[ThemeMonths]  # THEMES 순서. '기타'와 EXCLUDED 는 빠진다
    other_total: int  # 주제를 붙이지 못한 행사 수
    excluded: dict[str, int]  # 박람회가 아니라 주제 표에서 뺀 행사 수 (입주박람회, 박람회 아님)


@router.get("/history", response_model=History)
def history(
    db: DbSession,
    from_year: Annotated[int, Query(ge=2000, le=2100)] = 2019,
    to_year: Annotated[int, Query(ge=2000, le=2100)] = 2025,
):
    year = func.year(FairArchive.start_date)
    month = func.month(FairArchive.start_date)
    in_range = year.between(from_year, to_year)

    venue_rows = db.execute(
        select(Venue.id, Venue.name, func.min(year))
        .join(FairArchive, FairArchive.venue_id == Venue.id)
        .where(in_range)
        .group_by(Venue.id, Venue.name)
        .order_by(Venue.id)
    ).all()
    venues = [name for _, name, _ in venue_rows]
    venue_since = {name: since for _, name, since in venue_rows}

    by_year = {
        y: HistoryYear(year=y, total=0, by_venue=dict.fromkeys(venues, 0)) for y in range(from_year, to_year + 1)
    }
    for y, venue, n in db.execute(
        select(year, Venue.name, func.count())
        .join(Venue, Venue.id == FairArchive.venue_id)
        .where(in_range)
        .group_by(year, Venue.name)
    ):
        by_year[y].by_venue[venue] = n
        by_year[y].total += n

    months: dict[str, list[int]] = {t: [0] * 12 for t in THEMES}
    other = 0
    excluded = dict.fromkeys(EXCLUDED, 0)
    for theme, m, n in db.execute(
        select(FairArchive.theme, month, func.count()).where(in_range).group_by(FairArchive.theme, month)
    ):
        if theme in excluded:
            excluded[theme] += n
        elif theme == OTHER or theme not in months:
            other += n
        else:
            months[theme][m - 1] = n

    themes = []
    for theme, counts in months.items():
        top = max(counts)
        themes.append(
            ThemeMonths(
                theme=theme,
                total=sum(counts),
                by_month=counts,
                peak_months=[i + 1 for i, c in enumerate(counts) if top and c == top],
            )
        )
    total = sum(y.total for y in by_year.values())
    return History(
        from_year=from_year,
        to_year=to_year,
        total=total,
        venues=venues,
        venue_since=venue_since,
        by_year=list(by_year.values()),
        themes=themes,
        other_total=other,
        excluded=excluded,
    )
