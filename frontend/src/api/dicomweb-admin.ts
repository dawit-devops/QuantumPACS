import { request } from "./client";

export interface DicomwebAdminInfo {
  qido?: {
    enabled: boolean;
    endpoints: Array<Record<string, unknown>>;
    search_params: Array<Record<string, unknown>>;
    response_format: string;
  };
  [key: string]: unknown;
}

export const getDicomwebAdmin = (): Promise<DicomwebAdminInfo> =>
  request<DicomwebAdminInfo>("dicomweb/admin");

export interface DicomwebModalityCount {
  modality: string;
  count: number;
}

export interface DicomwebRequestCount {
  kind: string;
  total: number;
  errors: number;
}

export interface DicomwebMetrics {
  period: string;
  files_stored: number;
  studies_stored: number;
  failed_stores: number;
  storage_bytes: number;
  requests_total: number;
  requests_failed: number;
  requests_by_kind?: DicomwebRequestCount[];
  by_modality?: DicomwebModalityCount[];
  totals: {
    studies: number;
    series: number;
    files: number;
  };
}

export const getDicomwebMetrics = (
  period: string = "24h",
): Promise<DicomwebMetrics> =>
  request<DicomwebMetrics>("dicomweb/admin/metrics", {
    query: { period },
  });

export interface DicomwebRequestLog {
  id: number;
  created_at: string | null;
  kind: string | null;
  method: string | null;
  path: string | null;
  status: number | null;
  duration_ms: number | null;
  actor: number | string | null;
  tenant: string | null;
  request_id: string | null;
  trace_id: string | null;
}

export interface DicomwebRequestsResponse {
  data: DicomwebRequestLog[];
  next_cursor: number | null;
  has_more: boolean;
  total: number;
}

export const getDicomwebRequests = (
  params: {
    limit?: number;
    cursor?: number;
    kind?: string;
    status?: number;
    period?: string;
  } = {},
): Promise<DicomwebRequestsResponse> => {
  const query: Record<string, string> = { limit: String(params.limit ?? 50) };
  if (params.cursor !== undefined) query.cursor = String(params.cursor);
  if (params.kind) query.kind = params.kind;
  if (params.status !== undefined) query.status = String(params.status);
  if (params.period) query.period = params.period;
  return request<DicomwebRequestsResponse>("dicomweb/admin/requests", {
    query,
  });
};
