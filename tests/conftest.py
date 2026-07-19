import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.job_store import job_store


@pytest.fixture(autouse=True)
def clear_job_store():
    job_store.clear()
    yield
    job_store.clear()


@pytest.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
