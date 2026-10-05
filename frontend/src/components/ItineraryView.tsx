import type { RoadtripPlan } from "../api/client";

interface ItineraryViewProps {
  plan: RoadtripPlan;
}

export function ItineraryView({ plan }: ItineraryViewProps) {
  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-line bg-surface p-6">
        <h2 className="font-serif text-3xl leading-none tracking-[-0.03em] text-ink">{plan.title}</h2>
        <p className="mt-2 font-mono text-sm text-muted">{plan.total_days} days</p>
        {plan.tips.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-ink">Tips</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
              {plan.tips.map((tip, index) => (
                <li key={index}>{tip}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="grid gap-4">
        {plan.days.map((day) => (
          <article key={day.day} className="rounded-xl border border-line bg-surface p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-serif text-2xl leading-none tracking-[-0.03em] text-ink">
                Day {day.day} · {day.date}
              </h3>
              <span className="font-mono text-sm text-muted">{day.driving_hours.toFixed(1)} h driving</span>
            </div>
            <p className="mt-3 text-sm text-ink">{day.route_summary}</p>

            {day.stops.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-ink">Stops</h4>
                <ul className="mt-2 space-y-2">
                  {day.stops.map((stop, index) => (
                    <li key={`${stop.name}-${index}`} className="rounded-lg border border-line p-3 text-sm">
                      <div className="font-medium text-ink">{stop.name}</div>
                      {stop.description && <p className="mt-1 text-muted">{stop.description}</p>}
                      <p className="mt-1 font-mono text-xs text-muted">
                        {stop.category} · {stop.duration_hours} h
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-4 rounded-lg border border-line p-3 text-sm text-ink">
              <span className="font-medium">Overnight:</span> {day.overnight.city} (
              {day.overnight.stay_type}, {day.overnight.nights} night
              {day.overnight.nights === 1 ? "" : "s"})
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
