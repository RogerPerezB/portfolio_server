from typing import Optional
from pydantic import BaseModel, Field


class SleepData(BaseModel):
    score: Optional[int] = Field(None, description="Daily sleep score (0-100), or null if no score yet", ge=0, le=100)
    date: str = Field(..., description="Date of the sleep record (YYYY-MM-DD)")
    duration_seconds: Optional[int] = Field(None, description="Sleep duration in seconds")
    hrv: Optional[float] = Field(None, description="Heart rate variability measurement")
    is_default: bool = Field(False, description="Deprecated flag kept for frontend schema compatibility (always False)")
    status: str = Field(..., description="Status of the record (asleep, no_score_yet, synced)")
    message: Optional[str] = Field(None, description="Human-readable status (e.g., 'No score yet')")


class GarminSleepResponse(BaseModel):
    source: str = Field(..., description="Origin of the data (garmin_sync, garmin_telemetry, json_db)")
    last_updated: str = Field(..., description="ISO 8601 timestamp of last database update")
    data: SleepData
