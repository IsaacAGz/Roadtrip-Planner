# Roadtrip Planner

AI-powered roadtrip itinerary API. Send a trip request (origin, destination, dates, preferences, constraints) and receive a structured day-by-day plan with OSRM-verified driving segments, stops, overnight stays, and a validation report.

For full architecture and design details, see [PLAN.md](PLAN.md).

## Features

- **Planner agent** — geocodes routes, finds POIs via OpenStreetMap (Overpass) and Wikipedia, fetches weather, and drafts an itinerary
- **Feasibility pre-check** — geocodes endpoints and queries OSRM before any LLM calls; returns **422** for impossible trips (FEAS-001/002/003)
- **Hard validators** — Python + OSRM checks for driving hours, detours, backtracking, structure, geography, and POI rules
- **Validator agent** — soft checks for pacing, preferences, and weather fit
- **Async planning jobs** — `POST /trips/plan` returns immediately with a job ID; poll for progress and result
- **Replan loop** — automatically retries with structured, rule-specific feedback when validation fails
- **Plan enrichment** — deterministic repair of legs, OSRM driving hours, and stop placement before hard validation
- **Trip scaffold** — OSRM route-geometry daily leg targets injected into planner prompts (one-way trips)
- **Scaffold validation (SCAFFOLD-001)** — fails doomed jobs before LLM when a daily leg exceeds the driving cap
- **Web UI** — React app in `frontend/` (form, preferences, constraints, live progress via SSE, job history, OSM route map, itinerary view)
- **Structured JSON** — Pydantic models throughout (not free-form markdown)

## Requirements

