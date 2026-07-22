import type { DayPlan, RoadtripPlan } from "../api/client";

export interface LatLon {
  lat: number;
  lon: number;
}

export interface DayRoute {
  origin: LatLon;
  waypoints: LatLon[];
  destination: LatLon;
}

const GOOGLE_MAX_WAYPOINTS = 9;

function formatCoord({ lat, lon }: LatLon): string {
  return `${lat},${lon}`;
}

export function getDayRoute(plan: RoadtripPlan, dayIndex: number): DayRoute {
  const day = plan.days[dayIndex];
  const previousDay = dayIndex > 0 ? plan.days[dayIndex - 1] : null;

  let origin: LatLon;
  if (day.leg_start_lat != null && day.leg_start_lon != null) {
    origin = { lat: day.leg_start_lat, lon: day.leg_start_lon };
  } else if (previousDay) {
    origin = { lat: previousDay.overnight.lat, lon: previousDay.overnight.lon };
  } else {
    origin = { lat: plan.origin_lat, lon: plan.origin_lon };
  }

  const waypoints = day.stops.map((stop) => ({ lat: stop.lat, lon: stop.lon }));

  let destination: LatLon;
  if (day.leg_end_lat != null && day.leg_end_lon != null) {
    destination = { lat: day.leg_end_lat, lon: day.leg_end_lon };
  } else {
    destination = { lat: day.overnight.lat, lon: day.overnight.lon };
  }

  return { origin, waypoints, destination };
}

export function buildGoogleMapsUrl(route: DayRoute): string {
  const params = new URLSearchParams({
    api: "1",
    origin: formatCoord(route.origin),
    destination: formatCoord(route.destination),
    travelmode: "driving",
  });

  if (route.waypoints.length > 0) {
    const waypoints = route.waypoints.slice(0, GOOGLE_MAX_WAYPOINTS);
    params.set("waypoints", waypoints.map(formatCoord).join("|"));
  }

  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

export function buildAppleMapsUrl(route: DayRoute): string {
  const viaPoints = route.waypoints.slice(0, GOOGLE_MAX_WAYPOINTS);
  const daddr = [...viaPoints, route.destination].map(formatCoord).join("+to:");

  const params = new URLSearchParams({
    saddr: formatCoord(route.origin),
    daddr,
    dirflg: "d",
  });

  return `https://maps.apple.com/?${params.toString()}`;
}

export function buildDayMapsUrls(plan: RoadtripPlan, day: DayPlan): {
  google: string;
  apple: string;
  truncatedWaypoints: boolean;
} {
  const dayIndex = plan.days.findIndex((item) => item.day === day.day);
  const route = getDayRoute(plan, dayIndex >= 0 ? dayIndex : 0);

  return {
    google: buildGoogleMapsUrl(route),
    apple: buildAppleMapsUrl(route),
    truncatedWaypoints: route.waypoints.length > GOOGLE_MAX_WAYPOINTS,
  };
}
