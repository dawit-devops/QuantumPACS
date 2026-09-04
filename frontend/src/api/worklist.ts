import { request } from "./client";

export interface WorklistEntry {
  id: number;
  patient_id?: string;
  patient_name?: string;
  patient_birth_date?: string;
  patient_sex?: string;
  accession_number?: string;
  requested_procedure_id?: string;
  requested_procedure_desc?: string;
  modality?: string;
  status?: string;
  scheduled_date?: string;
  scheduled_time?: string;
  performed_at?: string | null;
  description?: string;
  station_ae_title?: string | string[];
}

export interface WorklistPage {
  data: WorklistEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface StationAe {
  ae_title?: string;
  [key: string]: unknown;
}

export const listWorklist = (
  query: Record<string, string>,
): Promise<WorklistPage> => request<WorklistPage>("worklist", { query });

export interface MwlSyncStats {
  synced: boolean;
  pushed: number;
  status: number;
  removed: number;
  failed: number;
  reason?: string;
}

// T-05: manual MWL sync trigger — replays dirty entries to the archive.
export const syncWorklist = (): Promise<MwlSyncStats> =>
  request<{ data: MwlSyncStats }>("worklist/sync", { method: "POST" }).then(
    (res) => res?.data ?? { synced: false, pushed: 0, status: 0, removed: 0, failed: 0 },
  );

export const listStationAes = (): Promise<StationAe[]> =>
  request<StationAe[]>("worklist/station-aes", { method: "GET" });

export const createWorklistEntry = (
  data: Record<string, unknown>,
): Promise<WorklistEntry> =>
  request<WorklistEntry>("worklist", { data }).then((res) => res ?? {});

export const updateWorklistEntry = (
  id: number | string,
  data: Record<string, unknown>,
): Promise<void> => request(`worklist/${id}`, { method: "PUT", data });

export const deleteWorklistEntry = (id: number | string): Promise<void> =>
  request(`worklist/${id}`, { data: undefined, method: "DELETE" });

export const markWorklistPerformed = (id: number | string): Promise<void> =>
  request(`worklist/${id}`, { method: "PUT", data: { status: "performed" } });
