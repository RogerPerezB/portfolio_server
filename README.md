# Portfolio Telemetry Microservice Server

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

A production-grade, asynchronous backend microservice designed to ingest, cache, and serve real-time developer telemetry metrics to my portfolio website:
1. **Garmin Vitals via Intervals.icu**: Daily sleep score monitoring with intelligent hourly polling and deterministic fallback.
2. **LeetCode Activity via GraphQL**: Cached algorithmic submissions with automatic periodic background synchronization.

---

## 🏛️ System Design & Architecture

The application adheres to a clean **Layered Architecture** with strict separation of concerns:

```
[ Client / Portfolio Frontend ]
              │ (HTTP / JSON)
              ▼
    ┌───────────────────────────────────────────┐
    │          FastAPI Application              │
    │  (CORS, OpenTelemetry / Health, Routing)   │
    └─────┬───────────────────────────────┬─────┘
          │                               │
          ▼                               ▼
    ┌───────────────┐               ┌───────────────┐
    │ Garmin Router │               │LeetCode Router│
    └───────┬───────┘               └───────┬───────┘
            │                               │
            ▼                               ▼
    ┌───────────────────────┐       ┌───────────────────────┐
    │     GarminService     │       │    LeetCodeService    │
    │ (In-Memory Hot Cache) │       │ (In-Memory Hot Cache) │
    └───────┬───────────────┘       └───────┬───────────────┘
            │                               │
            ├───────────────┐               │
            ▼               ▼               ▼
     [APScheduler]     [Intervals.icu]  [LeetCode GraphQL]
    (8 AM - 1 PM ET)    (REST API v1)    (Submissions API)
```

### Directory Structure

```text
portfolio_server/
├── app/
│   ├── core/
│   │   ├── config.py           # Typed environment settings
│   │   └── scheduler.py        # Centralized APScheduler (Cron & Interval)
│   ├── schemas/
│   │   ├── garmin.py           # Pydantic models for sleep score & telemetry
│   │   └── leetcode.py         # Pydantic models for LeetCode submissions
│   ├── services/
│   │   ├── garmin_service.py   # Intervals.icu client, window polling & caching
│   │   └── leetcode_service.py # LeetCode GraphQL client & caching
│   └── routers/
│       ├── garmin.py           # GET /api/garmin/sleep, POST /api/garmin/sync
│       └── leetcode.py         # GET /api/leetcode/latest, POST /api/leetcode/sync
├── main.py                     # App entrypoint, lifespan, CORS & health checks
├── Dockerfile                  # Containerization specification
├── docker-compose.yml          # Multi-container / local orchestration
├── requirements.txt            # Python dependencies
└── .env.example                # Documented configuration parameters
```

---

## ⏱️ Garmin Sleep Polling Strategy

To minimize external API rate limits and mirror realistic biometric sync patterns from Garmin watches:

```text
  00:00 - 07:59 ET               08:00 - 13:00 ET                     13:01+ ET
─────────────────────   ──────────────────────────────────   ──────────────────────────
Sleeping / Sync Idle    Hourly Polling Window (Every Hour)   Window Closed
                        ├─ Query Intervals.icu API           ├─ If score synced: Return it
                        ├─ If sleepScore found:               └─ If empty: Seal fallback
                        │   └─ Store score & STOP polling!       to default 85 score.
                        └─ If null: Retry next hour.
```

- **Timezone Aware**: Configured to `America/Toronto` (Eastern Time covering Gatineau / Ottawa / Montreal).
- **Self-Terminating Polling**: Once today's valid score is retrieved, subsequent polls in that day are immediately skipped (*"stops asking once filled"*).
- **Graceful Fallback**: If Garmin sync is delayed past 1:00 PM, the service seals a deterministic default score of **85** (`is_default: true`) so client applications never stall.

---

## 📡 API Endpoints

| Method | Endpoint | Description | Response Model |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/garmin/sleep` | Returns today's sleep score (synced or fallback) | `GarminSleepResponse` |
| `POST` | `/api/garmin/sync` | Manually triggers immediate Intervals.icu sync | JSON status |
| `GET` | `/api/leetcode/latest`| Returns latest accepted LeetCode submission | `LeetCodeResponse` |
| `POST` | `/api/leetcode/sync` | Manually triggers immediate LeetCode fetch | JSON status |
| `GET` | `/health` | Container orchestration health check | Health object |
| `GET` | `/docs` | Interactive Swagger / OpenAPI documentation | Swagger UI |

---

## 🚀 Quickstart & Local Development

### 1. Prerequisites
- Python 3.10+ or Docker
- Intervals.icu API key (from Intervals.icu -> Settings -> API Access)

### 2. Local Environment Setup
```bash
# Clone and enter the repository
cd portfolio_server

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run the development server
uvicorn main:app --reload --port 8000
```

### 3. Running with Docker
```bash
# Build and run container
docker build -t portfolio-telemetry-server .
docker run -p 8000:8000 --env-file .env portfolio-telemetry-server

# Or with Docker Compose:
docker compose up --build
```
