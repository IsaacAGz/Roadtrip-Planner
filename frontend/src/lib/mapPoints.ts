import type { RoadtripPlan } from "../api/client";

export type MapPointKind = "origin" | "destination" | "overnight";

export interface MapPoint {
  lat: number;
  lon: number;
  label: string;
  kind: MapPointKind;
  day?: number;
}

const kindStyles: Record<
  MapPointKind,
  { color: string; fillColor: string; radius: number }
> = {
  origin: { color: "#1c3a2e", fillColor: "#3f6b56", radius: 9 },
  destination: { color: "#8a4e10", fillColor: "#e08a2a", radius: 9 },
  overnight: { color: "#245654", fillColor: "#3d7a78", radius: 7 },
};

export const routeLineColor = "#1c3a2e";
export const plannedLineColor = "#5c6b62";

export function getMapPointStyle(kind: MapPointKind) {
  return kindStyles[kind];
}

export function buildMapPoints(plan: RoadtripPlan): MapPoint[] {
  const points: MapPoint[] = [
    {
      lat: plan.origin_lat,
      lon: plan.origin_lon,
      label: "Trip origin",
      kind: "origin",
    },
  ];

  for (const day of plan.days) {
    points.push({
      lat: day.overnight.lat,
      lon: day.overnight.lon,
      label: `Day ${day.day}: ${day.overnight.city}`,
      kind: "overnight",
      day: day.day,
    });
  }

  points.push({
    lat: plan.destination_lat,
    lon: plan.destination_lon,
    label: "Trip destination",
    kind: "destination",
  });

  return points;
}

export function buildRoutePolyline(points: MapPoint[]): [number, number][] {
  return points.map((point) => [point.lat, point.lon]);
}

export function dedupeOvernightMarkers(points: MapPoint[]): MapPoint[] {
  const result: MapPoint[] = [];
  let previousKey: string | null = null;

  for (const point of points) {
    if (point.kind !== "overnight") {
      result.push(point);
      continue;
    }

    const key = `${point.lat.toFixed(4)},${point.lon.toFixed(4)}`;
    if (key === previousKey) {
      const existing = result.at(-1);
      if (existing && existing.kind === "overnight") {
        existing.label = `${existing.label} · ${point.label}`;
      }
      continue;
    }

    previousKey = key;
    result.push(point);
  }

  return result;
}
