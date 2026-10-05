import { useEffect, useState } from "react";
import {
  ApiError,
  isTerminalJobStatus,
  startPlanningJob,
  type TripRequestPayload,
} from "./api/client";
import { CopyJsonButton } from "./components/CopyJsonButton";
import { ErrorAlert } from "./components/ErrorAlert";
import { ItineraryView } from "./components/ItineraryView";
import { JobHistoryPanel } from "./components/JobHistoryPanel";
import { ProgressPanel } from "./components/ProgressPanel";
import { TripForm } from "./components/TripForm";
import { TripMap } from "./components/TripMap";
import { ValidationSummary } from "./components/ValidationSummary";
import { usePlanningJob } from "./hooks/usePlanningJob";
import mountainRoad from "./assets/photos/mountain-road.jpg";
import { quietButtonClass } from "./lib/ui";
import {
  clearJobHistory,
  loadJobHistory,
  removeJobHistoryEntry,
  upsertJobHistory,
  type JobHistoryEntry,
} from "./lib/jobHistory";

export function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastRequest, setLastRequest] = useState<TripRequestPayload | null>(null);
  const [history, setHistory] = useState<JobHistoryEntry[]>(() => loadJobHistory());

  const jobQuery = usePlanningJob(jobId);
  const job = jobQuery.data;

  useEffect(() => {
    if (job && isTerminalJobStatus(job.status)) {
      const entry = upsertJobHistory(job, lastRequest);
      if (entry) {
        setHistory(loadJobHistory());
      }
    }
  }, [job, lastRequest]);

  async function handleSubmit(payload: TripRequestPayload) {
    setSubmitError(null);
    setJobId(null);
    setLastRequest(payload);
    setIsSubmitting(true);

    try {
      const created = await startPlanningJob(payload);
      setJobId(created.job_id);
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error);
      } else {
        setSubmitError(new ApiError(0, { detail: "Unexpected error while starting the job." }));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleReset() {
    setJobId(null);
    setSubmitError(null);
    setLastRequest(null);
  }

  function handleSelectHistoryEntry(selectedJobId: string) {
    setSubmitError(null);
    setJobId(selectedJobId);
  }

  function handleClearHistory() {
    clearJobHistory();
    setHistory([]);
  }

  function handleRemoveHistoryEntry(selectedJobId: string) {
    removeJobHistoryEntry(selectedJobId);
    setHistory(loadJobHistory());
  }

  return (
    <div className="min-h-screen bg-sand font-marketing text-pine">
      <a
        href="#planner-main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-24 focus:z-50 focus:rounded-full focus:bg-paper focus:px-4 focus:py-2 focus:text-sm focus:text-pine"
      >
        Skip to planner
      </a>
      <header className="relative min-h-44 overflow-hidden">
        <img
          src={mountainRoad}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-pine/80 via-pine/55 to-pine/25" />
        <div className="relative mx-auto flex min-h-44 max-w-6xl flex-col justify-end gap-4 px-4 pt-8 pb-7 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="font-display text-4xl leading-none tracking-[-0.03em] text-paper sm:text-5xl">
              Plan the drive
            </h1>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-paper/90">
              Set the route and the dates. Each drive is checked on real roads.
            </p>
          </div>
          {jobId && (
            <button type="button" onClick={handleReset} className={`${quietButtonClass} w-full sm:w-auto`}>
              Plan another trip
            </button>
          )}
        </div>
      </header>

      <main
        id="planner-main"
        className="mx-auto grid max-w-6xl gap-6 px-4 pt-8 pb-12 sm:gap-8 lg:grid-cols-[280px_minmax(0,1fr)] lg:items-start"
      >
        <aside className="order-2 lg:order-1 lg:sticky lg:top-24">
          <JobHistoryPanel
            entries={history}
            activeJobId={jobId}
            onSelect={handleSelectHistoryEntry}
            onClear={handleClearHistory}
            onRemove={handleRemoveHistoryEntry}
          />
        </aside>

        <div className="order-1 grid gap-4 sm:gap-6 lg:order-2">
          {!jobId && <TripForm disabled={isSubmitting} onSubmit={handleSubmit} />}

          {submitError && (
            <ErrorAlert
              title={
                submitError.status === 422
                  ? "Trip request rejected"
                  : submitError.status === 429
                    ? "Planning limit reached"
                    : "Could not start planning"
              }
              message={
                typeof submitError.detail === "string" ? submitError.detail : submitError.message
              }
              detail={typeof submitError.detail === "string" ? undefined : submitError.detail}
            />
          )}

          {jobId && job && !isTerminalJobStatus(job.status) && (
            <ProgressPanel
              jobId={job.job_id}
              status={job.status}
              progress={job.progress}
              transport={jobQuery.transport}
            />
          )}

          {jobQuery.isError && (
            <ErrorAlert
              title={
                jobQuery.error instanceof ApiError && jobQuery.error.status === 404
                  ? "Job no longer available"
                  : "Could not load job status"
              }
              message={
                jobQuery.error instanceof ApiError && jobQuery.error.status === 404
                  ? "This trip is still in your local history, but the server no longer has the job (for example after a restart). Plan the trip again to regenerate it."
                  : jobQuery.error instanceof Error
                    ? jobQuery.error.message
                    : "Unknown polling error"
              }
            />
          )}

          {job?.status === "failed" && (
            <ErrorAlert title="Planning failed" message={job.error ?? "The planning job failed."} />
          )}

          {job?.status === "completed" && job.result && (
            <>
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                <CopyJsonButton label="Copy result JSON" value={job.result} />
                <CopyJsonButton label="Copy full job JSON" value={job} />
              </div>
              <ValidationSummary
                validation={job.result.validation}
                replanAttempts={job.result.replan_attempts}
              />
              <TripMap plan={job.result.plan} />
              <ItineraryView plan={job.result.plan} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
