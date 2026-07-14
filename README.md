# Roadtrip Planner

AI-powered roadtrip itinerary API. Send a trip request (origin, destination, dates, preferences, constraints) and receive a structured day-by-day plan with OSRM-verified driving segments, stops, overnight stays, and a validation report.

For full architecture and design details, see [PLAN.md](PLAN.md).

## Features

- **Planner agent** — geocodes routes, finds POIs via Wikipedia text search and geosearch, fetches weather, and drafts an itinerary
- **Hard validators** — Python + OSRM checks for driving hours, detours, backtracking, structure, geography, and POI rules
- **Validator agent** — soft checks for pacing, preferences, and weather fit
- **Replan loop** — automatically retries with structured feedback when validation fails
- **Structured JSON** — Pydantic models throughout (not free-form markdown)

## Requirements

- Python 3.11+
- [OpenAI API key](https://platform.openai.com/api-keys) (required)
- [OpenWeatherMap API key](https://openweathermap.org/api) (optional; weather tool degrades gracefully without it)

External services used at runtime (no API key required):

- [Nominatim](https://nominatim.org/) (OpenStreetMap geocoding)
- [OSRM](https://project-osrm.org/) public demo server (routing)
- [Wikipedia API](https://www.mediawiki.org/wiki/API:Main_page) (POI discovery)

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

```powershell
python -m uvicorn app.main:app --reload
```

- Health check: http://127.0.0.1:8000/health
- Interactive API docs: http://127.0.0.1:8000/docs

## API

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| `GET`  | `/health`      | Liveness check                       |
| `POST` | `/trips/plan`  | Generate itinerary + validation      |

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

### Example response

```json
{
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
}
```

If replanning is exhausted, the API still returns **200** with the last draft and `"validation": { "approved": false, "hard_failures": [...] }`.

Invalid request bodies (bad dates, conflicting constraints) return **422** before any agents run.

## Try it with curl

**Git Bash:**

```bash
curl -X POST "http://127.0.0.1:8000/trips/plan" \
  -H "Content-Type: application/json" \
  -d '{"origin":"San Jose, CA","destination":"Monterey, CA","start_date":"2026-07-15","end_date":"2026-07-15","preferences":"direct route, minimal stops","constraints":{"max_replan_attempts":2}}'
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

Invoke-RestMethod -Uri "http://127.0.0.1:8000/trips/plan" -Method POST -ContentType "application/json" -Body $body
```

Planning requests typically take **30 seconds to a few minutes** (LLM calls + external APIs + possible replans).

## Testing

### Unit tests

Unit tests cover validators, request models, and tools. They run without starting the server or calling OpenAI.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

GitHub Actions runs the same test suite on every pull request to `main`.

| Test file | Covers |
|-----------|--------|
| `tests/test_constraints.py` | Cross-field constraint rules, `TripRequest` validation |
| `tests/test_structure.py` | STRUCT-001, STRUCT-002, STRUCT-003, STRUCT-004 |
| `tests/test_routing.py` | ROUTE-001, ROUTE-002 (mocked OSRM) |
| `tests/test_driving.py` | DRIVE-001, DRIVE-002, SCHED-001 (mocked OSRM) |
| `tests/test_geography.py` | GEO-001 country allowlist |
| `tests/test_poi.py` | POI-003 excluded categories |
| `tests/test_warnings.py` | Borderline DRIVE, SCHED, ROUTE warnings |
| `tests/test_wikipedia.py` | Wikipedia geosearch tool (mocked HTTP) |

Run a single file:

```powershell
python -m pytest tests/test_driving.py -v
```

### End-to-end tests

E2E tests hit the live API. Start the server first (`uvicorn`), then send a request via curl or http://127.0.0.1:8000/docs.

Example (Git Bash) — 2-day trip to verify overnight-city rules:

```bash
curl -X POST "http://127.0.0.1:8000/trips/plan" \
  -H "Content-Type: application/json" \
  -d '{"origin":"San Jose, CA","destination":"Monterey, CA","start_date":"2026-07-15","end_date":"2026-07-16","preferences":"relaxed pace, direct coastal route","constraints":{"max_driving_hours_per_day":6.0,"max_stops_per_day":2,"max_replan_attempts":2}}'
```

Check `validation.approved` and that consecutive days use **different** `overnight.city` values unless `allow_extended_stays` is true.

## Constraints

| Field | Default | Notes |
|-------|---------|-------|
| `max_driving_hours_per_day` | 6.0 | Hard cap 8.0 |
| `max_stops_per_day` | 4 | |
| `max_detour_km_per_stop` | 30.0 | |
| `max_backtracking_percent` | 15.0 | Clamped to 25 when `allow_return_stops=true` |
| `allow_extended_stays` | false | Required for multi-night stays in one city |
| `max_nights_per_stop` | 1 | Up to 7 when extended stays enabled |
| `allow_return_stops` | false | Revisit same city on return leg |
| `max_replan_attempts` | 2 | Planner retries on validation failure |
| `allowed_countries` | `["US", "MX"]` | |

Cross-field rules (return **422** if violated):

- `max_nights_per_stop > 1` requires `allow_extended_stays=true`
- `max_nights_per_stop` cannot exceed trip length (days)
- `origin` and `destination` must be non-empty

## Project structure

```
app/
├── main.py              # FastAPI app
├── config.py            # Settings from .env
├── models/              # Pydantic request/response models
├── routers/trips.py     # POST /trips/plan retry loop
├── agents/              # Planner and Validator agents
├── tools/               # LangChain tools (geocode, routing, wiki, weather)
├── services/            # Nominatim and OSRM clients
├── validators/          # Hard validation rules
└── prompts/             # Agent system prompts
```

## Operational notes

- **Nominatim** — rate-limited to 1 request/second; use a descriptive `NOMINATIM_USER_AGENT`
- **OSRM demo server** — suitable for development only; self-host for production
- **Costs** — each `/trips/plan` call uses OpenAI tokens; replans multiply usage

## License

Not specified.
