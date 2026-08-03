import { request } from "./client";

export interface FhirConfig {
  enabled: string;
  base_url?: string;
  publisher?: string;
  max_search_results?: string;
  log_retention_days?: string;
}

export interface FhirClient {
  id: string;
  client_id?: string;
  name?: string;
  description?: string;
  active?: boolean;
  redirect_uris?: string;
  created_at?: string;
}

export interface FhirLatency {
  p50: number;
  p95: number;
  p99: number;
}

export interface FhirMetrics {
  period: string;
  total_requests: number;
  error_rate: number;
  volume: Record<string, unknown>[];
  status_codes: Record<string, unknown>[];
  latency: FhirLatency;
  top_clients: Record<string, unknown>[];
}

export interface FhirRequestsParams {
  limit?: number;
  offset?: number;
  resource_type?: string;
  status_min?: string;
}

export interface FhirRequestsPage {
  requests: Record<string, unknown>[];
  total: number;
}

export interface FhirTestResult {
  reachable: boolean;
  status_code: number;
  response_time_ms: number;
  error?: string;
  fhir_version?: string;
}

export const getFhirConfig = (): Promise<FhirConfig> =>
  request<FhirConfig>("fhir/admin/config");

export const updateFhirConfig = (
  data: Partial<FhirConfig>,
): Promise<FhirConfig> =>
  request<FhirConfig>("fhir/admin/config", { method: "PUT", data });

export const listFhirClients = (): Promise<FhirClient[]> =>
  request<{ clients: FhirClient[] }>("fhir/admin/clients").then(
    (res) => res.clients ?? [],
  );

export const createFhirClient = (
  data: Record<string, unknown>,
): Promise<FhirClient> =>
  request<FhirClient>("fhir/admin/clients", { method: "POST", data });

export const updateFhirClient = (
  id: string,
  data: Record<string, unknown>,
): Promise<FhirClient> =>
  request<FhirClient>(`fhir/admin/clients/${id}`, { method: "PUT", data });

export const deleteFhirClient = (id: string): Promise<void> =>
  request(`fhir/admin/clients/${id}`, { method: "DELETE" });

export const getFhirMetrics = (period: string): Promise<FhirMetrics> =>
  request<FhirMetrics>("fhir/admin/metrics", { query: { period } });

export const getFhirRecentRequests = (
  params: FhirRequestsParams,
): Promise<FhirRequestsPage> =>
  request<FhirRequestsPage>("fhir/admin/requests", {
    query: params as Record<string, string>,
  });

export const testFhirConnection = (): Promise<FhirTestResult> =>
  request<FhirTestResult>("fhir/admin/test");

export const getFhirMetadata = (): Promise<Record<string, unknown>> =>
  request<Record<string, unknown>>("fhir/metadata");

export const fhirResourceRequest = (
  path: string,
): Promise<Record<string, unknown>> => request<Record<string, unknown>>(path);
