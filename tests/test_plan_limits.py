from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request

from app.config import get_settings
from app.services.job_store import job_store
from app.services.plan_limits import PlanRateLimiter, client_address
from tests.test_api_integration import FakeNominatimClient, _plan_payload, mock_feasibility_services


def _settings(**overrides):
    return get_settings().model_copy(update=overrides)


def _http_request(host: str = "10.0.0.8", forwarded: str | None = None) -> Request:
    headers = []
    if forwarded is not None:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": (host, 5000),
            "server": ("test", 80),
        }
    )


class CountingNominatim(FakeNominatimClient):
    def __init__(self) -> None:
        super().__init__(locations={})
        self.calls = 0

    async def geocode(self, query: str):
        self.calls += 1
        return await super().geocode(query)


def test_daily_window_frees_a_slot_when_it_expires():
    clock = {"now": 1_000_000.0}
    limiter = PlanRateLimiter(clock=lambda: clock["now"])

    assert (
        limiter.reject_if_over_cap("10.0.0.8", per_ip=1, global_limit=10, window_seconds=100)
        is None
    )
    limiter.record("10.0.0.8")

    rejected = limiter.reject_if_over_cap(
        "10.0.0.8", per_ip=1, global_limit=10, window_seconds=100
    )
    assert rejected is not None
    assert rejected.retry_after == 100
    assert "limit of 1 plan " in rejected.message

    clock["now"] += 100
    assert (
        limiter.reject_if_over_cap("10.0.0.8", per_ip=1, global_limit=10, window_seconds=100)
        is None
    )


def test_global_cap_applies_across_clients():
    limiter = PlanRateLimiter(clock=lambda: 50.0)
    limiter.record("a")
    limiter.record("b")

    rejected = limiter.reject_if_over_cap("c", per_ip=5, global_limit=2, window_seconds=86_400)
    assert rejected is not None
    assert "limit of 2 plans " in rejected.message


def test_client_address_ignores_forwarded_header_unless_trusted():
    request = _http_request(forwarded="1.1.1.1, 2.2.2.2")

    assert client_address(request, trust_proxy=False) == "10.0.0.8"
    assert client_address(request, trust_proxy=True) == "1.1.1.1"


def test_client_address_falls_back_when_forwarded_header_is_empty():
    request = _http_request(forwarded="   ")

    assert client_address(request, trust_proxy=True) == "10.0.0.8"


@pytest.mark.asyncio
async def test_failed_feasibility_counts_and_over_cap_skips_geocoding(api_client):
    nominatim = CountingNominatim()
    settings = _settings(plan_daily_limit_per_ip=1, plan_daily_limit_global=30)

    with (
        patch("app.routers.trips.get_settings", return_value=settings),
        mock_feasibility_services(nominatim=nominatim),
    ):
        first = await api_client.post("/trips/plan", json=_plan_payload())
        second = await api_client.post(
            "/trips/plan",
            json=_plan_payload(),
            headers={"X-Forwarded-For": "9.9.9.9"},
        )

    assert first.status_code == 422
    assert first.json()["detail"]["rule_id"] == "FEAS-002"
    assert second.status_code == 429
    assert second.headers["retry-after"]
    assert "limit of 1 plan " in second.json()["detail"]
    assert nominatim.calls == 1


@pytest.mark.asyncio
async def test_trusted_proxy_header_splits_daily_caps(api_client):
    nominatim = CountingNominatim()
    settings = _settings(
        plan_daily_limit_per_ip=1,
        plan_daily_limit_global=10,
        trust_x_forwarded_for=True,
    )

    with (
        patch("app.routers.trips.get_settings", return_value=settings),
        mock_feasibility_services(nominatim=nominatim),
    ):
        first = await api_client.post(
            "/trips/plan",
            json=_plan_payload(),
            headers={"X-Forwarded-For": "1.1.1.1"},
        )
        second = await api_client.post(
            "/trips/plan",
            json=_plan_payload(),
            headers={"X-Forwarded-For": "2.2.2.2"},
        )
        third = await api_client.post(
            "/trips/plan",
            json=_plan_payload(),
            headers={"X-Forwarded-For": "1.1.1.1"},
        )

    assert first.status_code == 422
    assert second.status_code == 422
    assert third.status_code == 429
    assert nominatim.calls == 2


@pytest.mark.asyncio
async def test_concurrent_jobs_block_new_plans_until_one_finishes(api_client):
    settings = _settings(plan_daily_limit_per_ip=10, plan_max_concurrent_jobs=1)
    run_job = AsyncMock()

    with (
        patch("app.routers.trips.get_settings", return_value=settings),
        patch("app.routers.trips.run_planning_job", run_job),
        mock_feasibility_services(),
    ):
        started = await api_client.post("/trips/plan", json=_plan_payload())
        blocked = await api_client.post("/trips/plan", json=_plan_payload())
        job_store.fail(started.json()["job_id"], "stopped for test")
        retried = await api_client.post("/trips/plan", json=_plan_payload())

    assert started.status_code == 202
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "60"
    assert blocked.json()["detail"] == "1 plan is already running. Try again in 1 minute."
    assert retried.status_code == 202
    assert run_job.await_count == 2

    status = await api_client.get(f"/trips/jobs/{started.json()['job_id']}")
    assert status.status_code == 200
