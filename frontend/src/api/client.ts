import type { TripRequestPayload } from "../lib/tripPayload";

export type JobStatus = "queued" | "running" | "completed" | "failed";

export type ProgressStage =
  | "queued"
  | "planning"
  | "hard_validation"
  | "soft_validation"
  | "completed"
  | "failed";

export type {
  Budget,
  Pace,
  TripConstraints,
  TripPreferences,
  TripRequestPayload,
} from "../lib/tripPayload";
export interface PlanningJobCreatedResponse {
  job_id: string;
  status: JobStatus;
  status_url: string;
  events_url: string;
}

export interface ProgressEvent {
  stage: ProgressStage;
  message: string;
  attempt: number | null;
  timestamp: string;
}

export interface PlaceContact {
  phone?: string | null;
  website?: string | null;
  address?: string | null;
  opening_hours?: string | null;
  reservation_required?: boolean;
}

export interface Stop {
  name: string;
  lat: number;
  lon: number;
  category: string;
  duration_hours: number;
  description: string;
  country_code: string;
  contact?: PlaceContact;
}

export interface OvernightStop {
  city: string;
  lat: number;
  lon: number;
  stay_type: string;
  nights: number;
  is_return_stop: boolean;
  country_code: string;
  property_name?: string | null;
  contact?: PlaceContact;
}

export interface DayWeather {
  summary: string;
  min_temp_c: number;
  max_temp_c: number;
  max_precip_chance: number;
}

export interface DayPlan {
  day: number;
  date: string;
  route_summary: string;
  driving_hours: number;
  stops: Stop[];
  overnight: OvernightStop;
  weather?: DayWeather | null;
  leg_start_lat?: number | null;
  leg_start_lon?: number | null;
  leg_end_lat?: number | null;
  leg_end_lon?: number | null;
}

export interface RoadtripPlan {
  title: string;
  total_days: number;
  origin_lat: number;
  origin_lon: number;
  destination_lat: number;
  destination_lon: number;
  days: DayPlan[];
  tips: string[];
  route_geometry?: number[][];
}

export interface RuleViolation {
  rule_id: string;
  severity: "error" | "warning" | "info";
  day: number | null;
  message: string;
  actual?: number | string | null;
  limit?: number | string | null;
}

export interface ValidationReport {
  approved: boolean;
  hard_failures: RuleViolation[];
  warnings: RuleViolation[];
  replan_attempts: number;
}

export interface TripResponse {
  plan: RoadtripPlan;
  validation: ValidationReport;
  replan_attempts: number;
}

export interface PlanningJobResponse {
  job_id: string;
  status: JobStatus;
  progress: ProgressEvent[];
  result: TripResponse | null;
  error: string | null;
}

export interface FeasibilityErrorDetail {
  rule_id: string;
  message: string;
  actual?: number | string | null;
  limit?: number | string | null;
}

export interface PydanticErrorDetail {
  type: string;
  loc: (string | number)[];
  msg: string;
}

export type ApiErrorDetail =
  | FeasibilityErrorDetail
  | PydanticErrorDetail[]
  | { detail: string };

export class ApiError extends Error {
  status: number;
  detail: ApiErrorDetail;

  constructor(status: number, detail: ApiErrorDetail, message?: string) {
    super(message ?? `Request failed with status ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export function formatApiErrorMessage(detail: ApiErrorDetail): string {
  if (Array.isArray(detail)) {
    return detail.map((item) => `${item.loc.join(".")}: ${item.msg}`).join("\n");
  }

  if ("rule_id" in detail) {
    return `${detail.rule_id}: ${detail.message}`;
  }

  if ("detail" in detail && typeof detail.detail === "string") {
    return detail.detail;
  }

  return "Unknown error format.";
}

const API_BASE = "/api";

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const body = (await response.json()) as T | { detail: ApiErrorDetail };
  if (!response.ok) {
    const detail = (body as { detail: ApiErrorDetail }).detail ?? body;
    throw new ApiError(response.status, detail as ApiErrorDetail);
  }
  return body as T;
}

export async function startPlanningJob(
  payload: TripRequestPayload,
): Promise<PlanningJobCreatedResponse> {
  const response = await fetch(`${API_BASE}/trips/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse<PlanningJobCreatedResponse>(response);
}

export async function fetchPlanningJob(jobId: string): Promise<PlanningJobResponse> {
  const response = await fetch(`${API_BASE}/trips/jobs/${jobId}`);
  return parseJsonResponse<PlanningJobResponse>(response);
}

export function isTerminalJobStatus(status: JobStatus): boolean {
  return status === "completed" || status === "failed";
}