- Python 3.11+
- [OpenAI API key](https://platform.openai.com/api-keys) (required)
- [OpenWeatherMap API key](https://openweathermap.org/api) (optional; weather tool degrades gracefully without it)

External services used at runtime (no API key required):

- [Nominatim](https://nominatim.org/) (OpenStreetMap geocoding)
- [OSRM](https://project-osrm.org/) public demo server (routing)
- [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) (OpenStreetMap POI discovery)
- [Wikipedia API](https://www.mediawiki.org/wiki/API:Main_page) (notable landmarks and descriptions)

## Setup

```powershell
cd Roadtrip-Planner
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...

# Optional but recommended
OPENWEATHER_API_KEY=...
NOMINATIM_USER_AGENT=RoadtripPlanner/1.0 (you@example.com)

# Optional — LangSmith tracing
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=Roadtrip_Planner
```

## Run

**API server:**

```powershell
python -m uvicorn app.main:app --reload
```

- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Interactive API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

**Web UI (Phase A):**

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The dev server proxies `/api/*` to the FastAPI backend on port 8000, so run both processes locally.

The UI supports structured preferences, an advanced constraints panel, a visual planning timeline, SSE live job updates (with polling fallback), local recent-trip history, an OpenStreetMap route map, and copy-to-clipboard JSON for debugging.

See [frontend/PLAN.md](frontend/PLAN.md) for UI architecture and future phases.

## API


| Method | Path                    | Description                                      |
| ------ | ----------------------- | ------------------------------------------------ |
| `GET`  | `/health`               | Liveness check                                   |
| `POST` | `/trips/plan`           | Start async planning job (**202** + `job_id`)    |
| `GET`  | `/trips/jobs/{job_id}`  | Poll job status, progress, and result            |
| `GET`  | `/trips/jobs/{job_id}/events` | SSE stream of job updates (`text/event-stream`) |


**Request pipeline:** Pydantic validation → feasibility pre-check (Nominatim + OSRM) → background replan loop (Planner → hard validators → Validator agent).

Feasibility and validation errors still return **422** synchronously before a job is created.

### Example request

```json
{
  "origin": "San Jose, CA",
  "destination": "Monterey, CA",
  "start_date": "2026-07-15",
  "end_date": "2026-07-15",
  "preferences": "direct route, minimal stops",
  "constraints": {
    "max_driving_hours_per_day": 6.0,
    "max_replan_attempts": 2
  }
}
```

### Start planning (202 Accepted)

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "queued",
  "status_url": "/trips/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "events_url": "/trips/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6/events"
}
```

Subscribe to `GET /trips/jobs/{job_id}/events` for live updates, or poll `GET /trips/jobs/{job_id}` until `status` is `completed` or `failed`.

### Completed job response

When `status` is `completed`, the `result` field contains the full trip payload:

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "completed",
  "progress": [
    { "stage": "queued", "message": "Planning job queued", "attempt": null, "timestamp": "..." },
    { "stage": "planning", "message": "Running planner", "attempt": 0, "timestamp": "..." },
    { "stage": "hard_validation", "message": "Running hard validators", "attempt": 0, "timestamp": "..." },
    { "stage": "soft_validation", "message": "Running validator agent", "attempt": 0, "timestamp": "..." },
    { "stage": "completed", "message": "Planning completed", "attempt": null, "timestamp": "..." }
  ],
  "result": {
    "plan": {
      "title": "...",
      "total_days": 1,
      "days": [...],
      "tips": [...]
    },
    "validation": {
      "approved": true,
      "hard_failures": [],
      "warnings": [],
      "replan_attempts": 0
    },
    "replan_attempts": 0
  },
  "error": null
}
```

If replanning is exhausted, the job still completes with `"validation": { "approved": false, "hard_failures": [...] }` inside `result`.

**422 responses** (before any agents run):

1. **Pydantic / cross-field constraints** — bad dates, conflicting `max_nights_per_stop`, empty origin/destination, etc.
2. **Feasibility pre-check (FEAS-001/002/003)** — impossible trip length, geocode/country failures, or OSRM routing failure

Impossible trips (e.g. San Diego → Portland in 2 days at 6 h/day) are rejected by the feasibility pre-check. It geocodes endpoints and queries OSRM driving time, adding ~2 seconds before planning starts but avoiding LLM calls on mathematically impossible requests.

Example **422** for an under-length trip:

```json
{
  "detail": {
    "rule_id": "FEAS-001",
    "message": "Trip requires at least 3 driving days at 6.0h/day (OSRM one-way 17.0h) but request allows 2 days",
    "actual": 2,
    "limit": 3
  }
}
```

| Rule | Meaning |
|------|---------|
| FEAS-001 | Trip days shorter than minimum driving days (OSRM one-way hours ÷ `max_driving_hours_per_day`; doubled when `allow_return_stops=true`) |
| FEAS-002 | Origin/destination geocode failure, or endpoint country not in `allowed_countries` |
| FEAS-003 | OSRM cannot find a driving route between endpoints |

## Try it with curl

**Git Bash:**

```bash
# Start job
curl -s -X POST "http://127.0.0.1:8000/trips/plan" \
  -H "Content-Type: application/json" \
  -d '{"origin":"San Jose, CA","destination":"Monterey, CA","start_date":"2026-07-15","end_date":"2026-07-15","preferences":"direct route, minimal stops","constraints":{"max_replan_attempts":2}}'

# Poll until completed (replace JOB_ID)
curl -s "http://127.0.0.1:8000/trips/jobs/JOB_ID"
```

**PowerShell:**

```powershell
$body = @{
  origin = "San Jose, CA"
  destination = "Monterey, CA"
  start_date = "2026-07-15"
  end_date = "2026-07-15"
  preferences = "direct route, minimal stops"
  constraints = @{ max_replan_attempts = 2 }
} | ConvertTo-Json -Depth 5

$job = Invoke-RestMethod -Uri "http://127.0.0.1:8000/trips/plan" -Method POST -ContentType "application/json" -Body $body
$jobId = $job.job_id

do {
  Start-Sleep -Seconds 2
  $status = Invoke-RestMethod -Uri "http://127.0.0.1:8000/trips/jobs/$jobId"
} while ($status.status -notin @("completed", "failed"))

$status
```

Planning jobs typically take **30 seconds to a few minutes** (LLM calls + external APIs + possible replans). Poll every few seconds until `status` is `completed` or `failed`. Feasibility-only **422** responses return synchronously in a few seconds (two Nominatim calls + one OSRM call).

## Testing

### Unit tests

Unit tests cover validators, request models, tools, and HTTP endpoints. They run without starting the server or calling OpenAI.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

GitHub Actions runs the same test suite on every pull request to `main`.


| Test file                   | Covers                                                 |
| --------------------------- | ------------------------------------------------------ |
| `tests/test_constraints.py` | Cross-field constraint rules, `TripRequest` validation |
| `tests/test_structure.py`   | STRUCT-001, STRUCT-002, STRUCT-003, STRUCT-004         |
| `tests/test_routing.py`     | ROUTE-001, ROUTE-002 (mocked OSRM)                     |
| `tests/test_driving.py`     | DRIVE-001, DRIVE-002, SCHED-001 (mocked OSRM)          |
| `tests/test_geography.py`   | GEO-001 country allowlist                              |
| `tests/test_poi.py`         | POI-003 excluded categories                            |
| `tests/test_warnings.py`    | Borderline DRIVE, SCHED, ROUTE warnings                |
| `tests/test_wikipedia.py`   | Wikipedia geosearch tool (mocked HTTP)                 |
| `tests/test_overpass.py`    | Overpass OSM POI tool (mocked HTTP)                    |
| `tests/test_weather_validator.py` | WEATHER-001 outdoor forecast checks (mocked)     |
| `tests/test_feasibility.py`   | FEAS-001/002/003 pre-check + router 422 (mocked) |
| `tests/test_api_integration.py` | HTTP API tests for `/health`, `/trips/plan`, `/trips/jobs/{id}`, SSE events |
| `tests/test_job_store.py`       | In-memory job store + subscriber notifications                 |
| `tests/test_planning_job.py`    | Background planning service + progress events                  |
| `tests/test_plan_enrichment.py` | Deterministic plan repair before hard validation               |
| `tests/test_trip_scaffold.py`   | OSRM daily leg scaffold + SCAFFOLD-001 validation              |
| `tests/test_osrm_geometry.py`   | Polyline decode + geometry-based route splitting               |
| `tests/test_replan_feedback.py` | Structured replan feedback templates                           |
| `tests/test_soft_precheck.py`   | Relaxed-pace warning pre-check                                 |


Run a single file:

```powershell
python -m pytest tests/test_driving.py -v
```

### End-to-end tests

E2E tests hit the live API. Start the server first (`uvicorn`), then send a request via curl or [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Example (Git Bash) — 2-day trip to verify overnight-city rules:

```bash
curl -X POST "http://127.0.0.1:8000/trips/plan" \
  -H "Content-Type: application/json" \
  -d '{"origin":"San Diego, CA","destination":"Portland, OR","start_date":"2026-07-15","end_date":"2026-07-18","preferences":"relaxed pace, direct coastal route","constraints":{"max_driving_hours_per_day":6.0,"max_stops_per_day":2,"max_replan_attempts":2}}'
```

Check `validation.approved` and that consecutive days use **different** `overnight.city` values unless `allow_extended_stays` is true.

Example (Git Bash) — infeasible trip (expect **422 FEAS-001** in a few seconds, no plan JSON):

```bash
curl -X POST "http://127.0.0.1:8000/trips/plan" \
  -H "Content-Type: application/json" \
  -d '{"origin":"San Diego, CA","destination":"Portland, OR","start_date":"2026-07-15","end_date":"2026-07-16","constraints":{"max_driving_hours_per_day":6.0}}'
```

PowerShell equivalent:

```powershell
$body = @{
  origin = "San Diego, CA"
  destination = "Portland, OR"
  start_date = "2026-07-15"
  end_date = "2026-07-16"
  constraints = @{ max_driving_hours_per_day = 6.0 }
} | ConvertTo-Json -Depth 5

try { Invoke-RestMethod -Uri "http://127.0.0.1:8000/trips/plan" -Method POST -ContentType "application/json" -Body $body }
catch { $_.ErrorDetails.Message }
```

## Constraints


| Field                       | Default        | Notes                                        |
| --------------------------- | -------------- | -------------------------------------------- |
| `max_driving_hours_per_day` | 6.0            | Hard cap 8.0                                 |
| `max_stops_per_day`         | 4              |                                              |
| `max_detour_km_per_stop`    | 30.0           |                                              |
| `max_backtracking_percent`  | 15.0           | Clamped to 25 when `allow_return_stops=true` |
| `allow_extended_stays`      | false          | Required for multi-night stays in one city   |
| `max_nights_per_stop`       | 1              | Up to 7 when extended stays enabled          |
| `allow_return_stops`        | false          | Revisit same city on return leg              |
| `max_replan_attempts`       | 2              | Planner retries on validation failure        |
| `allowed_countries`         | `["US", "MX"]` |                                              |
| `fail_on_weather_warnings`  | false          | Hard-check outdoor days against forecast     |
| `max_precip_chance`         | 0.5            | Max daily rain probability (0–1)             |
| `min_temp_c`                | 10.0           | Min daily low temp (°C) for outdoor days     |


Cross-field rules (return **422** if violated):

- `max_nights_per_stop > 1` requires `allow_extended_stays=true`
- `max_nights_per_stop` cannot exceed trip length (days)
- `origin` and `destination` must be non-empty

Feasibility rules (return **422** before LLM, after Pydantic validation; implemented in `app/validators/feasibility.py`):

- **FEAS-001:** Trip shorter than minimum driving days from OSRM one-way time (hours doubled when `allow_return_stops=true`)
- **FEAS-002:** Geocode failure or endpoint country outside `allowed_countries`
- **FEAS-003:** OSRM cannot route between geocoded endpoints

These are a **lower bound** — detours and stops only increase required time. Post-plan GEO-001 and DRIVE-001 still run on the generated itinerary.

## Project structure

```
app/
├── main.py              # FastAPI app
├── config.py            # Settings from .env
├── models/              # Pydantic request/response models
├── routers/trips.py     # POST /trips/plan + GET /trips/jobs/{id} + SSE events
├── agents/              # Planner and Validator agents
├── tools/               # LangChain tools (geocode, routing, overpass, wiki, weather)
├── services/            # Nominatim, OSRM, job store, scaffold, enrichment, planning jobs
├── validators/          # FEAS pre-check + hard validation (incl. WEATHER-001)
└── prompts/             # Agent system prompts

frontend/
├── PLAN.md              # UI phases and stack
├── src/                 # React + TypeScript (Vite, Tailwind, TanStack Query)
└── vite.config.ts       # Dev proxy /api → http://127.0.0.1:8000
```

## Operational notes

- **Async planning jobs** — in-memory job store with pub/sub for SSE (dev/MVP); jobs lost on server restart
- **Feasibility pre-check** — always runs on `POST /trips/plan`; uses Nominatim (2 calls at 1 req/sec) + OSRM before any OpenAI usage
- **Nominatim** — rate-limited to 1 request/second; use a descriptive `NOMINATIM_USER_AGENT`
- **Overpass API** — public demo server is rate-limited; suitable for development only
- **OSRM demo server** — suitable for development only; self-host for production
- **Costs** — each `/trips/plan` call uses OpenAI tokens; replans multiply usage

## License

Not specified.