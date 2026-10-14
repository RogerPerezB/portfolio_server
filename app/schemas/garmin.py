from typing import Optional
from pydantic import BaseModel, Field


class SleepData(BaseModel):
    score: Optional[int] = Field(None, description="Daily sleep score (0-100)", ge=0, le=100)
    date: str = Field(..., description="Date of the sleep record (YYYY-MM-DD)")
    duration_seconds: Optional[int] = Field(None, description="Sleep duration in seconds")
    hrv: Optional[float] = Field(None, description="Heart rate variability measurement")
    is_default: bool = Field(False, description="Whether this score was populated by default fallback")
    status: str = Field(..., description="Status of the record (asleep, synced, awaiting_sync, default_fallback)")
    message: Optional[str] = Field(None, description="Informational message about the sync state")


class GarminSleepResponse(BaseModel):
    source: str = Field(..., description="Origin of the data (garmin_telemetry, garmin_sync, default_fallback, cache)")
    last_updated: str = Field(..., description="ISO 8601 timestamp of last cache update")
    data: SleepData
