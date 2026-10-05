import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass

from starlette.requests import Request

CONCURRENT_RETRY_AFTER_SECONDS = 60


@dataclass(frozen=True)
class RateLimitRejection:
    message: str
    retry_after: int


class PlanRateLimiter:
    """In-memory sliding window for plan starts. One process, one budget."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.time
        self._ip_hits: dict[str, deque[float]] = defaultdict(deque)
        self._global_hits: deque[float] = deque()

    def clear(self) -> None:
        self._ip_hits.clear()
        self._global_hits.clear()

    def reject_if_over_cap(
        self,
        client_id: str,
        *,
        per_ip: int,
        global_limit: int,
        window_seconds: int,
    ) -> RateLimitRejection | None:
        now = self._clock()
        self._prune(now, window_seconds)
        ip_hits = self._ip_hits.get(client_id)
        ip_count = len(ip_hits) if ip_hits is not None else 0
        if ip_count >= per_ip:
            retry_after = _retry_after(ip_hits, now, window_seconds)
            return RateLimitRejection(
                message=(
                    f"This network has reached the limit of {per_ip} "
                    f"{_plan_noun(per_ip)} per {_window_phrase(window_seconds)}. "
                    f"Try again in {_retry_phrase(retry_after)}."
                ),
                retry_after=retry_after,
            )
        if len(self._global_hits) >= global_limit:
            retry_after = _retry_after(self._global_hits, now, window_seconds)
            return RateLimitRejection(
                message=(
                    f"The planner has reached its limit of {global_limit} "
                    f"{_plan_noun(global_limit)} per {_window_phrase(window_seconds)}. "
                    f"Try again in {_retry_phrase(retry_after)}."
                ),
                retry_after=retry_after,
            )
        return None

    def record(self, client_id: str) -> None:
        now = self._clock()
        self._ip_hits[client_id].append(now)
        self._global_hits.append(now)

    def _prune(self, now: float, window_seconds: int) -> None:
        cutoff = now - window_seconds
        for client_id in list(self._ip_hits):
            hits = self._ip_hits[client_id]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if not hits:
                del self._ip_hits[client_id]
        while self._global_hits and self._global_hits[0] <= cutoff:
            self._global_hits.popleft()


plan_rate_limiter = PlanRateLimiter()


def client_address(request: Request, *, trust_proxy: bool) -> str:
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def concurrent_rejection(limit: int) -> RateLimitRejection:
    if limit == 1:
        message = "1 plan is already running. Try again in 1 minute."
    else:
        message = f"{limit} plans are already running. Try again in 1 minute."
    return RateLimitRejection(message=message, retry_after=CONCURRENT_RETRY_AFTER_SECONDS)


def _retry_after(hits: deque[float] | None, now: float, window_seconds: int) -> int:
    if not hits:
        return window_seconds
    return max(1, math.ceil(hits[0] + window_seconds - now))


def _plan_noun(count: int) -> str:
    return "plan" if count == 1 else "plans"


def _window_phrase(window_seconds: int) -> str:
    if window_seconds == 86_400:
        return "24 hours"
    if window_seconds % 3600 == 0:
        hours = window_seconds // 3600
        return "1 hour" if hours == 1 else f"{hours} hours"
    return f"{window_seconds} seconds"


def _retry_phrase(seconds: int) -> str:
    if seconds < 60:
        unit = "second" if seconds == 1 else "seconds"
        return f"{seconds} {unit}"
    if seconds < 3600:
        minutes = max(1, math.ceil(seconds / 60))
        unit = "minute" if minutes == 1 else "minutes"
        return f"{minutes} {unit}"
    hours = max(1, math.ceil(seconds / 3600))
    unit = "hour" if hours == 1 else "hours"
    return f"{hours} {unit}"
