"""정기 수집 작업. 워커가 매일 새벽 4시(KST)에 부른다. 수동 실행: python -m app.jobs.crawl_job"""

import logging

from app.core.deps import get_now, get_today
from app.db.session import SessionLocal
from app.services.crawl import run_all_sources

logger = logging.getLogger(__name__)


def run_all() -> None:
    with SessionLocal() as db:
        runs = run_all_sources(db, today=get_today(), now=get_now())
    for r in runs:
        logger.info(
            "crawl %s: %s found=%s new=%s changed=%s",
            r.source_id,
            r.status,
            r.found_count,
            r.new_count,
            r.changed_count,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_all()
