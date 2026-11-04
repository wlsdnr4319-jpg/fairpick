"""
지난 행사 기록 (fair_archive) 저장과 주제 분류.

주제는 제목 키워드로 나눈다. 위에서부터 처음 맞는 주제 하나만 붙인다.
'아트'(스마트), '티'(파티), '술'(기술)처럼 다른 낱말 속에 흔히 들어가는 짧은 말은 키워드로 쓰지 않는다.
키워드를 바꾸면 python -m app.scripts.backfill_archive --retheme 으로 다시 매긴다.
"""

import logging
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawlers.base import RawFair
from app.crawlers.normalize import PeriodParseError, parse_period
from app.models import FairArchive

logger = logging.getLogger(__name__)

OTHER = "기타"
THEMES: dict[str, tuple[str, ...]] = {
    "베이비·육아": ("베이비", "베페", "유아", "육아", "임신", "출산", "키즈"),
    "웨딩": ("웨딩", "혼수", "결혼"),
    "반려동물": ("펫", "캣", "도그", "반려", "애견", "고양이", "강아지"),
    "식음료": (
        "커피",
        "카페",
        "푸드",
        "음식",
        "식품",
        "주류",
        "와인",
        "맥주",
        "위스키",
        "디저트",
        "베이커리",
        "먹거리",
    ),
    "캠핑·레저": ("캠핑", "캠페어", "레저", "아웃도어", "낚시", "골프", "자전거"),
    "취업·창업": ("취업", "채용", "일자리", "창업", "프랜차이즈"),
    "건축·인테리어": ("건축", "인테리어", "리빙", "가구", "하우징"),
    "문화·취미": (
        "코믹",
        "게임",
        "아트페어",
        "미술",
        "일러스트",
        "굿즈",
        "핸드메이드",
        "공예",
        "도서",
        "서울국제도서전",
    ),
}


def theme_of(title: str) -> str:
    text = title.casefold()
    for theme, words in THEMES.items():
        if any(w.casefold() in text for w in words):
            return theme
    return OTHER


def upsert(db: Session, *, source: str, venue_id: int, items: Iterable[RawFair], now: datetime) -> dict[str, int]:
    """같은 (source, external_id) 는 덮어쓴다. 기간을 못 읽는 항목은 건너뛴다."""
    counts = {"saved": 0, "skipped": 0}
    # 원본 표에 같은 행사가 두 줄로 적힌 경우가 있다 (엑스코 2019 웨딩박람회). 묶음 안에서 먼저 하나로 합친다
    unique = {raw.external_id[:255]: raw for raw in items}
    for raw in unique.values():
        try:
            start, end = parse_period(raw.period_text)
        except PeriodParseError:
            logger.warning("archive: period parse failed %r", raw.period_text)
            counts["skipped"] += 1
            continue
        row = db.scalar(
            select(FairArchive).where(FairArchive.source == source, FairArchive.external_id == raw.external_id)
        )
        if row is None:
            row = FairArchive(source=source, external_id=raw.external_id[:255])
            db.add(row)
        row.venue_id = venue_id
        row.title = raw.title[:300]
        row.start_date, row.end_date = start, end
        row.theme = theme_of(raw.title)
        row.collected_at = now
        counts["saved"] += 1
    db.flush()
    return counts


def retheme(db: Session) -> int:
    changed = 0
    for row in db.scalars(select(FairArchive)):
        theme = theme_of(row.title)
        if theme != row.theme:
            row.theme = theme
            changed += 1
    db.flush()
    return changed
