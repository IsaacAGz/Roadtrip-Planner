import { useState } from "react";
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

function statusClassName(status: JobHistoryEntry["status"]): string {
  if (status === "completed") {
    return "bg-pale-green text-pale-green-ink";
  }
  if (status === "failed") {
    return "bg-pale-red text-pale-red-ink";
  }
  if (status === "running") {
    return "bg-pale-blue text-pale-blue-ink";
  }
  return "bg-pale-yellow text-pale-yellow-ink";
}

function DisclosureMark({ open }: { open: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="shrink-0">
      <path d="M3 8h10" stroke="currentColor" strokeWidth="1.5" />
      {open ? null : <path d="M8 3v10" stroke="currentColor" strokeWidth="1.5" />}
    </svg>
  );
}

export function JobHistoryPanel({
  entries,
  activeJobId,
  onSelect,
  onClear,
  onRemove,
}: JobHistoryPanelProps) {
  const [open, setOpen] = useState(false);

  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted">
        Recent trips appear here after a planning job finishes.
      </p>
    );
  }

  return (
    <section className="border-b border-line">
      <h2>
        <button
          type="button"
          aria-expanded={open}
          aria-controls="recent-trips-panel"
          onClick={() => setOpen((current) => !current)}
          className="flex w-full items-center justify-between gap-4 py-3 text-left font-sans text-sm font-medium text-ink"
        >
          <span>
            Recent trips
            <span className="ml-2 font-mono text-xs font-normal text-muted">{entries.length}</span>
          </span>
          <DisclosureMark open={open} />
        </button>
      </h2>

      {open && (
        <div id="recent-trips-panel" className="pb-4">
          <div className="mb-3 flex justify-end">
            <button
              type="button"
              onClick={onClear}
              className="rounded-md border border-line bg-surface px-3 py-1.5 font-sans text-xs font-medium text-ink transition-transform duration-200 hover:bg-canvas active:scale-[0.98]"
            >
              Clear history
            </button>
          </div>
          <ul className="space-y-2">
            {entries.map((entry) => {
              const isActive = entry.job_id === activeJobId;
              return (
                <li
                  key={entry.job_id}
                  className={`rounded-lg border bg-surface p-4 transition-shadow duration-200 hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)] ${
                    isActive ? "border-ink" : "border-line"
                  }`}
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <button
                      type="button"
                      onClick={() => onSelect(entry.job_id)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <div className="truncate text-sm font-medium text-ink">
                        {entry.plan_title ?? formatRoute(entry)}
                      </div>
                      <div className="mt-1 text-xs text-muted">{formatRoute(entry)}</div>
                      <div className="mt-1 font-mono text-xs text-muted">{formatDates(entry)}</div>
                    </button>
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium uppercase tracking-wide ${statusClassName(entry.status)}`}
                      >
                        {entry.status}
                      </span>
                      <button
                        type="button"
                        onClick={() => onRemove(entry.job_id)}
                        className="rounded-md px-2 py-1 text-xs text-muted hover:bg-canvas hover:text-ink"
                        aria-label={`Remove ${formatRoute(entry)} from history`}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}
