import type { RoadtripPlan } from "../api/client";

interface ItineraryViewProps {
  plan: RoadtripPlan;
}

export function ItineraryView({ plan }: ItineraryViewProps) {
  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-semibold text-slate-900">{plan.title}</h2>
        <p className="mt-1 text-sm text-slate-600">{plan.total_days} days</p>
        {plan.tips.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-semibold text-slate-800">Tips</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {plan.tips.map((tip, index) => (
                <li key={index}>{tip}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="grid gap-4">
        {plan.days.map((day) => (
          <article key={day.day} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-lg font-semibold text-slate-900">
                Day {day.day} · {day.date}
              </h3>
              <span className="text-sm text-slate-600">{day.driving_hours.toFixed(1)} h driving</span>
            </div>
            <p className="mt-2 text-sm text-slate-700">{day.route_summary}</p>

            {day.stops.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-semibold text-slate-800">Stops</h4>
                <ul className="mt-2 space-y-2">
                  {day.stops.map((stop, index) => (
                    <li key={`${stop.name}-${index}`} className="rounded-lg bg-slate-50 p-3 text-sm">
                      <div className="font-medium text-slate-900">{stop.name}</div>
                      {stop.description && <p className="mt-1 text-slate-600">{stop.description}</p>}
                      <p className="mt-1 text-xs text-slate-500">
                        {stop.category} · {stop.duration_hours} h
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm">
              <span className="font-medium text-slate-800">Overnight:</span> {day.overnight.city} (
              {day.overnight.stay_type}, {day.overnight.nights} night
              {day.overnight.nights === 1 ? "" : "s"})
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
