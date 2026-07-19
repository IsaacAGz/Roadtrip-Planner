# Frontend Plan — Roadtrip Planner

Monorepo location: `frontend/` (sibling to `app/`).

## Stack

| Layer | Choice |
|-------|--------|
| Build | Vite |
| UI | React 19 + TypeScript |
| Styling | Tailwind CSS |
| Server state | TanStack Query + SSE (`EventSource`) with polling fallback |
| Map | Leaflet + react-leaflet (OpenStreetMap tiles) |
| Dev API | Vite proxy `/api` → `http://127.0.0.1:8000` |

## Phases

### Phase A (implemented)

- Trip form: origin, destination, dates, preferences, basic constraints
- `POST /trips/plan` → handle **422** (Pydantic + FEAS) and **202** (job id)
- Poll `GET /trips/jobs/{id}` until `completed` or `failed`
- Progress panel (coarse stages)
- Itinerary day cards + validation summary

### Phase B (implemented)

- Advanced constraints accordion (routing, stays, countries, weather)
- Structured preferences (pace, budget, accessibility, interests)
- Progress timeline with step indicators and timestamps
- Copy JSON buttons for job status and completed results

### Phase C (implemented)

- Leaflet map with OpenStreetMap tiles
- Origin (green), overnight stops (blue), destination (red)
- Dashed polyline connecting stop order (approximate path, not OSRM geometry)
- Auto-fit bounds and popups for each marker

### Phase D (implemented)

- SSE live updates via `GET /trips/jobs/{id}/events` (polling fallback if stream fails)
- Recent trips sidebar persisted in `localStorage` (last 20 jobs)
- Mobile-friendly layout: responsive header, full-width submit, shorter map on small screens

## Dev workflow

```powershell
# Terminal 1 — API
python -m uvicorn app.main:app --reload

# Terminal 2 — UI
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — requests go to `/api/*` and proxy to the FastAPI server.

## Production (future)

Option A: `npm run build` → serve `frontend/dist` from FastAPI static files + CORS  
Option B: Deploy UI to static host; enable CORS on API
