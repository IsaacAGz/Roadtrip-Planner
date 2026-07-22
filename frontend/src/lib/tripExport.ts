import type { PlanningJobResponse, RoadtripPlan, TripResponse } from "../api/client";

export function stripRouteGeometryFromPlan(plan: RoadtripPlan): RoadtripPlan {
  const { route_geometry: _geometry, ...rest } = plan;
  return rest;
}

export function stripRouteGeometryFromTripResponse(result: TripResponse): TripResponse {
  return {
    ...result,
    plan: stripRouteGeometryFromPlan(result.plan),
  };
}

export function stripRouteGeometryFromJobResponse(job: PlanningJobResponse): PlanningJobResponse {
  if (!job.result) {
    return job;
  }
  return {
    ...job,
    result: stripRouteGeometryFromTripResponse(job.result),
  };
}
