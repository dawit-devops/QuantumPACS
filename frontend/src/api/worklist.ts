import { request } from "./client";

export interface WorklistEntry {
  id: number;
  patient_id?: string;
  patient_name?: string;
  accession_number?: string;
  modality?: string;
  status?: string;
  scheduled_time?: string;
  performed_at?: string | null;
  description?: string;
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
): Promise<WorklistPage> =>
  request<WorklistPage>("worklist", { query });

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
