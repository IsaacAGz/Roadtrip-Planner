import type { JobHistoryEntry } from "../lib/jobHistory";

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
      <section className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-600">
        Recent trips will appear here after you complete or fail a planning job.
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Recent trips</h2>
          <p className="text-xs text-slate-500">Stored locally in this browser</p>
        </div>
        <button
          type="button"
          onClick={onClear}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          Clear history
        </button>
      </div>

      <ul className="mt-4 space-y-2">
        {entries.map((entry) => {
          const isActive = entry.job_id === activeJobId;
          return (
            <li
              key={entry.job_id}
              className={`rounded-lg border p-3 ${
                isActive ? "border-slate-900 bg-slate-50" : "border-slate-200"
              }`}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <button
                  type="button"
                  onClick={() => onSelect(entry.job_id)}
                  className="min-w-0 flex-1 text-left"
                >
                  <div className="truncate text-sm font-medium text-slate-900">
                    {entry.plan_title ?? formatRoute(entry)}
                  </div>
                  <div className="mt-1 text-xs text-slate-600">{formatRoute(entry)}</div>
                  <div className="mt-1 text-xs text-slate-500">{formatDates(entry)}</div>
                </button>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                      entry.status === "completed"
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {entry.status}
                  </span>
                  <button
                    type="button"
                    onClick={() => onRemove(entry.job_id)}
                    className="rounded-md px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-700"
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
