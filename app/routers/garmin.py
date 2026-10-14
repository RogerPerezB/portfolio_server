from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Query
from app.schemas.garmin import GarminSleepResponse, SleepData
from app.services.garmin_service import garmin_service

router = APIRouter(tags=["Garmin / Telemetry"])


@router.get("/sleep", response_model=GarminSleepResponse)
async def get_garmin_sleep(force_refresh: bool = Query(False, description="Force re-querying Intervals.icu")):
    """
    Returns today's sleep score synced from Garmin via Intervals.icu.
    - Midnight to 8:00 AM Eastern Time: status is 'asleep' (monitoring vitals).
    - Polled hourly from 8:00 AM to 1:00 PM Eastern Time until populated.
    - If no score is received after 1:00 PM, returns the default score of 85.
    """
    data = await garmin_service.get_latest_sleep(force_refresh=force_refresh)

    if not data or (data.get("score") is None and data.get("status") != "asleep"):
        raise HTTPException(status_code=503, detail="Sleep score data is warming up or temporarily unavailable.")

    return GarminSleepResponse(
        source=data.get("source", "garmin_telemetry"),
        last_updated=data.get("last_updated") or "",
        data=SleepData(
            score=data.get("score"),
            date=data.get("date") or "",
            duration_seconds=data.get("duration_seconds"),
            hrv=data.get("hrv"),
            is_default=data.get("is_default", False),
            status=data.get("status", "synced"),
            message=data.get("message")
        )
    )


@router.post("/sync")
async def trigger_garmin_sync(force: bool = Query(True, description="Force sync ignoring existing cache")):
    """Manually triggers an immediate synchronization with Intervals.icu."""
    updated = await garmin_service.sync_sleep_score(force=force)
    return {
        "status": "success",
        "result": updated
    }
