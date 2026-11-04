"""
오래된 기록 정리 (워커가 매일 03:30 KST 에 부른다). 수동 실행: python -m app.jobs.cleanup_job

- login_attempts: 하루 지난 로그인 시도 기록. 횟수 제한은 최근 15분만 보므로 더 둘 이유가 없다.
"""

import logging

from app.core.deps import get_now
from app.db.session import SessionLocal
from app.services import login_guard

logger = logging.getLogger(__name__)


def cleanup() -> None:
    with SessionLocal() as db:
        deleted = login_guard.purge(db, get_now())
        db.commit()
    logger.info("cleanup: login_attempts deleted=%s", deleted)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cleanup()
