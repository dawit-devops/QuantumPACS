import { request } from "./client";

export interface TatByPriority {
  priority: string;
  p95_seconds: number;
}

export interface UnbilledAging {
  total_unbilled: number;
}

export interface DrillDownRow {
  exam_id: string;
  accession_number: string;
  priority: string;
  tat_seconds: number;
}

export interface PriorAuthMixRow {
  status: string;
  n: number;
}

export interface RisDashboardKpi {
  tat_by_priority: TatByPriority[];
  prior_auth?: {
    mix: PriorAuthMixRow[];
    approval_rate: number;
  };
  utilization: number;
  unbilled_aging: UnbilledAging;
  volume: number;
  drill_down: DrillDownRow[];
}

// S12-34: manager dashboard KPIs (TAT, utilization, unbilled aging, volume).
export const getRisDashboardKpi = (
  drillDown = false,
): Promise<RisDashboardKpi> =>
  request<RisDashboardKpi>("ris/dashboard/kpi", {
    query: drillDown ? { drill_down: "true" } : {},
  });