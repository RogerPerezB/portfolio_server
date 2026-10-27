import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class Settings:
    PROJECT_NAME: str = "Portfolio Telemetry Server"
    VERSION: str = "1.1.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Local JSON Database path
    DB_FILE_PATH: str = os.getenv(
        "DB_FILE_PATH",
        str(BASE_DIR / "data" / "telemetry_db.json")
    )

    # Garmin / Intervals.icu credentials
    INTERVALS_API_KEY: str = os.getenv("INTERVALS_API_KEY", "")
    INTERVALS_ATHLETE_ID: str = os.getenv("INTERVALS_ATHLETE_ID", "0")

    # LeetCode configuration (Correct handle is rogerpb)
    LEETCODE_USERNAME: str = os.getenv("LEETCODE_USERNAME", "rogerpb")
    LEETCODE_POLL_INTERVAL_HOURS: int = int(os.getenv("LEETCODE_POLL_INTERVAL_HOURS", "2"))

    # Garmin polling configuration (Gatineau, QC Eastern Time)
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Toronto")
    POLL_START_HOUR: int = int(os.getenv("POLL_START_HOUR", "8"))  # Starts checking at 8:00 AM
    GARMIN_POLL_INTERVAL_MINUTES: int = int(os.getenv("GARMIN_POLL_INTERVAL_MINUTES", "30"))

    # CORS
    CORS_ORIGINS: Tuple[str, ...] = ("*",)


settings = Settings()
