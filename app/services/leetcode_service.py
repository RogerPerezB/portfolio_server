import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict
import httpx

from app.core.config import settings
from app.core.database import db

logger = logging.getLogger("leetcode_service")


class LeetCodeService:
    def __init__(self):
        self._sync_lock = asyncio.Lock()

    async def fetch_latest_submission(self, force: bool = False) -> Dict[str, Any]:
        """Fetches the latest accepted submission from LeetCode's public GraphQL API and saves it to the JSON DB."""
        async with self._sync_lock:
            if not settings.LEETCODE_USERNAME:
                logger.warning("[LeetCodeService] LEETCODE_USERNAME is not configured.")
                return db.get_leetcode()

            url = "https://leetcode.com/graphql"
            query = """
            query getRecentSubmissionList($username: String!, $limit: Int!) {
              recentSubmissionList(username: $username, limit: $limit) {
                title
                titleSlug
                timestamp
                statusDisplay
                lang
              }
            }
            """

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": "https://leetcode.com/",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(headers=headers, timeout=12.0) as client:
                try:
                    logger.info(f"[LeetCodeService] Polling LeetCode for user: {settings.LEETCODE_USERNAME}...")
                    response = await client.post(
                        url,
                        json={
                            "query": query,
                            "variables": {"username": settings.LEETCODE_USERNAME, "limit": 20}
                        }
                    )

                    if response.status_code != 200:
                        logger.error(f"[LeetCodeService] LeetCode request failed with status: {response.status_code}")
                        return db.get_leetcode()

                    data = response.json()
                    submissions = data.get("data", {}).get("recentSubmissionList", [])

                    # Find the most recent accepted submission
                    accepted = [sub for sub in submissions if sub.get("statusDisplay") == "Accepted"]

                    if accepted:
                        updated_state = {
                            "latest_submission": accepted[0],
                            "last_updated": datetime.now(timezone.utc).isoformat(),
                            "status": "synced"
                        }
                        db.save_leetcode(updated_state)
                        logger.info(f"[LeetCodeService] JSON DB updated with: {accepted[0]['title']}")
                        return updated_state
                    else:
                        logger.info(
                            f"[LeetCodeService] No accepted submissions found in the last 20 tries "
                            f"for {settings.LEETCODE_USERNAME}."
                        )

                except Exception as e:
                    logger.error(f"[LeetCodeService] Failed to fetch LeetCode data: {e}")

            return db.get_leetcode()

    async def get_latest(self) -> Dict[str, Any]:
        """Returns the latest submission immediately from the local JSON database."""
        cached = db.get_leetcode()
        if not cached.get("latest_submission"):
            # Trigger non-blocking background fetch if DB is completely empty
            asyncio.create_task(self.fetch_latest_submission())
        return cached


leetcode_service = LeetCodeService()
