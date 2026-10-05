import type { RoadtripPlan } from "../api/client";

interface ItineraryViewProps {
  plan: RoadtripPlan;
}

export function ItineraryView({ plan }: ItineraryViewProps) {
  return (
    <section className="space-y-4">
      <div className="rounded-2xl bg-paper p-6 text-pine shadow-[0_16px_40px_rgb(28_58_46_/_0.06)] ring-1 ring-pine/10">
        <h2 className="max-w-3xl font-display text-3xl leading-none tracking-[-0.03em] text-balance">
          {plan.title}
        </h2>
        <p className="mt-3 text-sm tabular-nums text-pine-muted">{plan.total_days} days</p>
        {plan.tips.length > 0 && (
          <div className="mt-5">
            <h3 className="font-display text-xl tracking-[-0.02em]">Tips</h3>
            <ul className="mt-2 max-w-prose list-disc space-y-1 pl-5 text-sm leading-relaxed text-pine">
              {plan.tips.map((tip, index) => (
                <li key={index}>{tip}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="grid gap-4">
        {plan.days.map((day) => (
          <article
            key={day.day}
            className="rounded-2xl bg-paper p-5 text-pine shadow-[0_16px_40px_rgb(28_58_46_/_0.06)] ring-1 ring-pine/10"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-display text-2xl tracking-[-0.02em]">
                Day {day.day}, {day.date}
              </h3>
              <span className="text-sm tabular-nums text-pine-muted">{day.driving_hours.toFixed(1)} h driving</span>
            </div>
            <p className="mt-3 max-w-prose text-sm leading-relaxed text-pine">{day.route_summary}</p>

            {day.stops.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-pine">Stops</h4>
                <ul className="mt-2 space-y-2">
                  {day.stops.map((stop, index) => (
                    <li key={`${stop.name}-${index}`} className="rounded-xl bg-sand p-3 text-sm">
                      <div className="font-medium text-pine">{stop.name}</div>
                      {stop.description && (
                        <p className="mt-1 max-w-prose leading-relaxed text-pine-muted">{stop.description}</p>
                      )}
                      <p className="mt-1 text-xs text-pine-muted">
                        {stop.category}, {stop.duration_hours} h
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-4 rounded-xl bg-sand p-3 text-sm">
              <span className="font-medium text-pine">Overnight:</span> {day.overnight.city} (
              {day.overnight.stay_type}, {day.overnight.nights} night
              {day.overnight.nights === 1 ? "" : "s"})
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
