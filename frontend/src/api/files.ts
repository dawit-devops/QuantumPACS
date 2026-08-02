import { request } from "./client";

export type DicomJsonObject = Record<string, unknown>;

// QIDO-RS returns a bare DICOM JSON array (possibly wrapped in {data} by a
// legacy proxy layer — accept both so callers don't care).
export const qidoSearch = (
  params: Record<string, string>,
): Promise<DicomJsonObject[]> =>
  request<DicomJsonObject[] | { data: DicomJsonObject[] }>(
    "v2/dicomweb/studies",
    { query: params },
  ).then((res) => (Array.isArray(res) ? res : res?.data ?? []));

export interface FileSearchResult {
  data: Record<string, unknown>[];
  total?: number;
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

export const getFile = (id: number | string): Promise<Record<string, unknown>> =>
  request<Record<string, unknown>>(`files/${id}`);

export const deleteFile = (id: number | string): Promise<void> =>
  request(`files/${id}`, { method: "DELETE" });

export const listFileChanges = (
  id: number,
  params: Record<string, string> = {},
): Promise<FileChange[]> =>
  request<{ data: FileChange[] } | FileChange[]>(`files/${id}/changes`, {
    query: params,
  }).then((res) => (Array.isArray(res) ? res : res?.data ?? []));

export const listFileShares = (id: number | string): Promise<FileShare[]> =>
  request<{ data: FileShare[] } | FileShare[]>(`files/${id}/shares`, {
    method: "GET",
  }).then((res) => (Array.isArray(res) ? res : res?.data ?? []));

export const createFileShare = (
  id: number,
  data: Record<string, unknown>,
): Promise<FileShare> =>
  request<FileShare>(`files/${id}/share`, { data }).then((res) => res ?? {});

export const revokeFileShare = (
  id: number | string,
  shareId: number | string,
): Promise<void> => request(`files/${id}/shares/${shareId}`, { method: "DELETE" });
