import { request } from "./client";
import { API_URL } from "../config";

export interface LogEntry {
  id: number;
  created_at?: string | null;
  event_type?: string | null;
  actor?: string;
  resource_type?: string | null;
  resource_id?: string | null;
  description?: string | null;
  tenant?: string | null;
  payload?: Record<string, unknown>;
}

export interface LogQuery {
  event_type?: string;
  actor?: string;
  date_from?: string;
  date_to?: string;
  tenant?: string;
  cursor?: number;
  limit?: number;
}

export interface LogList {
  data: LogEntry[];
  next_cursor: number | null;
  has_more: boolean;
  total: number;
}

export const listLogs = (query: LogQuery): Promise<LogList> =>
  request<LogList>("logs", { query: query as Record<string, string> });

export async function downloadLogsCsv(query: LogQuery): Promise<void> {
  // P2-2: server-side CSV of the FULL filtered result set (not the current
  // page). Raw fetch — the response is a CSV attachment, not the JSON
  // envelope request() unwraps.
  const params = new URLSearchParams();
  params.set("download", "csv");
  if (query.event_type) params.set("event_type", query.event_type);
  if (query.actor) params.set("actor", query.actor);
  if (query.date_from) params.set("date_from", query.date_from);
  if (query.date_to) params.set("date_to", query.date_to);
  if (query.tenant) params.set("tenant", query.tenant);
  const resp = await fetch(`${API_URL}/logs?${params.toString()}`, {
    credentials: "include",
  });
  if (!resp.ok) {
    let message = `Export failed (${resp.status})`;
    try {
      const err = await resp.json();
      message = err?.error?.message || message;
    } catch {
      // keep status-based message
    }
    throw new Error(message);
  }
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const listLogActors = (search: string): Promise<string[]> =>
  request<{ data: string[] }>("logs/actors", {
    query: { search, limit: "10" },
  }).then((res) => res.data ?? []);
