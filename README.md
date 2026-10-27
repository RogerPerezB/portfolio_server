# Portfolio Telemetry Microservice Server

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

A production-grade, asynchronous backend microservice that silently polls external telemetry APIs in the background, persists the latest state into a local JSON database (`data/telemetry_db.json`), and serves instant responses to the portfolio frontend:
1. **Garmin Vitals via Intervals.icu**: Daily sleep score monitoring starting at 8:00 AM ET, polling every 30 minutes until today's score is received, and returning `"No score yet"` before sync completes.
2. **LeetCode Activity via GraphQL**: Cached algorithmic submissions with automatic periodic background synchronization persisted to JSON.

---

## 🏛️ System Design & Architecture

The application decouples frontend `GET` requests from external network calls using a persistent JSON database (`app/core/database.py`):

```
[ Client / Portfolio Frontend ]
              │ (HTTP GET — Instant Read < 2ms)
              ▼
    ┌───────────────────────────────────────────┐
    │          FastAPI Application              │
    │     (Garmin & LeetCode REST Routers)      │
    └─────────────────┬─────────────────────────┘
                      │ Reads Latest State
                      ▼
    ┌───────────────────────────────────────────┐
    │      Local JSON Database + RAM Cache      │
    │          (data/telemetry_db.json)         │
    └─────────▲───────────────────────▲─────────┘
              │ Writes State          │ Writes State
    ┌─────────┴─────────┐   ┌─────────┴─────────┐
    │   GarminService   │   │  LeetCodeService  │
    └─────────▲─────────┘   └─────────▲─────────┘
              │                       │
      [APScheduler]           [APScheduler]
   (Every 30m from 8 AM)      (Every 2 Hours)
              │                       │
              ▼                       ▼
       [Intervals.icu]       [LeetCode GraphQL]
```

### Directory Structure

```text
portfolio_server/
├── app/
│   ├── core/
│   │   ├── config.py           # Typed environment settings
│   │   ├── database.py         # Thread-safe local JSON database (data/telemetry_db.json)
│   │   └── scheduler.py        # Centralized APScheduler (30m Garmin & 2h LeetCode)
│   ├── schemas/
│   │   ├── garmin.py           # Pydantic models for sleep score & telemetry
│   │   └── leetcode.py         # Pydantic models for LeetCode submissions
│   ├── services/
│   │   ├── garmin_service.py   # Intervals.icu background poller & JSON DB reader/writer
│   │   └── leetcode_service.py # LeetCode GraphQL background poller & JSON DB reader/writer
│   └── routers/
│       ├── garmin.py           # GET /api/garmin/sleep, POST /api/garmin/sync
│       └── leetcode.py         # GET /api/leetcode/latest, POST /api/leetcode/sync
├── data/
│   └── telemetry_db.json       # Auto-generated latest telemetry state
├── main.py                     # App entrypoint, lifespan, CORS & health checks
├── Dockerfile                  # Containerization specification
├── docker-compose.yml          # Multi-container / local orchestration
├── requirements.txt            # Python dependencies
└── .env.example                # Documented configuration parameters
```

---

## ⏱️ Garmin Sleep Polling Strategy

```text
  00:00 - 07:59 ET               08:00 - 23:30 ET (Every 30 Minutes)
─────────────────────   ────────────────────────────────────────────────────
Asleep / Vitals Idle    Polls Intervals.icu at :00 and :30 past the hour
(No external polling)   ├─ If sleepScore is not yet available:
                        │   └─ Saves status="no_score_yet", message="No score yet"
                        └─ Once sleepScore is received:
                            └─ Saves score to JSON DB & STOPS checking for the day!
```

- **Timezone Aware**: Configured to `America/Toronto` (Eastern Time).
- **No Premature Polling**: Never polls before 8:00 AM.
- **Self-Terminating Polling**: Checks every 30 minutes starting at 8:00 AM until a valid score is received, then stops checking for the rest of the day.
- **Instant Frontend Reads**: Frontend requests read directly from `data/telemetry_db.json` (and its in-memory mirror) without waiting on Intervals.icu or LeetCode.

---

## 📡 API Endpoints

| Method | Endpoint | Description | Response Model |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/garmin/sleep` | Returns today's sleep state immediately from JSON DB | `GarminSleepResponse` |
| `POST` | `/api/garmin/sync` | Manually triggers immediate Intervals.icu sync | JSON status |
| `GET` | `/api/leetcode/latest`| Returns latest accepted LeetCode submission from JSON DB | `LeetCodeResponse` |
| `POST` | `/api/leetcode/sync` | Manually triggers immediate LeetCode fetch | JSON status |
| `GET` | `/health` | Container orchestration health check | Health object |
| `GET` | `/docs` | Interactive Swagger / OpenAPI documentation | Swagger UI |
