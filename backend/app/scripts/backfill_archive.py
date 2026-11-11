"""
지난 행사 기록(fair_archive)을 전시장 사이트에서 모은다. 분석용으로 한 번(또는 해마다 한 번) 돌린다.

    python -m app.scripts.backfill_archive --from 2019 --to 2025
    python -m app.scripts.backfill_archive --sources exco --from 2010 --to 2025
    python -m app.scripts.backfill_archive --retheme      # 주제 키워드를 바꾼 뒤 다시 매기기

수집 매너는 정기 수집과 같다 (요청 간 2초, User-Agent 에 연락처). 요청 수:
- exco: 1년에 1번 (연간 일정표)
- coex: 1달에 1~3번 (월별 목록, 페이지 나눔)
- setec: 1달에 1~2번 (개최기간 검색)
- kintex: 1년에 2~3번 (기간 검색, 100건씩)
같은 행사는 (source, external_id) 로 덮어쓰므로 다시 돌려도 중복되지 않는다.
"""

import argparse
import calendar
import logging
from datetime import date

from sqlalchemy import select

from app.core.deps import get_now
from app.crawlers.http import PoliteClient
from app.crawlers.registry import get_parser
from app.db.session import SessionLocal
from app.models import CrawlSource
from app.services import archive

logger = logging.getLogger(__name__)
SOURCES = ("exco", "coex", "setec", "kintex")


def _months(year: int):
    for month in range(1, 13):
        yield month, date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def fetch_year(parser_key: str, client: PoliteClient, year: int):
    parser = get_parser(parser_key)(client)
    if parser_key == "exco":
        from app.crawlers.exco import EXHIBITION, LIST_URL

        return parser.parse_list(client.get(LIST_URL, params={"syear": year, "ex_cate": EXHIBITION}))
    if parser_key == "kintex":
        return parser.fetch_period(date(year, 1, 1), date(year, 12, 31))
    items = []
    for month, first, last in _months(year):
        if parser_key == "coex":
            items += parser.fetch_list(year, month)
        else:  # setec
            items += parser.fetch_period(first, last)
    return items


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", default=",".join(SOURCES))
    ap.add_argument("--from", dest="year_from", type=int, default=2019)
    ap.add_argument("--to", dest="year_to", type=int, default=date.today().year - 1)
    ap.add_argument("--retheme", action="store_true", help="수집하지 않고 주제만 다시 매긴다")
    args = ap.parse_args()

    with SessionLocal() as db:
        if args.retheme:
            print(f"retheme: {archive.retheme(db)} rows changed")
            db.commit()
            return
        with PoliteClient() as client:
            for key in args.sources.split(","):
                source = db.scalar(select(CrawlSource).where(CrawlSource.parser_key == key))
                if source is None:
                    raise SystemExit(f"crawl_sources 에 {key} 가 없어요. 먼저 python -m app.scripts.seed")
                for year in range(args.year_from, args.year_to + 1):
                    items = fetch_year(key, client, year)
                    counts = archive.upsert(db, source=key, venue_id=source.venue_id, items=items, now=get_now())
                    db.commit()  # 해마다 저장: 중간에 끊겨도 받은 만큼은 남는다
                    print(f"{key} {year}: fetched={len(items)} {counts}", flush=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
