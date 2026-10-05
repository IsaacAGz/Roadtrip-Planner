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
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-3 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-4 sm:py-6">
          <div>
            <h1 className="font-serif text-3xl leading-none tracking-[-0.03em] text-ink sm:text-4xl">
              Roadtrip Planner
            </h1>
            <p className="mt-2 text-sm text-muted">AI itineraries with OSRM-verified driving segments</p>
          </div>
          {jobId && (
            <button
              type="button"
              onClick={handleReset}
              className="w-full rounded-md border border-line bg-surface px-3 py-2 font-sans text-sm font-medium text-ink transition-transform duration-200 hover:bg-canvas active:scale-[0.98] sm:w-auto"
            >
              Plan another trip
            </button>
          )}
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-8 px-3 py-8 sm:px-4">
        <JobHistoryPanel
          entries={history}
          activeJobId={jobId}
          onSelect={handleSelectHistoryEntry}
          onClear={handleClearHistory}
          onRemove={handleRemoveHistoryEntry}
        />

        <div className="grid gap-4 sm:gap-6">
          {!jobId && <TripForm disabled={isSubmitting} onSubmit={handleSubmit} />}

          {submitError && (
            <ErrorAlert
              title={submitError.status === 422 ? "Trip request rejected" : "Could not start planning"}
              message={submitError.message}
              detail={submitError.detail}
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
