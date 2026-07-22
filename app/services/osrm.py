import math
from dataclasses import dataclass

import httpx

from app.config import get_settings
from app.services.nominatim import LatLon

OSRM_MIN_DISTANCE_KM = 0.001
EARTH_RADIUS_KM = 6371.0


@dataclass
class RouteResult:
    distance_km: float
    duration_hours: float


@dataclass
class RouteGeometry:
    distance_km: float
    duration_hours: float
    coordinates: list[LatLon]


@dataclass
class LegSegment:
    start: LatLon
    end: LatLon
    duration_hours: float
    distance_km: float


def decode_polyline(encoded: str) -> list[LatLon]:
    coordinates: list[LatLon] = []
    index = 0
    lat = 0
    lon = 0

    while index < len(encoded):
        shift = 0
        result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += delta_lat

        shift = 0
        result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lon = ~(result >> 1) if (result & 1) else (result >> 1)
        lon += delta_lon

        coordinates.append((lat / 1e5, lon / 1e5))

    return coordinates


def haversine_km(origin: LatLon, destination: LatLon) -> float:
    lat1, lon1 = origin
    lat2, lon2 = destination
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def closest_geometry_index(
    coordinates: list[LatLon],
    point: LatLon,
    *,
    min_index: int = 0,
) -> int:
    best_index = min_index
    best_distance = float("inf")
    for index in range(min_index, len(coordinates)):
        distance = haversine_km(point, coordinates[index])
        if distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index


def points_equal(left: LatLon, right: LatLon, *, tolerance: float = 1e-4) -> bool:
    return abs(left[0] - right[0]) <= tolerance and abs(left[1] - right[1]) <= tolerance


def combine_route_geometries(
    outbound: RouteGeometry,
    inbound: RouteGeometry,
) -> tuple[RouteGeometry, int]:
    """Concatenate outbound and inbound polylines; return combined geometry and turnaround index."""
    combined_coords = outbound.coordinates + inbound.coordinates[1:]
    turnaround_index = len(outbound.coordinates) - 1
    combined = RouteGeometry(
        distance_km=outbound.distance_km + inbound.distance_km,
        duration_hours=outbound.duration_hours + inbound.duration_hours,
        coordinates=combined_coords,
    )
    return combined, turnaround_index


class OSRMClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._cache: dict[tuple[LatLon, LatLon], RouteResult] = {}
        self._geometry_cache: dict[tuple[LatLon, LatLon], RouteGeometry] = {}

    def _coord_str(self, point: LatLon) -> str:
        lat, lon = point
        return f"{lon},{lat}"

    async def route(self, origin: LatLon, destination: LatLon) -> RouteResult:
        if points_equal(origin, destination):
            return RouteResult(distance_km=0.0, duration_hours=0.0)

        key = (origin, destination)
        if key in self._cache:
            return self._cache[key]

        coords = f"{self._coord_str(origin)};{self._coord_str(destination)}"
        url = f"{self._settings.osrm_base_url}/route/v1/driving/{coords}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"overview": "false", "steps": "false"})
            response.raise_for_status()
            data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError(f"OSRM could not find route between {origin} and {destination}")

        route = data["routes"][0]
        result = RouteResult(
            distance_km=route["distance"] / 1000.0,
            duration_hours=route["duration"] / 3600.0,
        )
        self._cache[key] = result
        return result

    async def route_geometry(self, origin: LatLon, destination: LatLon) -> RouteGeometry:
        key = (origin, destination)
        if key in self._geometry_cache:
            return self._geometry_cache[key]

        coords = f"{self._coord_str(origin)};{self._coord_str(destination)}"
        url = f"{self._settings.osrm_base_url}/route/v1/driving/{coords}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params={"overview": "full", "geometries": "polyline", "steps": "false"},
            )
            response.raise_for_status()
            data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError(f"OSRM could not find route between {origin} and {destination}")

        route = data["routes"][0]
        encoded = route.get("geometry")
        if not encoded:
            raise ValueError(f"OSRM returned no geometry between {origin} and {destination}")

        coordinates = decode_polyline(encoded)
        if len(coordinates) < 2:
            coordinates = [origin, destination]

        result = RouteGeometry(
            distance_km=route["distance"] / 1000.0,
            duration_hours=route["duration"] / 3600.0,
            coordinates=coordinates,
        )
        self._geometry_cache[key] = result
        summary = RouteResult(
            distance_km=result.distance_km,
            duration_hours=result.duration_hours,
        )
        self._cache[key] = summary
        return result

    async def distance_km(self, origin: LatLon, destination: LatLon) -> float:
        return (await self.route(origin, destination)).distance_km

    async def duration_hours(self, origin: LatLon, destination: LatLon) -> float:
        return (await self.route(origin, destination)).duration_hours

    async def _find_waypoint_on_geometry(
        self,
        geometry: RouteGeometry,
        start_index: int,
        dest_index: int,
        current_start: LatLon,
        target_hours: float,
    ) -> LatLon:
        if target_hours <= 0:
            return current_start

        destination = geometry.coordinates[dest_index]
        remaining_hours = await self.duration_hours(current_start, destination)
        if target_hours >= remaining_hours:
            return destination

        low = max(start_index + 1, 1)
        high = dest_index
        best = destination

        while low <= high:
            mid = (low + high) // 2
            point = geometry.coordinates[mid]
            hours = await self.duration_hours(current_start, point)
            if hours <= target_hours:
                best = point
                low = mid + 1
            else:
                high = mid - 1

        return best

    async def _split_geometry_into_legs(
        self,
        geometry: RouteGeometry,
        origin: LatLon,
        destination: LatLon,
        num_days: int,
        max_hours_per_day: float,
        *,
        driving_target_ratio: float = 0.95,
        turnaround_index: int | None = None,
    ) -> tuple[list[LegSegment], list[bool]]:
        if num_days <= 0:
            return [], []

        target_hours = max_hours_per_day * driving_target_ratio
        dest_index = len(geometry.coordinates) - 1
        legs: list[LegSegment] = []
        return_flags: list[bool] = []
        current_start = origin
        start_index = 0

        for day_index in range(num_days):
            remaining_days = num_days - day_index
            remaining_hours = await self.duration_hours(current_start, destination)

            if remaining_days == 1 or remaining_hours <= target_hours:
                end_point = destination
            else:
                per_day_target = remaining_hours / remaining_days
                end_point = await self._find_waypoint_on_geometry(
                    geometry,
                    start_index,
                    dest_index,
                    current_start,
                    min(target_hours, per_day_target),
                )

            route = await self.route(current_start, end_point)
            end_index = closest_geometry_index(
                geometry.coordinates,
                end_point,
                min_index=start_index,
            )
            is_return = (
                turnaround_index is not None
                and end_index > turnaround_index
                and not points_equal(end_point, destination)
            )
            legs.append(
                LegSegment(
                    start=current_start,
                    end=end_point,
                    duration_hours=route.duration_hours,
                    distance_km=route.distance_km,
                )
            )
            return_flags.append(is_return)
            current_start = end_point
            start_index = end_index

            if points_equal(end_point, destination):
                while len(legs) < num_days:
                    legs.append(
                        LegSegment(
                            start=destination,
                            end=destination,
                            duration_hours=0.0,
                            distance_km=0.0,
                        )
                    )
                    return_flags.append(
                        turnaround_index is not None
                        and len(return_flags) > 0
                        and return_flags[-1]
                    )
                break

        return legs[:num_days], return_flags[:num_days]

    async def split_route_into_legs(
        self,
        origin: LatLon,
        destination: LatLon,
        num_days: int,
        max_hours_per_day: float,
        *,
        driving_target_ratio: float = 0.95,
    ) -> tuple[list[LegSegment], RouteGeometry | None]:
        if num_days <= 0:
            return [], None

        geometry = await self.route_geometry(origin, destination)
        legs, _ = await self._split_geometry_into_legs(
            geometry,
            origin,
            destination,
            num_days,
            max_hours_per_day,
            driving_target_ratio=driving_target_ratio,
        )
        return legs, geometry

    async def split_round_trip_into_legs(
        self,
        origin: LatLon,
        destination: LatLon,
        num_days: int,
        max_hours_per_day: float,
        *,
        driving_target_ratio: float = 0.95,
    ) -> tuple[list[LegSegment], list[bool], RouteGeometry | None]:
        if num_days <= 0:
            return [], [], None

        outbound = await self.route_geometry(origin, destination)
        inbound = await self.route_geometry(destination, origin)
        combined, turnaround_index = combine_route_geometries(outbound, inbound)
        legs, return_flags = await self._split_geometry_into_legs(
            combined,
            origin,
            origin,
            num_days,
            max_hours_per_day,
            driving_target_ratio=driving_target_ratio,
            turnaround_index=turnaround_index,
        )
        return legs, return_flags, combined


_osrm_client: OSRMClient | None = None


def get_osrm_client() -> OSRMClient:
    global _osrm_client
    if _osrm_client is None:
        _osrm_client = OSRMClient()
    return _osrm_client
