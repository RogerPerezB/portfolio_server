from fastapi import APIRouter, Query
from app.schemas.garmin import GarminSleepResponse, SleepData
from app.services.garmin_service import garmin_service

router = APIRouter(tags=["Garmin / Telemetry"])


@router.get("/sleep", response_model=GarminSleepResponse)
async def get_garmin_sleep(force_refresh: bool = Query(False, description="Force live re-query to Intervals.icu")):
    """
    Returns today's sleep score immediately from the local JSON database:
    - Midnight to 8:00 AM Eastern Time: status is 'asleep'.
    - 8:00 AM onwards: background scheduler checks every 30 minutes until a score arrives.
    - If no score is available yet after 8:00 AM, returns status='no_score_yet' and message='No score yet'.
    - Once today's score is received, returns status='synced' with the score and stops polling for the day.
    """
    data = await garmin_service.get_latest_sleep(force_refresh=force_refresh)

    return GarminSleepResponse(
        source=data.get("source", "json_db"),
        last_updated=data.get("last_updated") or "",
        data=SleepData(
            score=data.get("score"),
            date=data.get("date") or "",
            duration_seconds=data.get("duration_seconds"),
            hrv=data.get("hrv"),
            is_default=data.get("is_default", False),
            status=data.get("status", "no_score_yet"),
            message=data.get("message") or "No score yet"
        )
    )


@router.post("/sync")
async def trigger_garmin_sync(force: bool = Query(True, description="Force sync ignoring existing cache")):
    """Manually triggers an immediate synchronization with Intervals.icu and updates the JSON database."""
    updated = await garmin_service.sync_sleep_score(force=force)
    return {
        "status": "success",
        "result": updated
    }
