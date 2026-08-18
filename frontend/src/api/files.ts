import { request } from "./client";
import type { PatientSummary } from "./patient";

export type DicomJsonObject = Record<string, unknown>;

// QIDO-RS returns a bare DICOM JSON array (possibly wrapped in {data} by a
// legacy proxy layer — accept both so callers don't care).
export const qidoSearch = (
  params: Record<string, string>,
): Promise<DicomJsonObject[]> =>
  request<DicomJsonObject[] | { data: DicomJsonObject[] }>(
    "v2/dicomweb/studies",
    { query: params },
  ).then((res) => (Array.isArray(res) ? res : (res?.data ?? [])));

export interface FileSearchResult {
  data: Record<string, unknown>[];
  total?: number;
  // P2-5 (tenant_admin review): false when the search backend was down, so
  // the Files page can distinguish a degraded search from an empty archive.
  search_available?: boolean;
}

// POST /api/files runs an Elasticsearch query for the file browser.
export const searchFiles = (payload: unknown): Promise<FileSearchResult> =>
  request<FileSearchResult>("files", { data: payload });

export interface FileChange {
  id?: number;
  event?: string;
  created_at?: string;
  detail?: Record<string, unknown> | string | null;
  [key: string]: unknown;
}

export interface FileShare {
  id: number;
  token?: string;
  expires_at?: string | null;
  created_at?: string;
  [key: string]: unknown;
}

export interface FileNode {
  id: number;
  name?: string;
  hash?: string;
  indexed?: boolean;
  sop_instance_uid?: string;
  deleted?: boolean;
}

export interface FileSeries {
  id: number;
  study_id?: number;
  number?: string | number;
  modality?: string;
  description?: string;
  series_instance_uid?: string;
  files?: FileNode[];
}

export interface FileStudy {
  id: number;
  study_id?: string;
  description?: string;
  study_instance_uid?: string;
  accession_number?: string;
  series?: FileSeries[];
}

export interface FileRecord {
  id: number;
  name?: string;
  meta?: Record<string, unknown>;
  tools_state?: unknown;
  patient_db_id?: number;
  study_db_id?: number;
  series_db_id?: number;
  patient_id?: string;
  patient?: PatientSummary & { studies?: FileStudy[] };
}

export const getFile = (id: number | string): Promise<FileRecord> =>
  request<FileRecord>(`files/${id}`);

export const deleteFile = (id: number | string): Promise<void> =>
  request(`files/${id}`, { method: "DELETE" });

export const listFileChanges = (
  id: number,
  params: Record<string, string> = {},
): Promise<FileChange[]> =>
  request<{ data: FileChange[] } | FileChange[]>(`files/${id}/changes`, {
    query: params,
  }).then((res) => (Array.isArray(res) ? res : (res?.data ?? [])));

export const listFileShares = (id: number | string): Promise<FileShare[]> =>
  request<{ data: FileShare[] } | FileShare[]>(`files/${id}/shares`, {
    method: "GET",
  }).then((res) => (Array.isArray(res) ? res : (res?.data ?? [])));

export const createFileShare = (
  id: number,
  data: Record<string, unknown>,
): Promise<FileShare> =>
  request<FileShare>(`files/${id}/share`, { data }).then((res) => res ?? {});

export const revokeFileShare = (
  id: number | string,
  shareId: number | string,
): Promise<void> =>
  request(`files/${id}/shares/${shareId}`, { method: "DELETE" });
