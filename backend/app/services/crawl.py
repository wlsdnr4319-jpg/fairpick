"""
수집 실행과 중복 판정·변경 감지 (레퍼런스 8장).

- 같은 소스 안에서는 (source_id, external_id)로 찾는다. 이미 있으면 content_hash 를 비교한다.
  - 해시가 같으면 last_seen_at 만 갱신한다 (unchanged)
  - 해시가 다르면 changed 로 표시하고 검수 대기로 되돌린다
- 소스가 다르면 같은 장소, 겹치는 기간, 비슷한 제목을 기준으로 '병합 후보'만 표시하고 자동 병합하지 않는다.
- 수집 결과는 바로 공개하지 않는다. 새로 들어오거나 바뀐 항목만 검수 큐에 올리고, 공개 여부는 항상 관리자가 정한다.
"""

import logging
from collections.abc import Callable
from datetime import date, datetime
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.crawlers.base import BaseParser, RawFair
from app.crawlers.http import PoliteClient
from app.crawlers.normalize import PeriodParseError, content_hash, match_venue, parse_period
from app.crawlers.registry import get_parser
from app.models import CrawledItem, CrawlRun, CrawlSource, Fair, Venue, VenueAlias
from app.models.mixins import utcnow

logger = logging.getLogger(__name__)

# 오늘이 속한 달부터 몇 달 치를 수집할지
MONTHS_AHEAD = 3


def _months(today: date, count: int) -> list[tuple[int, int]]:
    out, y, m = [], today.year, today.month
    for _ in range(count):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def alias_map(db: Session) -> dict[str, int]:
    aliases = {v.name: v.id for v in db.scalars(select(Venue))}
    aliases.update({a.alias: a.venue_id for a in db.scalars(select(VenueAlias))})
    return aliases


def learn_alias(db: Session, alias: str, venue_id: int) -> int:
    """
    장소를 못 맞춘 항목을 관리자가 전시장을 골라 승인할 때: 원본 장소 문자열을 그 전시장의 별칭으로 저장한다.
    다음 수집부터 자동으로 맞춰지고, 지금 검수 대기 중인 같은 장소 항목도 바로 다시 맞춘다. 다시 맞춘 개수를 돌려준다.
    """
    alias = alias.strip()
    existing = db.scalar(select(VenueAlias).where(VenueAlias.alias == alias))
    if existing is not None and existing.venue_id != venue_id:
        raise AppError(409, "ALIAS_TAKEN", f"'{alias}' 는 이미 다른 전시장의 별칭이에요")
    if existing is None:
        db.add(VenueAlias(venue_id=venue_id, alias=alias))
        db.flush()

    aliases = alias_map(db)
    rematched = 0
    unmatched = select(CrawledItem).where(CrawledItem.review_status == "pending", CrawledItem.parsed_venue_id.is_(None))
    for item in db.scalars(unmatched):
        matched, _hall = match_venue(item.raw_venue or "", aliases)
        if matched is not None:
            item.parsed_venue_id = matched
            rematched += 1
    return rematched


def upsert_item(
    db: Session, source: CrawlSource, raw: RawFair, aliases: dict[str, int], now: datetime, ref_year: int
) -> str:
    """수집 항목 하나를 저장한다. 'new' | 'changed' | 'unchanged' 를 돌려준다."""
    digest = content_hash(raw.title, raw.period_text, raw.venue_text)
    item = db.scalar(
        select(CrawledItem).where(CrawledItem.source_id == source.id, CrawledItem.external_id == raw.external_id)
    )
    if item is not None and item.content_hash == digest:
        item.last_seen_at = now
        item.change_status = "unchanged"
        return "unchanged"

    try:
        start, end = parse_period(raw.period_text, ref_year=ref_year)
    except PeriodParseError:
        # 날짜를 못 읽으면 NULL 로 두고 검수 화면에서 직접 입력한다. 실패한 문자열은 테스트 케이스로 추가한다
        logger.warning("period parse failed: %r (%s)", raw.period_text, raw.detail_url)
        start = end = None
    venue_id, _hall = match_venue(raw.venue_text, aliases)

    status = "new" if item is None else "changed"
    if item is None:
        item = CrawledItem(source_id=source.id, external_id=raw.external_id, first_seen_at=now)
        db.add(item)
    item.raw_title = raw.title[:300]
    item.raw_period = raw.period_text[:200]
    item.raw_venue = raw.venue_text[:200]
    item.detail_url = raw.detail_url[:500]
    item.raw_payload = raw.to_payload()
    item.parsed_start_date, item.parsed_end_date = start, end
    item.parsed_venue_id = venue_id
    item.content_hash = digest
    item.change_status = status
    item.review_status = "pending"  # 새 항목, 바뀐 항목 모두 검수 대기
    item.last_seen_at = now
    return status


