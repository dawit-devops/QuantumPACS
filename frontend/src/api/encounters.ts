import { request } from "./client";

// CS6/CC-03: patient encounter log — visit/call/message/fax contact rows.
export interface Encounter {
  id: string;
  patient_id: string;
  encounter_type: "visit" | "call" | "message" | "fax";
  occurred_at: string;
  summary: string;
  linked_order_id: string;
  linked_report_id: string;
  recorded_by: string;
  tenant_id: string;
  created_at: string;
}

export interface EncounterInput {
  patient_id: string;
  encounter_type: string;
  summary: string;
  occurred_at?: string | null;
  linked_order_id?: string;
  linked_report_id?: string;
}

export const listEncounters = (
  query: Record<string, string>,
): Promise<{ data: Encounter[] }> =>
  request<{ data: Encounter[] }>("ris/encounters", { query });

export const createEncounter = (
  data: EncounterInput,
): Promise<{ data: Encounter }> =>
  request("ris/encounters", { method: "POST", data });
