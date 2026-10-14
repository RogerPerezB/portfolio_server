import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Settings:
    PROJECT_NAME: str = "Portfolio Telemetry Server"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Garmin / Intervals.icu credentials
    INTERVALS_API_KEY: str = os.getenv("INTERVALS_API_KEY", "")
    INTERVALS_ATHLETE_ID: str = os.getenv("INTERVALS_ATHLETE_ID", "0")
    
    # LeetCode configuration
    LEETCODE_USERNAME: str = os.getenv("LEETCODE_USERNAME", "RogerPerezB")
    LEETCODE_POLL_INTERVAL_HOURS: int = int(os.getenv("LEETCODE_POLL_INTERVAL_HOURS", "2"))

    # Garmin polling window & defaults (Gatineau, QC Eastern Time)
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Toronto")
    DEFAULT_SLEEP_SCORE: int = int(os.getenv("DEFAULT_SLEEP_SCORE", "85"))
    POLL_START_HOUR: int = int(os.getenv("POLL_START_HOUR", "8"))   # 8:00 AM
    POLL_END_HOUR: int = int(os.getenv("POLL_END_HOUR", "13"))      # 1:00 PM

    # CORS
    CORS_ORIGINS: List[str] = ("*",)


settings = Settings()
