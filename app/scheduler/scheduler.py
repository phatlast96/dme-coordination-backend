from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import FOLLOWUP_POLL_SECONDS
from app.jobs.process_followups import process_due_followups

logger = logging.getLogger("dme.scheduler")

_scheduler: AsyncIOScheduler | None = None


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        process_due_followups,
        "interval",
        seconds=FOLLOWUP_POLL_SECONDS,
        id="process_due_followups",
        replace_existing=True,
        max_instances=1,
    )
    return scheduler


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    _scheduler = create_scheduler()
    _scheduler.start()
    logger.info("SCHEDULER_STARTED poll_seconds=%s", FOLLOWUP_POLL_SECONDS)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("SCHEDULER_STOPPED")
    _scheduler = None
