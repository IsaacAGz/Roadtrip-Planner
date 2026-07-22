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

export function ProgressPanel({ jobId, status, progress, transport = "sse" }: ProgressPanelProps) {
  const latest = progress.at(-1);
  const activeIndex = latestStageIndex(progress);
  const jobSnapshot = { job_id: jobId, status, progress };

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Planning in progress</h2>
          <p className="mt-1 text-sm text-slate-600">Job {jobId}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <CopyJsonButton label="Copy job JSON" value={jobSnapshot} />
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium uppercase tracking-wide text-slate-700">
            {transport === "sse" ? "live updates" : "polling fallback"}
          </span>
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium uppercase tracking-wide text-amber-800">
            {status}
          </span>
        </div>
      </div>

      {status === "queued" && progress.length <= 1 && (
        <div className="mt-4 animate-pulse space-y-3 rounded-lg bg-slate-50 px-4 py-3">
          <div className="h-3 w-1/3 rounded bg-slate-200" />
          <div className="h-3 w-2/3 rounded bg-slate-200" />
          <div className="h-3 w-1/2 rounded bg-slate-200" />
        </div>
      )}

      {latest && (
        <p className="mt-4 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-700">
          <span className="font-medium text-slate-900">Current step:</span> {latest.message}
          {latest.attempt !== null && latest.attempt > 0 ? ` (replan ${latest.attempt + 1})` : ""}
        </p>
      )}

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-slate-900">Timeline</h3>
        <ol className="mt-4 space-y-0">
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
                  <span
                    className={`absolute left-[11px] top-6 h-full w-0.5 ${
                      isComplete ? "bg-emerald-300" : "bg-slate-200"
                    }`}
                  />
                )}
                <span
                  className={`relative z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                    isComplete
                      ? "bg-emerald-500 text-white"
                      : isActive
                        ? "bg-amber-500 text-white"
                        : "bg-slate-200 text-slate-600"
                  }`}
                >
                  {isComplete ? "✓" : index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-slate-900">{stageLabels[stage]}</span>
                    {isActive && (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
                        in progress
                      </span>
                    )}
                  </div>
                  {events.length > 0 ? (
                    <ul className="mt-2 space-y-1">
                      {events.map((event, eventIndex) => (
                        <li key={`${event.timestamp}-${eventIndex}`} className="text-sm text-slate-600">
                          <span className="text-xs text-slate-400">{formatTimestamp(event.timestamp)}</span>
                          {" · "}
                          {event.message}
                          {event.attempt !== null && event.attempt > 0
                            ? ` (attempt ${event.attempt + 1})`
                            : ""}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-slate-400">Waiting</p>
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
