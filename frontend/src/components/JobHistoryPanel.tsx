import type { JobHistoryEntry } from "../lib/jobHistory";
import { focusRing, quietButtonClass } from "../lib/ui";

interface JobHistoryPanelProps {
  entries: JobHistoryEntry[];
  activeJobId: string | null;
  onSelect: (jobId: string) => void;
  onClear: () => void;
  onRemove: (jobId: string) => void;
}

function formatRoute(entry: JobHistoryEntry): string {
  return `${entry.origin} → ${entry.destination}`;
}

function formatDates(entry: JobHistoryEntry): string {
  if (!entry.start_date || !entry.end_date) {
    return "Dates unavailable";
  }
  if (entry.start_date === entry.end_date) {
    return entry.start_date;
  }
  return `${entry.start_date} – ${entry.end_date}`;
}

export function JobHistoryPanel({
  entries,
  activeJobId,
  onSelect,
  onClear,
  onRemove,
}: JobHistoryPanelProps) {
  if (entries.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-pine/25 bg-paper p-4 text-sm leading-relaxed text-pine-muted">
        Recent trips will appear here after you complete or fail a planning job.
      </section>
    );
  }

  return (
    <section className="rounded-2xl bg-paper p-4 text-pine shadow-[0_16px_40px_rgb(28_58_46_/_0.06)] ring-1 ring-pine/10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-xl tracking-[-0.02em]">Recent trips</h2>
          <p className="text-xs text-pine-muted">Stored locally in this browser</p>
        </div>
        <button type="button" onClick={onClear} className={quietButtonClass}>
          Clear history
        </button>
      </div>

      <ul className="mt-4 space-y-2">
        {entries.map((entry) => {
          const isActive = entry.job_id === activeJobId;
          return (
            <li
              key={entry.job_id}
              className={`rounded-xl p-3 ring-1 ${
                isActive ? "bg-sand ring-amber" : "ring-pine/10"
              }`}
            >
              <div className="flex flex-col gap-3">
                <button
                  type="button"
                  onClick={() => onSelect(entry.job_id)}
                  className={`min-w-0 text-left ${focusRing}`}
                >
                  <div className="truncate text-sm font-medium text-pine">
                    {entry.plan_title ?? formatRoute(entry)}
                  </div>
                  <div className="mt-1 text-xs text-pine-muted">{formatRoute(entry)}</div>
                  <div className="mt-1 text-xs tabular-nums text-pine-muted">{formatDates(entry)}</div>
                </button>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs capitalize ${
                      entry.status === "completed"
                        ? "bg-moss-wash text-pine"
                        : "bg-clay-wash text-clay"
                    }`}
                  >
                    {entry.status}
                  </span>
                  <button
                    type="button"
                    onClick={() => onRemove(entry.job_id)}
                    className={`rounded-full px-2 py-1 text-xs text-pine-muted transition duration-200 hover:bg-sand-deep hover:text-pine ${focusRing}`}
                    aria-label="Remove from history"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
