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

export interface HealthStatus {
  status?: string;
  database?: string;
  [key: string]: unknown;
}

export const getDashboardMetrics = (range: string): Promise<DashboardMetrics> =>
  request<DashboardMetrics>("v2/dashboard/metrics", {
    query: { range },
  });

export const getHealth = (): Promise<HealthStatus | null> =>
  request<HealthStatus>("v2/health").catch(() => null);
