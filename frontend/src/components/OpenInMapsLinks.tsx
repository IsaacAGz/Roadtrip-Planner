import type { DayPlan, RoadtripPlan } from "../api/client";
import { buildDayMapsUrls } from "../lib/mapsLinks";

interface OpenInMapsLinksProps {
  plan: RoadtripPlan;
  day: DayPlan;
}

export function OpenInMapsLinks({ plan, day }: OpenInMapsLinksProps) {
  const { google, apple, truncatedWaypoints } = buildDayMapsUrls(plan, day);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <a
        href={google}
        target="_blank"
        rel="noopener noreferrer"
        className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
      >
        Google Maps
      </a>
      <a
        href={apple}
        target="_blank"
        rel="noopener noreferrer"
        className="rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
      >
        Apple Maps
      </a>
      {truncatedWaypoints && (
        <span className="text-xs text-slate-500">First 9 stops only</span>
      )}
    </div>
  );
}
