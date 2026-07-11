from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers.trips import router as trips_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Roadtrip Planner",
    description="AI-powered roadtrip planner with LangChain agents",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(trips_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
