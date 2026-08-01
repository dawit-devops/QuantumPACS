import { request } from "./client";

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

export const listLogActors = (search: string): Promise<string[]> =>
  request<{ data: string[] }>("logs/actors", {
    query: { search, limit: "10" },
  }).then((res) => res.data ?? []);
