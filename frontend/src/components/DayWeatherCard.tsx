import type { DayWeather } from "../api/client";

interface DayWeatherCardProps {
  weather?: DayWeather | null;
}

export function DayWeatherCard({ weather }: DayWeatherCardProps) {
  if (!weather) {
    return (
      <p className="mt-3 text-xs text-slate-500 italic">Weather forecast unavailable</p>
    );
  }

  const precipPercent = Math.round(weather.max_precip_chance * 100);

  return (
    <div className="mt-3 rounded-lg border border-sky-100 bg-sky-50 p-3 text-sm text-sky-950">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium capitalize">{weather.summary}</span>
        <span className="text-xs text-sky-800">
          {weather.min_temp_c.toFixed(0)}–{weather.max_temp_c.toFixed(0)}°C
        </span>
      </div>
      <p className="mt-1 text-xs text-sky-800">Max precip chance: {precipPercent}%</p>
    </div>
  );
}
