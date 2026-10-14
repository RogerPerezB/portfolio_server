import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo
import httpx

from app.core.config import settings

logger = logging.getLogger("garmin_service")


class GarminService:
    def __init__(self):
        self._cache: Dict[str, Any] = {
            "score": None,
            "date": None,
            "duration_seconds": None,
            "hrv": None,
            "is_default": False,
            "status": "uninitialized",
            "last_updated": None,
            "source": "none",
            "message": None
        }
        self.tz = ZoneInfo(settings.TIMEZONE)

    def _get_local_now(self) -> datetime:
        return datetime.now(self.tz)

    def is_score_filled_for_today(self, today_str: str) -> bool:
        """Returns True if a real (non-fallback) score is already cached for today."""
        return (
            self._cache.get("date") == today_str
            and self._cache.get("score") is not None
            and not self._cache.get("is_default", False)
        )

    async def sync_sleep_score(self, force: bool = False) -> Dict[str, Any]:
        """
        State Machine for Sleep Score Telemetry:
        1. 00:00 - 08:00 AM (Eastern Time): Status is 'asleep' (overnight vitals monitoring).
        2. 08:00 AM - 1:00 PM: Hourly polling to Intervals.icu until sleepScore is populated.
           - Stops asking once today's score is retrieved.
        3. 1:00 PM onwards: If no score retrieved from Garmin, seals default score of 85.
        """
        now = self._get_local_now()
        today = now.date().isoformat()
        current_hour = now.hour

        # 1. Midnight to 8:00 AM (Eastern Time): Asleep window
        if current_hour < settings.POLL_START_HOUR and not force:
            self._cache = {
                "score": None,
                "date": today,
                "duration_seconds": None,
                "hrv": None,
                "is_default": False,
                "status": "asleep",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "source": "garmin_telemetry",
                "message": "Asleep (monitoring vitals overnight on Garmin watch)"
            }
            logger.info(f"[GarminService] Night window active (hour={current_hour} ET). Status: asleep.")
            return self._cache

        # 2. Stop asking if today's score is already filled (unless forced)
        if not force and self.is_score_filled_for_today(today):
            logger.info(
                f"[GarminService] Score already filled for {today}: "
                f"{self._cache['score']}/100. Skipping external API call."
            )
            return self._cache

        # 3. Check if we have credentials
        if not settings.INTERVALS_API_KEY:
            logger.warning("[GarminService] INTERVALS_API_KEY is not configured.")
            if current_hour >= settings.POLL_END_HOUR or force:
                self._apply_fallback(today, "API key not set, applied default score.")
            return self._cache

        # 4. Check if we are within the allowed polling window (8:00 AM - 1:00 PM)
        in_window = settings.POLL_START_HOUR <= current_hour <= settings.POLL_END_HOUR

        if in_window or force:
            logger.info(f"[GarminService] Polling Intervals.icu for sleep score ({today}, hour={current_hour})...")
            url = f"https://intervals.icu/api/v1/athlete/{settings.INTERVALS_ATHLETE_ID}/wellness?oldest={today}&newest={today}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(
                        url,
                        auth=("API_KEY", settings.INTERVALS_API_KEY)
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data and len(data) > 0:
                            wellness = data[0]
                            sleep_score = wellness.get("sleepScore")

                            if sleep_score is not None:
                                self._cache = {
                                    "score": int(sleep_score),
                                    "date": today,
                                    "duration_seconds": wellness.get("sleepSecs"),
                                    "hrv": wellness.get("hrv"),
                                    "is_default": False,
                                    "status": "synced",
                                    "last_updated": datetime.now(timezone.utc).isoformat(),
                                    "source": "garmin_sync",
                                    "message": "Live sleep score synced successfully"
                                }
                                logger.info(f"[GarminService] Successfully synced sleep score: {sleep_score}/100 for {today}.")
                                return self._cache
                            else:
                                logger.info(f"[GarminService] Wellness record exists for {today}, but sleepScore is null.")
                        else:
                            logger.info(f"[GarminService] No wellness data synced for {today} yet.")
                    else:
                        logger.error(f"[GarminService] Intervals.icu API error: HTTP {response.status_code}")

                except Exception as e:
                    logger.error(f"[GarminService] Network or parsing error during sync: {e}")

        # 5. If after 1:00 PM and still no score, assign default score of 85
        if current_hour >= settings.POLL_END_HOUR and not self.is_score_filled_for_today(today):
            self._apply_fallback(today, "Past 1:00 PM without sleep score. Default score applied.")

        return self._cache

    def _apply_fallback(self, today: str, reason: str):
        self._cache = {
            "score": settings.DEFAULT_SLEEP_SCORE,
            "date": today,
            "duration_seconds": None,
            "hrv": None,
            "is_default": True,
            "status": "default_fallback",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "source": "default_fallback",
            "message": "Default fallback score assigned"
        }
        logger.info(f"[GarminService] {reason} Assigned score: {settings.DEFAULT_SLEEP_SCORE}/100.")

    async def get_latest_sleep(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Returns the latest cached sleep record, triggering sync if needed."""
        now = self._get_local_now()
        today = now.date().isoformat()

        # If cache is from a previous date, or uninitialized, or force requested:
        if force_refresh or self._cache.get("date") != today:
            await self.sync_sleep_score(force=force_refresh)

        return self._cache

    async def scheduled_hourly_job(self):
        """Called every hour by the background scheduler."""
        now = self._get_local_now()
        hour = now.hour
        logger.info(f"[GarminScheduler] Hourly check trigger at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        if settings.POLL_START_HOUR <= hour <= settings.POLL_END_HOUR:
            await self.sync_sleep_score()
        else:
            logger.info(f"[GarminScheduler] Outside 8:00 AM - 1:00 PM window (current hour={hour}). Skipping poll.")


garmin_service = GarminService()