def run_source(
    db: Session,
    source: CrawlSource,
    *,
    today: date,
    now: datetime,
    parser_factory: Callable[[PoliteClient], BaseParser] | None = None,
) -> CrawlRun:
    """소스 하나를 수집하고 실행 이력(crawl_runs)을 남긴다. 실패해도 예외를 밖으로 던지지 않는다."""
    run = CrawlRun(source_id=source.id, status="running", started_at=now)
    db.add(run)
    db.commit()

    try:
        factory = parser_factory or get_parser(source.parser_key)
        aliases = alias_map(db)
        seen: dict[str, RawFair] = {}
        with PoliteClient() as client:
            parser = factory(client)
            for year, month in _months(today, MONTHS_AHEAD):
                for raw in parser.fetch_list(year, month):
                    seen.setdefault(raw.external_id, raw)
                if not parser.monthly:
                    break  # 월 지정 없이 한 번에 목록을 주는 사이트
        counts = {"new": 0, "changed": 0, "unchanged": 0}
        for raw in seen.values():
            counts[upsert_item(db, source, raw, aliases, now, today.year)] += 1
        run.found_count = len(seen)
        run.new_count = counts["new"]
        run.changed_count = counts["changed"]
        run.status = "succeeded"
    except Exception as exc:  # 사이트 구조 변경, 차단, 네트워크 오류
        db.rollback()
        run = db.get(CrawlRun, run.id)
        run.status = "failed"
        run.error_message = f"{type(exc).__name__}: {exc}"[:2000]
        logger.exception("crawl failed: %s", source.parser_key)
    run.finished_at = utcnow()
    db.commit()
    if run.status == "failed":
        alert_if_repeated_failures(db, source)
    return run


def run_all_sources(db: Session, *, today: date, now: datetime) -> list[CrawlRun]:
    sources = db.scalars(select(CrawlSource).where(CrawlSource.is_active.is_(True)).order_by(CrawlSource.id)).all()
    return [run_source(db, s, today=today, now=now) for s in sources]


# ---------------------------------------------------------------------------
# 병합 후보: 다른 경로로 이미 등록된 박람회와 같은 행사일 수 있는 것
# ---------------------------------------------------------------------------


def _similar(a: str, b: str) -> float:
    norm = lambda s: "".join(ch for ch in s.casefold() if ch.isalnum())  # noqa: E731
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def merge_candidates(db: Session, item: CrawledItem, limit: int = 3) -> list[tuple[Fair, float]]:
    if item.parsed_start_date is None or item.parsed_end_date is None:
        return []
    stmt = select(Fair).where(
        Fair.start_date <= item.parsed_end_date,
        Fair.end_date >= item.parsed_start_date,
    )
    if item.parsed_venue_id:
        stmt = stmt.where(Fair.venue_id == item.parsed_venue_id)
    scored = [(f, _similar(item.raw_title, f.title)) for f in db.scalars(stmt)]
    return sorted([x for x in scored if x[1] >= 0.4], key=lambda x: -x[1])[:limit]


# ---------------------------------------------------------------------------
# 수집 모니터링 (F-18): 연속 실패 시 관리자 메일
# ---------------------------------------------------------------------------

ALERT_AFTER = 2  # 연속 실패 횟수


def alert_if_repeated_failures(db: Session, source: CrawlSource) -> bool:
    recent = db.scalars(
        select(CrawlRun)
        .where(CrawlRun.source_id == source.id)
        .order_by(CrawlRun.started_at.desc(), CrawlRun.id.desc())
        .limit(ALERT_AFTER)
    ).all()
    if len(recent) < ALERT_AFTER or any(r.status != "failed" for r in recent):
        return False
    from app.models import User
    from app.services import mail

    admins = db.scalars(select(User).where(User.role == "admin")).all()
    for admin in admins:
        try:
            mail.send(
                mail.Mail(
                    to=admin.email,
                    subject=f"[페어픽 관리자] 수집 연속 실패: {source.parser_key}",
                    template="crawl_alert",
                    context={"source": source.parser_key, "count": ALERT_AFTER, "error": recent[0].error_message or ""},
                )
            )
        except Exception:
            logger.exception("crawl alert mail failed")
    return bool(admins)
