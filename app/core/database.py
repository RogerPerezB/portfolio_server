import json
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger("database")


class JsonDatabase:
    """
    Lightweight persistent JSON store backed by an in-memory cache.
    Background jobs write to disk and update memory; frontend GET requests
    read instantaneously from memory/disk without blocking on external APIs.
    """

    def __init__(self, db_path: str):
        self.file_path = Path(db_path)
        self._lock = Lock()
        self._state: Dict[str, Any] = {
            "garmin": {
                "score": None,
                "date": None,
                "duration_seconds": None,
                "hrv": None,
                "is_default": False,
                "status": "no_score_yet",
                "last_updated": None,
                "source": "json_db",
                "message": "No score yet"
            },
            "leetcode": {
                "latest_submission": None,
                "last_updated": None,
                "status": "uninitialized"
            }
        }
        self._load_from_disk()

    def _ensure_dir(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_from_disk(self) -> None:
        with self._lock:
            self._ensure_dir()
            if self.file_path.exists():
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    if isinstance(loaded, dict):
                        if "garmin" in loaded and isinstance(loaded["garmin"], dict):
                            self._state["garmin"].update(loaded["garmin"])
                        if "leetcode" in loaded and isinstance(loaded["leetcode"], dict):
                            self._state["leetcode"].update(loaded["leetcode"])
                    logger.info(f"[JsonDatabase] Loaded persistent state from {self.file_path}")
                except Exception as e:
                    logger.error(f"[JsonDatabase] Failed to read {self.file_path}, initializing fresh state: {e}")
                    self._write_to_disk_unlocked()
            else:
                self._write_to_disk_unlocked()
                logger.info(f"[JsonDatabase] Initialized new JSON database at {self.file_path}")

    def _write_to_disk_unlocked(self) -> None:
        try:
            self._ensure_dir()
            tmp_path = self.file_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
            os.replace(tmp_path, self.file_path)
        except Exception as e:
            logger.error(f"[JsonDatabase] Failed to write state to {self.file_path}: {e}")

    def get_garmin(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._state["garmin"])

    def save_garmin(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._state["garmin"] = dict(data)
            self._write_to_disk_unlocked()
            return dict(self._state["garmin"])

    def get_leetcode(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._state["leetcode"])

    def save_leetcode(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._state["leetcode"] = dict(data)
            self._write_to_disk_unlocked()
            return dict(self._state["leetcode"])


db = JsonDatabase(settings.DB_FILE_PATH)
