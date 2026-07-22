import type {
  JobStatus,
  PlanningJobResponse,
  TripRequestPayload,
  TripResponse,
} from "../api/client";
import { stripRouteGeometryFromTripResponse } from "./tripExport";

export interface JobHistoryEntry {
  job_id: string;
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  status: JobStatus;
  updated_at: string;
  plan_title?: string;
  request?: TripRequestPayload;
  result?: TripResponse | null;
}

const STORAGE_KEY = "roadtrip-planner.job-history";
const MAX_ENTRIES = 20;
const MAX_FULL_RESULTS = 10;

function normalizeEntry(entry: JobHistoryEntry): JobHistoryEntry {
  if (!entry.result) {
    return entry;
  }
  return {
    ...entry,
    result: stripRouteGeometryFromTripResponse(entry.result),
  };
}

function readHistory(): JobHistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as JobHistoryEntry[];
    return Array.isArray(parsed) ? parsed.map(normalizeEntry) : [];
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

export function getJobHistoryEntry(jobId: string): JobHistoryEntry | undefined {
  return readHistory().find((item) => item.job_id === jobId);
}

export function upsertJobHistory(
  job: PlanningJobResponse,
  request: TripRequestPayload | null,
): JobHistoryEntry | null {
  if (job.status !== "completed" && job.status !== "failed") {
    return null;
  }

  const latestProgress = job.progress.at(-1);
  const existing = readHistory().find((item) => item.job_id === job.job_id);

  const entry: JobHistoryEntry = {
    job_id: job.job_id,
    origin: request?.origin ?? existing?.origin ?? "Unknown origin",
    destination: request?.destination ?? existing?.destination ?? "Unknown destination",
    start_date: request?.start_date ?? job.result?.plan.days[0]?.date ?? existing?.start_date ?? "",
    end_date:
      request?.end_date ?? job.result?.plan.days.at(-1)?.date ?? existing?.end_date ?? "",
    status: job.status,
    updated_at: latestProgress?.timestamp ?? new Date().toISOString(),
    plan_title: job.result?.plan.title,
    request: request ?? existing?.request,
    result: (() => {
      const rawResult = job.result ?? existing?.result ?? null;
      return rawResult ? stripRouteGeometryFromTripResponse(rawResult) : null;
    })(),
  };

  const withoutCurrent = readHistory().filter((item) => item.job_id !== job.job_id);
  const next = [entry, ...withoutCurrent];

  let fullResultCount = 0;
  const trimmed = next.map((item) => {
    if (item.result) {
      fullResultCount += 1;
      if (fullResultCount > MAX_FULL_RESULTS) {
        return { ...item, result: undefined };
      }
    }
    return item;
  });

  writeHistory(trimmed);
  return entry;
}

export function clearJobHistory(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function removeJobHistoryEntry(jobId: string): void {
  writeHistory(readHistory().filter((item) => item.job_id !== jobId));
}
