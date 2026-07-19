import type { JobStatus, PlanningJobResponse, TripRequestPayload } from "../api/client";

export interface JobHistoryEntry {
  job_id: string;
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  status: JobStatus;
  updated_at: string;
  plan_title?: string;
}

const STORAGE_KEY = "roadtrip-planner.job-history";
const MAX_ENTRIES = 20;

function readHistory(): JobHistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as JobHistoryEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeHistory(entries: JobHistoryEntry[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, MAX_ENTRIES)));
}

export function loadJobHistory(): JobHistoryEntry[] {
  return readHistory();
}

export function upsertJobHistory(
  job: PlanningJobResponse,
  request: TripRequestPayload | null,
): JobHistoryEntry | null {
  if (job.status !== "completed" && job.status !== "failed") {
    return null;
  }

  const latestProgress = job.progress.at(-1);
  const entry: JobHistoryEntry = {
    job_id: job.job_id,
    origin: request?.origin ?? "Unknown origin",
    destination: request?.destination ?? "Unknown destination",
    start_date: request?.start_date ?? job.result?.plan.days[0]?.date ?? "",
    end_date: request?.end_date ?? job.result?.plan.days.at(-1)?.date ?? "",
    status: job.status,
    updated_at: latestProgress?.timestamp ?? new Date().toISOString(),
    plan_title: job.result?.plan.title,
  };

  const existing = readHistory().filter((item) => item.job_id !== job.job_id);
  writeHistory([entry, ...existing]);
  return entry;
}

export function clearJobHistory(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function removeJobHistoryEntry(jobId: string): void {
  writeHistory(readHistory().filter((item) => item.job_id !== jobId));
}
