"""
알림 선별·발송 작업 (레퍼런스 9장). 워커가 매일 오전 9시(KST)에 부른다.
수동 실행: python -m app.jobs.notify_job
"""

import logging

from app.core.config import get_settings
from app.core.deps import get_now, get_today
from app.db.session import SessionLocal
from app.services.notifications import select_targets, send_pending

logger = logging.getLogger(__name__)


def select_and_send() -> None:
    with SessionLocal() as db:
        selected = select_targets(db, today=get_today(), now=get_now())
        sent = send_pending(db, now=get_now(), base_url=get_settings().app_base_url.rstrip("/"))
    logger.info("notify: selected=%s result=%s", selected, sent)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    select_and_send()
