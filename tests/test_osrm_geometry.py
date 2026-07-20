import pytest

from app.services.osrm import (
    LegSegment,
    RouteGeometry,
    RouteResult,
    closest_geometry_index,
    decode_polyline,
    haversine_km,
    points_equal,
)


def test_decode_polyline_round_trip_known_point():
    # Encoded point near (38.5, -120.2)
    encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    coordinates = decode_polyline(encoded)

    assert len(coordinates) >= 2
    first_lat, first_lon = coordinates[0]
    assert abs(first_lat - 38.5) < 0.1
    assert abs(first_lon - (-120.2)) < 0.1


def test_haversine_km_is_nonzero_for_separated_points():
    distance = haversine_km((0.0, 0.0), (1.0, 1.0))
    assert distance > 100.0


def test_closest_geometry_index_prefers_later_points():
    coordinates = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)]
    index = closest_geometry_index(coordinates, (2.1, 0.0), min_index=1)
    assert index == 2


def test_points_equal_within_tolerance():
    assert points_equal((1.0, 2.0), (1.00001, 2.00001))


class GeometryTrackingOSRM:
    def __init__(self) -> None:
        self.geometry = RouteGeometry(
            distance_km=300.0,
            duration_hours=12.0,
            coordinates=[
                (0.0, 0.0),
                (0.0, 1.0),
                (0.0, 2.0),
                (0.0, 3.0),
                (0.0, 4.0),
            ],
        )
        self.duration_map = {
            ((0.0, 0.0), (0.0, 4.0)): 12.0,
            ((0.0, 0.0), (0.0, 1.0)): 3.0,
            ((0.0, 1.0), (0.0, 2.0)): 3.0,
            ((0.0, 2.0), (0.0, 3.0)): 3.0,
            ((0.0, 3.0), (0.0, 4.0)): 3.0,
            ((0.0, 1.0), (0.0, 4.0)): 9.0,
            ((0.0, 2.0), (0.0, 4.0)): 6.0,
            ((0.0, 3.0), (0.0, 4.0)): 3.0,
        }
        self.distance_map = {key: hours * 25.0 for key, hours in self.duration_map.items()}

    async def route_geometry(self, origin, destination):
        return self.geometry

    async def route(self, origin, destination):
        hours = self.duration_map.get((origin, destination), 1.0)
        return RouteResult(distance_km=hours * 25.0, duration_hours=hours)

    async def duration_hours(self, origin, destination):
        return (await self.route(origin, destination)).duration_hours

    async def split_route_into_legs(self, origin, destination, num_days, max_hours_per_day, **kwargs):
        target_hours = max_hours_per_day * kwargs.get("driving_target_ratio", 0.95)
        legs: list[LegSegment] = []
        current_start = origin
        start_index = 0
        dest_index = len(self.geometry.coordinates) - 1

        for day_index in range(num_days):
            remaining_days = num_days - day_index
            remaining_hours = await self.duration_hours(current_start, destination)

            if remaining_days == 1 or remaining_hours <= target_hours:
                end_point = destination
            else:
                per_day_target = remaining_hours / remaining_days
                end_point = await self._find_waypoint_on_geometry(
                    self.geometry,
                    start_index,
                    dest_index,
                    current_start,
                    min(target_hours, per_day_target),
                )

            route = await self.route(current_start, end_point)
            legs.append(
                LegSegment(
                    start=current_start,
                    end=end_point,
                    duration_hours=route.duration_hours,
                    distance_km=route.distance_km,
                )
            )
            current_start = end_point
            start_index = closest_geometry_index(
                self.geometry.coordinates,
                end_point,
                min_index=start_index,
            )
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
                break

        return legs[:num_days], self.geometry

    async def _find_waypoint_on_geometry(
        self,
        geometry,
        start_index,
        dest_index,
        current_start,
        target_hours,
    ):
        from app.services.osrm import OSRMClient

        return await OSRMClient._find_waypoint_on_geometry(
            self,
            geometry,
            start_index,
            dest_index,
            current_start,
            target_hours,
        )


@pytest.mark.asyncio
async def test_split_route_into_legs_uses_geometry_waypoints():
    client = GeometryTrackingOSRM()
    origin = (0.0, 0.0)
    destination = (0.0, 4.0)

    legs, geometry = await client.split_route_into_legs(
        origin,
        destination,
        num_days=4,
        max_hours_per_day=6.0,
        driving_target_ratio=0.95,
    )

    assert geometry is not None
    assert len(legs) == 4
    assert all(leg.duration_hours <= 6.0 + 0.01 for leg in legs if leg.duration_hours > 0)
    assert legs[-1].end == destination
    assert legs[0].end in geometry.coordinates
    assert legs[0].end != destination
