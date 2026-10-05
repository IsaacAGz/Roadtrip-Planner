import type { ProgressEvent, ProgressStage } from "../api/client";
import { CopyJsonButton } from "./CopyJsonButton";

interface ProgressPanelProps {
  jobId: string;
  status: string;
  progress: ProgressEvent[];
  transport?: "sse" | "polling";
}

const stageOrder: ProgressStage[] = [
  "queued",
  "planning",
  "hard_validation",
  "soft_validation",
  "completed",
];

const stageLabels: Record<ProgressStage, string> = {
  queued: "Queued",
  planning: "Planning",
  hard_validation: "Hard validation",
  soft_validation: "Soft validation",
  completed: "Completed",
  failed: "Failed",
};

function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function latestStageIndex(progress: ProgressEvent[]): number {
  let maxIndex = 0;
  for (const event of progress) {
    const index = stageOrder.indexOf(event.stage);
    if (index > maxIndex) {
      maxIndex = index;
    }
  }
  return maxIndex;
}

function statusClassName(status: string): string {
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

function StageMark({ complete, active, index }: { complete: boolean; active: boolean; index: number }) {
  const tone = complete
    ? "bg-pale-green text-pale-green-ink"
    : active
      ? "bg-pale-yellow text-pale-yellow-ink"
      : "bg-canvas text-muted";

  return (
    <span
      className={`relative z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full font-mono text-xs ${tone}`}
      aria-hidden="true"
    >
      {complete ? (
        <svg width="12" height="12" viewBox="0 0 12 12">
          <path d="M2 6.2 4.6 9 10 3" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      ) : (
        index + 1
      )}
    </span>
  );
}

export function ProgressPanel({ jobId, status, progress, transport = "sse" }: ProgressPanelProps) {
  const latest = progress.at(-1);
  const activeIndex = latestStageIndex(progress);
  const jobSnapshot = { job_id: jobId, status, progress };

  return (
    <section className="rounded-xl border border-line bg-surface p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl leading-none tracking-[-0.03em] text-ink">Planning in progress</h2>
          <p className="mt-2 font-mono text-xs text-muted">Job {jobId}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <CopyJsonButton label="Copy job JSON" value={jobSnapshot} />
          <span className="rounded-full bg-pale-blue px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-pale-blue-ink">
            {transport === "sse" ? "live updates" : "polling fallback"}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium uppercase tracking-wide ${statusClassName(status)}`}
          >
            {status}
          </span>
        </div>
      </div>

      {latest && (
        <p className="mt-4 text-sm text-ink">
          <span className="font-medium">Current step:</span> {latest.message}
          {latest.attempt !== null && latest.attempt > 0 ? ` (replan ${latest.attempt + 1})` : ""}
        </p>
      )}

      <div className="mt-6">
        <h3 className="text-sm font-medium text-ink">Timeline</h3>
        <ol className="mt-4">
          {stageOrder.map((stage, index) => {
            const events = progress.filter((event) => event.stage === stage);
            if (events.length === 0 && index > activeIndex) {
              return null;
            }

            const isActive = index === activeIndex && status !== "completed";
            const isComplete = index < activeIndex || status === "completed";

            return (
              <li key={stage} className="relative flex gap-4 pb-6 last:pb-0">
                {index < stageOrder.length - 1 && (
                  <span className="absolute top-6 left-[11px] h-full w-px bg-line" />
                )}
                <StageMark complete={isComplete} active={isActive} index={index} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-ink">{stageLabels[stage]}</span>
                    {isComplete && (
                      <span className="text-xs uppercase tracking-wide text-pale-green-ink">Done</span>
                    )}
                    {isActive && (
                      <span className="rounded-full bg-pale-yellow px-2 py-0.5 text-xs uppercase tracking-wide text-pale-yellow-ink">
                        In progress
                      </span>
                    )}
                  </div>
                  {events.length > 0 ? (
                    <ul className="mt-2 space-y-1">
                      {events.map((event, eventIndex) => (
                        <li key={`${event.timestamp}-${eventIndex}`} className="text-sm text-muted">
                          <span className="font-mono text-xs">{formatTimestamp(event.timestamp)}</span>
                          {" · "}
                          {event.message}
                          {event.attempt !== null && event.attempt > 0
                            ? ` (attempt ${event.attempt + 1})`
                            : ""}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-muted">Waiting</p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
