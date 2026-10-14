import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.scheduler import scheduler, setup_scheduler
from app.routers.garmin import router as garmin_router
from app.routers.leetcode import router as leetcode_router
from app.services.garmin_service import garmin_service
from app.services.leetcode_service import leetcode_service

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan:
    1. Sets up and starts the periodic scheduler (Garmin hourly window & LeetCode interval).
    2. Runs initial background warm-ups for cache responsiveness.
    3. Handles graceful shutdown.
    """
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    
    # 1. Initialize background jobs
    setup_scheduler()
    scheduler.start()

    # 2. Warm up caches asynchronously without blocking server start
    asyncio.create_task(leetcode_service.fetch_latest_submission())
    asyncio.create_task(garmin_service.sync_sleep_score())

    yield

    # 3. Graceful shutdown
    logger.info("Shutting down background scheduler...")
    scheduler.shutdown(wait=False)
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-grade asynchronous microservice caching LeetCode solves and Garmin sleep telemetry.",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(leetcode_router, prefix="/api/leetcode")
app.include_router(garmin_router, prefix="/api/garmin")


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for cloud load balancers and container orchestrators."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "scheduler_running": scheduler.running,
        "timezone": settings.TIMEZONE
    }


@app.get("/", tags=["System"])
async def root():
    """API overview and interactive docs pointer."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "endpoints": {
            "leetcode_latest": "/api/leetcode/latest",
            "garmin_sleep": "/api/garmin/sleep",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
