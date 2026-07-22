import { useEffect, useState } from "react";
import {
  ApiError,
  isTerminalJobStatus,
  startPlanningJob,
  type PlanningJobResponse,
  type TripRequestPayload,
  type TripResponse,
} from "./api/client";
import { CopyJsonButton } from "./components/CopyJsonButton";
import { DownloadJsonButton } from "./components/DownloadJsonButton";
import { ErrorAlert } from "./components/ErrorAlert";
import { ItineraryView } from "./components/ItineraryView";
import { JobHistoryPanel } from "./components/JobHistoryPanel";
import { ProgressPanel } from "./components/ProgressPanel";
import { TripForm, type TripFormValues } from "./components/TripForm";
import { TripMap } from "./components/TripMap";
import { ValidationSummary } from "./components/ValidationSummary";
import { usePlanningJob } from "./hooks/usePlanningJob";
import { payloadToFormValues } from "./lib/formPersistence";
import {
  stripRouteGeometryFromJobResponse,
  stripRouteGeometryFromTripResponse,
} from "./lib/tripExport";
import {
  clearJobHistory,
  getJobHistoryEntry,
  loadJobHistory,
  removeJobHistoryEntry,
  upsertJobHistory,
  type JobHistoryEntry,
} from "./lib/jobHistory";

function resultFilename(result: TripResponse): string {
  const slug = result.plan.title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
  const start = result.plan.days[0]?.date ?? "trip";
  const end = result.plan.days.at(-1)?.date ?? start;
  return `${slug || "roadtrip"}-${start}-to-${end}.json`;
}

export function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastRequest, setLastRequest] = useState<TripRequestPayload | null>(null);
  const [history, setHistory] = useState<JobHistoryEntry[]>(() => loadJobHistory());
  const [formInitialValues, setFormInitialValues] = useState<TripFormValues | undefined>();
  const [offlineResult, setOfflineResult] = useState<TripResponse | null>(null);
  const [showForm, setShowForm] = useState(true);

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
    setOfflineResult(null);
    setShowForm(false);
    setLastRequest(payload);
    setIsSubmitting(true);

    try {
      const created = await startPlanningJob(payload);
      setJobId(created.job_id);
    } catch (error) {
      setShowForm(true);
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
    setOfflineResult(null);
    setShowForm(true);
    setFormInitialValues(undefined);
  }

  function handleSelectHistoryEntry(selectedJobId: string) {
    setSubmitError(null);
    setOfflineResult(null);
    setShowForm(false);
    setJobId(selectedJobId);
  }

  function handleViewSaved(entry: JobHistoryEntry) {
    if (!entry.result) {
      return;
    }
    setSubmitError(null);
    setJobId(null);
    setOfflineResult(entry.result);
    setShowForm(false);
  }

  function handlePlanAgain(entry: JobHistoryEntry) {
    if (!entry.request) {
      return;
    }
    setSubmitError(null);
    setJobId(null);
    setOfflineResult(null);
    setFormInitialValues(payloadToFormValues(entry.request));
    setShowForm(true);
  }

  function handleClearHistory() {
    clearJobHistory();
    setHistory([]);
  }

  function handleRemoveHistoryEntry(selectedJobId: string) {
    removeJobHistoryEntry(selectedJobId);
    setHistory(loadJobHistory());
  }

  function renderCompletedResult(result: TripResponse, jobSnapshot?: PlanningJobResponse) {
    return (
      <>
        <div className="no-print flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          <CopyJsonButton
            label="Copy result JSON"
            value={stripRouteGeometryFromTripResponse(result)}
          />
          {jobSnapshot && (
            <CopyJsonButton
              label="Copy full job JSON"
              value={stripRouteGeometryFromJobResponse(jobSnapshot)}
            />
          )}
          <DownloadJsonButton
            label="Download JSON"
            value={stripRouteGeometryFromTripResponse(result)}
            filename={resultFilename(result)}
          />
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Print itinerary
          </button>
        </div>
        <ValidationSummary
          validation={result.validation}
          replanAttempts={result.replan_attempts}
        />
        <TripMap plan={result.plan} />
        <ItineraryView plan={result.plan} />
      </>
    );
  }

  const cachedEntry = jobId ? getJobHistoryEntry(jobId) : undefined;
  const showOfflineFallback =
    jobQuery.isError &&
    jobQuery.error instanceof ApiError &&
    jobQuery.error.status === 404 &&
    cachedEntry?.result != null;

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="no-print border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-3 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-4 sm:py-5">
          <div>
            <h1 className="text-xl font-bold text-slate-900 sm:text-2xl">Roadtrip Planner</h1>
            <p className="text-sm text-slate-600">AI itineraries with OSRM-verified driving segments</p>
          </div>
          {(jobId || offlineResult) && (
            <button
              type="button"
              onClick={handleReset}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 sm:w-auto"
            >
              Plan another trip
            </button>
          )}
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-4 px-3 py-6 sm:gap-6 sm:px-4 sm:py-8 lg:grid-cols-[280px_minmax(0,1fr)] lg:items-start">
        <aside className="order-2 lg:order-1 lg:sticky lg:top-6">
          <JobHistoryPanel
            entries={history}
            activeJobId={jobId}
            onSelect={handleSelectHistoryEntry}
            onViewSaved={handleViewSaved}
            onPlanAgain={handlePlanAgain}
            onClear={handleClearHistory}
            onRemove={handleRemoveHistoryEntry}
          />
        </aside>

        <div className="order-1 grid gap-4 sm:gap-6 lg:order-2">
          {showForm && (
            <TripForm
              disabled={isSubmitting}
              initialValues={formInitialValues}
              onSubmit={handleSubmit}
            />
          )}

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

          {jobQuery.isError && !showOfflineFallback && (
            <ErrorAlert
              title={
                jobQuery.error instanceof ApiError && jobQuery.error.status === 404
                  ? "Job no longer available"
                  : "Could not load job status"
              }
              message={
                jobQuery.error instanceof ApiError && jobQuery.error.status === 404
                  ? "This trip is still in your local history, but the server no longer has the job (for example after a restart). Use View saved or Plan again from the sidebar."
                  : jobQuery.error instanceof Error
                    ? jobQuery.error.message
                    : "Unknown polling error"
              }
            />
          )}

          {showOfflineFallback && cachedEntry?.result && (
            <>
              <ErrorAlert
                title="Showing saved copy"
                message="The server no longer has this job, so results below are loaded from your browser history."
              />
              {renderCompletedResult(cachedEntry.result)}
            </>
          )}

          {job?.status === "failed" && (
            <ErrorAlert title="Planning failed" message={job.error ?? "The planning job failed."} />
          )}

          {job?.status === "completed" && job.result && renderCompletedResult(job.result, job)}

          {offlineResult && renderCompletedResult(offlineResult)}
        </div>
      </main>
    </div>
  );
}
