import { request } from "./client";

// CS7/CC-04: communication log — inbound/outbound correspondence trail.
export interface Communication {
  id: string;
  patient_id: string;
  direction: "inbound" | "outbound";
  channel: string;
  category: string;
  summary: string;
  related_order_id: string;
  logged_by: string;
  tenant_id: string;
  created_at: string;
}

export interface CommunicationInput {
  patient_id: string;
  direction: string;
  channel?: string;
  category?: string;
  summary: string;
  related_order_id?: string;
}

export const listCommunications = (
  query: Record<string, string>,
): Promise<{ data: Communication[] }> =>
  request<{ data: Communication[] }>("ris/communications", { query });

export const createCommunication = (
  data: CommunicationInput,
): Promise<{ data: Communication }> =>
  request("ris/communications", { method: "POST", data });
