import { request } from "./client";

export interface TrackingEntry {
  id: string;
  patient_id: string;
  patient_name: string;
  accession_number: string;
  modality: string;
  status: string;
  requested_procedure_priority: string;
  station_ae_title: string;
  scheduled_date: string;
  scheduled_time: string;
  requested_procedure_desc: string;
  protocol_name?: string;
  exam_status?: string;
  assigned_technologist?: string;
}

export interface TrackingPage {
  data: TrackingEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface TrackingKpi {
  volume: number;
  in_progress: number;
  awaiting_read: number;
  overdue: number;
  stat_count: number;
}

export interface TimelineEntry {
  event_type: string;
  actor_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

export const listTracking = (
  query: Record<string, string>,
): Promise<TrackingPage> => request<TrackingPage>("ris/tracking", { query });

export const getTrackingKpi = (): Promise<TrackingKpi> =>
  request<TrackingKpi>("ris/tracking/kpi", { method: "GET" });

export const getTrackingTimeline = (
  id: string,
): Promise<{ data: TimelineEntry[] }> =>
  request(`ris/tracking/${id}/timeline`, { method: "GET" });

export const updateTrackingStatus = (
  id: string,
  status: string,
): Promise<{ data: { status: string } }> =>
  request(`ris/tracking/${id}/status`, {
    method: "PUT",
    data: { status },
  });
