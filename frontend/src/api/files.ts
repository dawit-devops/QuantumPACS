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
