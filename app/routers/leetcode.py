from fastapi import APIRouter, HTTPException, Query
from app.schemas.leetcode import LeetCodeResponse, LeetCodeSubmission
from app.services.leetcode_service import leetcode_service

router = APIRouter(tags=["LeetCode"])


@router.get("/latest", response_model=LeetCodeResponse)
async def get_latest_leetcode():
    """
    Returns the latest accepted LeetCode submission.
    Served via an in-memory asynchronous cache refreshed periodically.
    """
    cache = await leetcode_service.get_latest()
    submission = cache.get("latest_submission")

    if not submission:
        raise HTTPException(status_code=503, detail="Cache warming up or LeetCode unavailable.")

    return LeetCodeResponse(
        source="cache",
        last_updated=cache.get("last_updated") or "",
        data=LeetCodeSubmission(
            title=submission["title"],
            titleSlug=submission["titleSlug"],
            timestamp=str(submission["timestamp"]),
            statusDisplay=submission["statusDisplay"],
            lang=submission["lang"]
        ),
        url=f"https://leetcode.com/problems/{submission['titleSlug']}"
    )


@router.post("/sync")
async def trigger_leetcode_sync(force: bool = Query(True, description="Force sync ignoring existing cache")):
    """Manually triggers an immediate query to LeetCode GraphQL."""
    updated = await leetcode_service.fetch_latest_submission(force=force)
    return {
        "status": "success",
        "result": updated
    }
