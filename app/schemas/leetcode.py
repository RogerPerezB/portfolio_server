from pydantic import BaseModel, Field


class LeetCodeSubmission(BaseModel):
    title: str = Field(..., description="Problem title")
    titleSlug: str = Field(..., description="Problem URL slug")
    timestamp: str = Field(..., description="Unix timestamp of submission")
    statusDisplay: str = Field(..., description="Status string (e.g. Accepted)")
    lang: str = Field(..., description="Programming language used for solution")


class LeetCodeResponse(BaseModel):
    source: str = Field(..., description="Origin of the data (cache)")
    last_updated: str = Field(..., description="ISO 8601 timestamp of last cache update")
    data: LeetCodeSubmission
    url: str = Field(..., description="Direct link to the problem on LeetCode")
