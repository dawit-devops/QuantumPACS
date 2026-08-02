import { request } from "./client";

export interface Hl7Message {
  id: number;
  message_type?: string;
  parse_status?: string;
  patient_id?: string;
  sending_facility?: string;
  created_at?: string;
  [key: string]: unknown;
}

export interface Hl7MessagesPage {
  messages: Hl7Message[];
  total: number;
}

export interface Hl7MessagesParams {
  limit?: number;
  offset?: number;
  message_type?: string;
  parse_status?: string;
  patient_id?: string;
  sending_facility?: string;
}

export interface Hl7Config {
  enabled?: boolean;
  mllp_port?: number;
  allowed_ips?: string[];
  [key: string]: unknown;
}

export interface Hl7Status {
  listening?: boolean;
  [key: string]: unknown;
}

export interface Hl7Metrics {
  period: string;
  [key: string]: unknown;
}

export const listHl7Messages = (
  params: Hl7MessagesParams,
): Promise<Hl7MessagesPage> =>
  request<Hl7MessagesPage>("hl7/admin/messages", {
    query: params as Record<string, string>,
  });

export const getHl7Message = (id: string): Promise<Hl7Message> =>
  request<Hl7Message>(`hl7/admin/messages/${id}`);

export const getHl7Metrics = (period: string): Promise<Hl7Metrics> =>
  request<Hl7Metrics>("hl7/admin/metrics", { query: { period } });

export const getHl7Config = (): Promise<Hl7Config> =>
  request<Hl7Config>("hl7/admin/config");

export const updateHl7Config = (
  data: Record<string, unknown>,
): Promise<{ updated: string[] }> =>
  request<{ updated: string[] }>("hl7/admin/config", {
    method: "PUT",
    data,
  });

export const getHl7Status = (): Promise<Hl7Status> =>
  request<Hl7Status>("hl7/admin/status");
