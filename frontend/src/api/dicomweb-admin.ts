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
