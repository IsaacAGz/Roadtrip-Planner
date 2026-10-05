import type { TripRequestPayload } from "./tripPayload";

export interface PlanHandoff {
  requestId: string;
  payload: TripRequestPayload;
}

const startedRequestIds = new Set<string>();

export function readPlanHandoff(state: unknown): PlanHandoff | null {
  if (!state || typeof state !== "object") {
    return null;
  }

  const record = state as Partial<PlanHandoff>;
  const payload = record.payload;
  if (typeof record.requestId !== "string" || !payload || typeof payload !== "object") {
    return null;
  }

  if (
    typeof payload.origin !== "string" ||
    typeof payload.destination !== "string" ||
    typeof payload.start_date !== "string" ||
    typeof payload.end_date !== "string"
  ) {
    return null;
  }

  return { requestId: record.requestId, payload };
}

export function claimPlanHandoff(requestId: string): boolean {
  if (startedRequestIds.has(requestId)) {
    return false;
  }
  startedRequestIds.add(requestId);
  return true;
}
