import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  fetchPlanningJob,
  isTerminalJobStatus,
  type PlanningJobResponse,
} from "../api/client";

const API_BASE = "/api";

function parseJobEvent(data: string): PlanningJobResponse {
  return JSON.parse(data) as PlanningJobResponse;
}

export function usePlanningJob(jobId: string | null) {
  const queryClient = useQueryClient();
  const [usePollingFallback, setUsePollingFallback] = useState(false);

  const query = useQuery({
    queryKey: ["planning-job", jobId],
    queryFn: () => fetchPlanningJob(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (currentQuery) => {
      if (!usePollingFallback) {
        return false;
      }
      const status = currentQuery.state.data?.status;
      if (status && isTerminalJobStatus(status)) {
        return false;
      }
      return 2000;
    },
  });

  useEffect(() => {
    if (!jobId || usePollingFallback) {
      return;
    }

    const source = new EventSource(`${API_BASE}/trips/jobs/${jobId}/events`);

    source.onmessage = (event) => {
      const job = parseJobEvent(event.data);
      queryClient.setQueryData(["planning-job", jobId], job);
      if (isTerminalJobStatus(job.status)) {
        source.close();
      }
    };

    source.onerror = () => {
      source.close();
      setUsePollingFallback(true);
      void queryClient.invalidateQueries({ queryKey: ["planning-job", jobId] });
    };

    return () => {
      source.close();
    };
  }, [jobId, queryClient, usePollingFallback]);

  useEffect(() => {
    setUsePollingFallback(false);
  }, [jobId]);

  return {
    ...query,
    transport: usePollingFallback ? ("polling" as const) : ("sse" as const),
  };
}
