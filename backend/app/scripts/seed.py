"""
시드 데이터 넣기. 여러 번 실행해도 같은 결과가 나온다 (이미 있으면 갱신).

실행 (backend/ 폴더에서):
    python -m app.scripts.seed

- 카테고리는 code, 태그는 slug, 전시장은 name, 박람회는 (title, start_date) 로 같은 행을 찾는다.
- 박람회는 공개(published) 상태, 출처 manual 로 넣는다.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Category, CrawlSource, Fair, FairTag, Tag, Venue, VenueAlias
from app.scripts.seed_data import CATEGORIES, CRAWL_SOURCES, FAIRS, PARKING_NOTES, TAGS, VENUES

# 박람회 30건을 조사·확인한 날 (verified=True 인 행사의 정보 확인일). 한국 시간 2026-11-04 14:00 = UTC 05:00
RESEARCHED_AT_UTC = datetime(2026, 11, 4, 5, 0)

_FAIR_META_KEYS = {"category", "venue", "tags", "verified", "ref"}


def seed_categories(db: Session) -> dict[str, Category]:
    out = {}
    for code, name, order in CATEGORIES:
        obj = db.scalar(select(Category).where(Category.code == code)) or Category(code=code)
        obj.name, obj.sort_order = name, order
        db.add(obj)
        out[code] = obj
    db.flush()
    return out


def seed_tags(db: Session) -> dict[str, Tag]:
    out = {}
    for slug, name, votable in TAGS:
        obj = db.scalar(select(Tag).where(Tag.slug == slug)) or Tag(slug=slug)
        obj.name, obj.is_votable = name, votable
        db.add(obj)
        out[slug] = obj
    db.flush()
    return out


def seed_venues(db: Session) -> dict[str, Venue]:
    out = {}
    for name, region, address, (lat, lng), aliases in VENUES:
        obj = db.scalar(select(Venue).where(Venue.name == name)) or Venue(name=name)
        obj.region, obj.address = region, address
        obj.latitude, obj.longitude = Decimal(str(lat)), Decimal(str(lng))
        obj.parking_note = PARKING_NOTES.get(name)
        db.add(obj)
        db.flush()
        existing = set(db.scalars(select(VenueAlias.alias).where(VenueAlias.venue_id == obj.id)))
        for alias in aliases:
            if alias not in existing:
                db.add(VenueAlias(venue_id=obj.id, alias=alias))
        out[name] = obj
    db.flush()
    return out


def seed_fairs(db: Session, categories, venues, tags) -> tuple[int, int]:
    created = updated = 0
    for row in FAIRS:
        fields = {k: v for k, v in row.items() if k not in _FAIR_META_KEYS}
        obj = db.scalar(select(Fair).where(Fair.title == row["title"], Fair.start_date == row["start_date"]))
        if obj is None:
            obj = Fair(source="manual")
            created += 1
        else:
            updated += 1

        for key, value in fields.items():
            setattr(obj, key, value)
        obj.category = categories[row["category"]]
        obj.venue = venues[row["venue"]]
        obj.status = "published"
        obj.verified_at = RESEARCHED_AT_UTC if row["verified"] else None
        db.add(obj)
        db.flush()

        # 태그는 시드 목록과 똑같이 맞춘다 (관리자 태그만. 투표로 붙은 태그는 건드리지 않는다)
        wanted = {tags[slug].id for slug in row.get("tags", [])}
        current = {ft.tag_id: ft for ft in obj.fair_tags if ft.source == "admin"}
        for tag_id, ft in current.items():
            if tag_id not in wanted:
                db.delete(ft)
        for tag_id in wanted - current.keys():
            db.add(FairTag(fair_id=obj.id, tag_id=tag_id, source="admin"))
    db.flush()
    return created, updated


def seed_crawl_sources(db: Session, venues: dict[str, Venue]) -> int:
    for row in CRAWL_SOURCES:
        obj = db.scalar(select(CrawlSource).where(CrawlSource.parser_key == row["parser_key"]))
        obj = obj or CrawlSource(parser_key=row["parser_key"])
        obj.venue_id = venues[row["venue"]].id
        obj.list_url = row["list_url"]
        obj.policy_note = row["policy_note"]
        obj.policy_checked_at = RESEARCHED_AT_UTC
        db.add(obj)
    db.flush()
    return len(CRAWL_SOURCES)


def run(db: Session) -> dict[str, int]:
    categories = seed_categories(db)
    tags = seed_tags(db)
    venues = seed_venues(db)
    created, updated = seed_fairs(db, categories, venues, tags)
    sources = seed_crawl_sources(db, venues)
    return {
        "crawl_sources": sources,
        "categories": len(categories),
        "tags": len(tags),
        "venues": len(venues),
        "fairs_created": created,
        "fairs_updated": updated,
    }


def main() -> None:
    with SessionLocal() as db:
        result = run(db)
        db.commit()
    print("seed done:", ", ".join(f"{k}={v}" for k, v in result.items()))


if __name__ == "__main__":
    main()
