import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.job_store import job_store
from app.services.plan_limits import plan_rate_limiter


@pytest.fixture(autouse=True)
def clear_job_store():
    job_store.clear()
    plan_rate_limiter.clear()
    yield
    job_store.clear()
    plan_rate_limiter.clear()


@pytest.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
