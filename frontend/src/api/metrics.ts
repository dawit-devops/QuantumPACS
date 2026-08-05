import { request } from "./client";

export interface DashboardMetrics {
  total_patients?: number;
  total_studies?: number;
  total_series?: number;
  total_files?: number;
  total_users?: number;
  storage_bytes?: number;
  [key: string]: unknown;
}

export type ComponentStatus = "ok" | "degraded" | "error";

export interface HealthComponent {
  status: ComponentStatus;
  latency_ms?: number;
  message?: string;
  [key: string]: unknown;
}

export interface HealthStatus {
  status: "ok" | "degraded";
  uptime_seconds?: number;
  components: Record<string, HealthComponent>;
  [key: string]: unknown;
}

export const getDashboardMetrics = (range: string): Promise<DashboardMetrics> =>
  request<DashboardMetrics>("v2/dashboard/metrics", {
    query: { range },
  });

// 403 (no METRICS_READ) resolves null so the System Health card degrades to
// its graceful OK state for low-privilege users; any other failure rethrows
// so the card can surface "metrics unavailable" + retry (AC-R01-19).
export const getHealth = (): Promise<HealthStatus | null> =>
  request<HealthStatus>("v2/dashboard/health").catch((e: any) => {
    if (e?.status === 403) return null;
    throw e;
  });
