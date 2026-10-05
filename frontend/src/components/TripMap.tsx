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
import {
  buildMapPoints,
  buildRoutePolyline,
  dedupeOvernightMarkers,
  getMapPointStyle,
} from "../lib/mapPoints";

interface TripMapProps {
  plan: RoadtripPlan;
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
    <section className="overflow-hidden rounded-xl border border-line bg-surface">
      <div className="border-b border-line px-6 py-5">
        <h2 className="font-serif text-2xl leading-none tracking-[-0.03em] text-ink">Route map</h2>
        <p className="mt-2 text-sm text-muted">
          OpenStreetMap view of origin, overnight stops, and destination.
          {roadGeometry.length > 0
            ? " Solid line shows the OSRM driving route; markers show planned stops."
            : " Dashed line shows planned stop order, not OSRM road geometry."}
        </p>
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted">
          <span className="inline-flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-pale-green-ink" />
            Origin
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-pale-blue-ink" />
            Overnight
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-pale-red-ink" />
            Destination
          </span>
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
              pathOptions={{ color: "#2f3437", weight: 4 }}
            />
          )}
          <Polyline
            positions={route}
            pathOptions={{
              color: "#787774",
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
                  <div className="font-sans text-sm text-ink">
                    <div className="font-medium">{point.label}</div>
                    <div className="mt-1 font-mono text-xs text-muted">
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
