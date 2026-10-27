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
    Registers periodic silent background tasks:
    1. Garmin Sleep Polling: Starts at 8:00 AM Eastern Time and runs every 30 minutes (8:00, 8:30, 9:00, ...)
       until today's sleep score is received, then skips further checks for the rest of the day.
    2. Garmin Midnight Rollover: Resets status to 'asleep' at 00:00 Eastern Time.
    3. LeetCode Submissions: Runs every 2 hours in the background and saves to the JSON database.
    """
    # 1. Garmin 30-minute polling starting at 8:00 AM ET (minute 0 and 30 of every hour from 8:00 AM to 11:30 PM)
    scheduler.add_job(
        garmin_service.scheduled_poll_job,
        trigger=CronTrigger(
            hour=f"{settings.POLL_START_HOUR}-23",
            minute="0,30",
            timezone=ZoneInfo(settings.TIMEZONE)
        ),
        id="garmin_sleep_poll_30m",
        name="Poll Intervals.icu every 30m starting at 8am until score received",
        replace_existing=True
    )

    # 2. Garmin overnight rollover at midnight ET
    scheduler.add_job(
        garmin_service.scheduled_poll_job,
        trigger=CronTrigger(
            hour=0,
            minute=0,
            timezone=ZoneInfo(settings.TIMEZONE)
        ),
        id="garmin_midnight_rollover",
        name="Reset Garmin status to asleep at midnight ET",
        replace_existing=True
    )

    # 3. LeetCode interval: runs every N hours
    scheduler.add_job(
        leetcode_service.fetch_latest_submission,
        trigger=IntervalTrigger(hours=settings.LEETCODE_POLL_INTERVAL_HOURS),
        id="leetcode_poll",
        name="Refresh LeetCode Submissions in JSON DB",
        replace_existing=True
    )

    logger.info("[Scheduler] Registered 30-minute Garmin polling (from 8:00 AM) and LeetCode background jobs.")
