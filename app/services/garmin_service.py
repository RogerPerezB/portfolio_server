import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo
import httpx

from app.core.config import settings
from app.core.database import db

logger = logging.getLogger("garmin_service")


class GarminService:
    def __init__(self):
        self.tz = ZoneInfo(settings.TIMEZONE)
        self._sync_lock = asyncio.Lock()

    def _get_local_now(self) -> datetime:
        return datetime.now(self.tz)

    def is_score_filled_for_today(self, today_str: str) -> bool:
        """Returns True if a real sleep score has already been received and saved for today."""
        cached = db.get_garmin()
        return (
            cached.get("date") == today_str
            and cached.get("score") is not None
            and not cached.get("is_default", False)
        )

    def _build_asleep_state(self, today: str) -> Dict[str, Any]:
        return {
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

    def _build_no_score_yet_state(self, today: str) -> Dict[str, Any]:
        return {
            "score": None,
            "date": today,
            "duration_seconds": None,
            "hrv": None,
            "is_default": False,
            "status": "no_score_yet",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "source": "garmin_telemetry",
            "message": "No score yet"
        }

    async def sync_sleep_score(self, force: bool = False) -> Dict[str, Any]:
        """
        Background State Machine for Sleep Score Telemetry:
        1. 00:00 - 07:59 AM (Eastern Time): Status is 'asleep' (no polling before 8:00 AM).
        2. 08:00 AM onwards: Polls Intervals.icu every 30 minutes until sleepScore is received.
           - While waiting for data, stores status='no_score_yet' and message='No score yet' in JSON DB.
           - Once today's score is received, saves it to the JSON DB and stops checking for the day.
        """
        async with self._sync_lock:
            now = self._get_local_now()
            today = now.date().isoformat()
            current_hour = now.hour

            # 1. Midnight to 8:00 AM (Eastern Time): Do not poll before 8:00 AM
            if current_hour < settings.POLL_START_HOUR and not force:
                state = db.save_garmin(self._build_asleep_state(today))
                logger.info(f"[GarminService] Before 8:00 AM ET (hour={current_hour}). Status saved as 'asleep'.")
                return state

            # 2. Stop checking for the day if today's real score is already saved
            if not force and self.is_score_filled_for_today(today):
                cached = db.get_garmin()
                logger.info(
                    f"[GarminService] Score already received for {today} "
                    f"({cached['score']}/100). Stopping checks for today."
                )
                return cached

            # 3. Check if credentials are configured
            if not settings.INTERVALS_API_KEY:
                logger.warning("[GarminService] INTERVALS_API_KEY is not configured. Saving 'No score yet'.")
                return db.save_garmin(self._build_no_score_yet_state(today))

            # 4. Poll Intervals.icu (8:00 AM onwards, or when forced)
            logger.info(f"[GarminService] Polling Intervals.icu for sleep score ({today}, {now.strftime('%H:%M')} ET)...")
            url = (
                f"https://intervals.icu/api/v1/athlete/{settings.INTERVALS_ATHLETE_ID}"
                f"/wellness?oldest={today}&newest={today}"
            )

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
                                synced_state = {
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
                                db.save_garmin(synced_state)
                                logger.info(
                                    f"[GarminService] Received sleep score: {sleep_score}/100 for {today}. "
                                    f"Saved to JSON DB; polling complete for today."
                                )
                                return synced_state
                            else:
                                logger.info(f"[GarminService] Wellness entry found for {today}, but sleepScore is null.")
                        else:
                            logger.info(f"[GarminService] No wellness data synced for {today} yet.")
                    else:
                        logger.error(f"[GarminService] Intervals.icu API error: HTTP {response.status_code}")

                except Exception as e:
                    logger.error(f"[GarminService] Network or parsing error during sync: {e}")

            # 5. No score received yet: record 'No score yet' in JSON DB and wait for next 30-min check
            return db.save_garmin(self._build_no_score_yet_state(today))

    async def get_latest_sleep(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Serves sleep data directly from the local JSON database for instant frontend response.
        Only blocks on an external API call if force_refresh=True is explicitly requested.
        """
        if force_refresh:
            return await self.sync_sleep_score(force=True)

        now = self._get_local_now()
        today = now.date().isoformat()
        current_hour = now.hour
        cached = db.get_garmin()

        # Before 8:00 AM: ensure state reflects overnight 'asleep' if date rolled over
        if current_hour < settings.POLL_START_HOUR:
            if cached.get("date") != today or cached.get("status") != "asleep":
                return db.save_garmin(self._build_asleep_state(today))
            return cached

        # 8:00 AM onwards: if DB still has yesterday's record or overnight 'asleep' status,
        # immediately transition DB to 'No score yet', trigger a silent background poll, and return immediately.
        if (
            cached.get("date") != today
            or cached.get("status") in ("asleep", "uninitialized", "default_fallback")
            or cached.get("is_default", False)
        ):
            state = db.save_garmin(self._build_no_score_yet_state(today))
            asyncio.create_task(self.sync_sleep_score())
            return state

        return cached

    async def scheduled_poll_job(self):
        """Called every 30 minutes starting at 8:00 AM by the background scheduler."""
        now = self._get_local_now()
        today = now.date().isoformat()
        hour = now.hour

        if hour < settings.POLL_START_HOUR:
            db.save_garmin(self._build_asleep_state(today))
            logger.info(f"[GarminScheduler] Before 8:00 AM ({now.strftime('%H:%M %Z')}). Skipping poll.")
            return

        if self.is_score_filled_for_today(today):
            logger.info(
                f"[GarminScheduler] 30-min tick at {now.strftime('%H:%M %Z')}: "
                f"Score already stored for {today}. Skipping poll."
            )
            return

        logger.info(f"[GarminScheduler] 30-min check triggered at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        await self.sync_sleep_score()


garmin_service = GarminService()
