import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.services.garmin_service import garmin_service
from app.services.leetcode_service import leetcode_service

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.TIMEZONE))


def setup_scheduler():
    """
    Registers periodic background tasks:
    1. Garmin Sleep Polling: Runs every hour on the hour between 8:00 AM and 1:00 PM (Eastern Time).
    2. LeetCode Submissions: Runs every 2 hours to keep the cache fresh.
    """
    # Garmin cron: runs every hour at minute 0 during the polling window (8:00 to 13:00)
    scheduler.add_job(
        garmin_service.scheduled_hourly_job,
        trigger=CronTrigger(
            hour=f"{settings.POLL_START_HOUR}-{settings.POLL_END_HOUR}",
            minute=0,
            timezone=ZoneInfo(settings.TIMEZONE)
        ),
        id="garmin_sleep_poll",
        name="Poll Intervals.icu for Garmin Sleep Score",
        replace_existing=True
    )

    # Also add a backup job at 1:05 PM to ensure default fallback is sealed if no score arrived
    scheduler.add_job(
        garmin_service.scheduled_hourly_job,
        trigger=CronTrigger(
            hour=settings.POLL_END_HOUR,
            minute=5,
            timezone=ZoneInfo(settings.TIMEZONE)
        ),
        id="garmin_fallback_seal",
        name="Seal Garmin Sleep Default Fallback",
        replace_existing=True
    )

    # LeetCode interval: runs every N hours
    scheduler.add_job(
        leetcode_service.fetch_latest_submission,
        trigger=IntervalTrigger(hours=settings.LEETCODE_POLL_INTERVAL_HOURS),
        id="leetcode_poll",
        name="Refresh LeetCode Submissions Cache",
        replace_existing=True
    )

    logger.info("[Scheduler] Registered background tasks successfully.")
