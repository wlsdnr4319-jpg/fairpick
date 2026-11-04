"""
수집·알림 워커 (레퍼런스 8장 '워커 분리'). 실행: python -m app.jobs.worker

APScheduler 를 API 서버 안에서 돌리면 uvicorn 워커를 여러 개 띄울 때 같은 작업이 워커 수만큼 실행된다.
그래서 수집·알림 작업은 이 별도 프로세스 하나에서만 돌린다 (docker compose 의 worker 서비스는 반드시 1개).
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.jobs.crawl_job import run_all
from app.jobs.notify_job import select_and_send


def build_scheduler() -> BlockingScheduler:
    tz = get_settings().app_tz
    scheduler = BlockingScheduler(timezone=tz)
    # max_instances=1: 이전 실행이 안 끝났으면 겹쳐 돌지 않는다. coalesce: 밀린 실행은 한 번으로 합친다
    scheduler.add_job(run_all, CronTrigger(hour=4, minute=0, timezone=tz), id="crawl", max_instances=1, coalesce=True)
    scheduler.add_job(
        select_and_send,
        CronTrigger(hour=9, minute=0, timezone=tz),
        id="notify",
        max_instances=1,
        coalesce=True,
    )
    return scheduler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    build_scheduler().start()
