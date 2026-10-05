import { useEffect, useMemo } from "react";
import {
  CircleMarker,
  MapContainer,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import type { LatLngBoundsExpression, LatLngExpression } from "leaflet";
import L from "leaflet";
import type { RoadtripPlan } from "../api/client";
import type { MapPointKind } from "../lib/mapPoints";
import {
  buildMapPoints,
  buildRoutePolyline,
  dedupeOvernightMarkers,
  getMapPointStyle,
  plannedLineColor,
  routeLineColor,
} from "../lib/mapPoints";

interface TripMapProps {
  plan: RoadtripPlan;
}

function LegendDot({ kind, label }: { kind: MapPointKind; label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="size-3 rounded-full"
        style={{ backgroundColor: getMapPointStyle(kind).fillColor }}
      />
      {label}
    </span>
  );
}

function FitBounds({ bounds }: { bounds: LatLngBoundsExpression | null }) {
  const map = useMap();

  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [32, 32] });
    }
  }, [bounds, map]);

  return null;
}

export function TripMap({ plan }: TripMapProps) {
  const points = useMemo(
    () => dedupeOvernightMarkers(buildMapPoints(plan)),
    [plan],
  );
  const route = useMemo(() => buildRoutePolyline(points), [points]);
  const roadGeometry = useMemo(
    () =>
      (plan.route_geometry ?? []).map(
        (coordinate) => [coordinate[0], coordinate[1]] as [number, number],
      ),
    [plan.route_geometry],
  );
  const bounds = useMemo(() => {
    if (points.length === 0) {
      return null;
    }
    return L.latLngBounds(points.map((point) => [point.lat, point.lon]));
  }, [points]);

  const center: LatLngExpression =
    points.length > 0 ? [points[0].lat, points[0].lon] : [39.8, -98.6];

  return (
    <section className="overflow-hidden rounded-2xl bg-paper text-pine shadow-[0_16px_40px_rgb(28_58_46_/_0.06)] ring-1 ring-pine/10">
      <div className="border-b border-pine/10 px-6 py-5">
        <h2 className="font-display text-3xl leading-none tracking-[-0.03em]">Route map</h2>
        <p className="mt-3 max-w-prose text-sm leading-relaxed text-pine-muted">
          OpenStreetMap view of origin, overnight stops, and destination.
          {roadGeometry.length > 0
            ? " Solid line shows the OSRM driving route; markers show planned stops."
            : " Dashed line shows planned stop order, not OSRM road geometry."}
        </p>
        <div className="mt-4 flex flex-wrap gap-4 text-xs text-pine-muted">
          <LegendDot kind="origin" label="Origin" />
          <LegendDot kind="overnight" label="Overnight" />
          <LegendDot kind="destination" label="Destination" />
        </div>
      </div>

      <div className="h-[280px] w-full sm:h-[420px]">
        <MapContainer center={center} zoom={6} scrollWheelZoom className="h-full w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {bounds && <FitBounds bounds={bounds} />}
          {roadGeometry.length > 0 && (
            <Polyline
              positions={roadGeometry}
              pathOptions={{ color: routeLineColor, weight: 4 }}
            />
          )}
          <Polyline
            positions={route}
            pathOptions={{
              color: plannedLineColor,
              weight: roadGeometry.length > 0 ? 2 : 3,
              dashArray: roadGeometry.length > 0 ? "4 6" : "8 8",
              opacity: roadGeometry.length > 0 ? 0.7 : 1,
            }}
          />
          {points.map((point, index) => {
            const style = getMapPointStyle(point.kind);
            return (
              <CircleMarker
                key={`${point.kind}-${point.day ?? index}-${point.lat}-${point.lon}`}
                center={[point.lat, point.lon]}
                radius={style.radius}
                pathOptions={{
                  color: style.color,
                  fillColor: style.fillColor,
                  fillOpacity: 0.95,
                  weight: 2,
                }}
              >
                <Popup>
                  <div className="text-sm">
                    <div className="font-semibold">{point.label}</div>
                    <div className="mt-1 text-pine-muted">
                      {point.lat.toFixed(4)}, {point.lon.toFixed(4)}
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </section>
  );
}
