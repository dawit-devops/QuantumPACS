import { request } from "./client";

export interface MessageLogEntry {
  id: string;
  channel: "sms" | "email" | "phone";
  recipient: string;
  event_type: string;
  subject: string;
  status: "SENT" | "FAILED";
  attempts: number;
  provider_receipt: string;
  sent_at: string;
}

export interface MessageLogPage {
  data: MessageLogEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface ReminderConfig {
  id: string;
  event_type: string;
  channel: "sms" | "email" | "phone";
  template: string;
  lead_time_hours: number;
  active: boolean;
}

export interface SendReminderInput {
  event_type: string;
  recipient: string;
  channel: "sms" | "email" | "phone";
  subject?: string;
  body?: string;
}

export interface ReminderConfigInput {
  event_type: string;
  channel: "sms" | "email" | "phone";
  template?: string;
  lead_time_hours?: number;
  active?: boolean;
}

// R2-02: reminders — dispatch, delivery audit log, per-event config.
export const sendReminder = (data: SendReminderInput): Promise<{ status: string }> =>
  request("ris/reminders/send", { method: "POST", data });

export const listReminderLog = (
  query: Record<string, string> = {},
): Promise<MessageLogPage> =>
  request<MessageLogPage>("ris/reminders/log", { query });

export const listReminderConfig = (): Promise<{ data: ReminderConfig[] }> =>
  request("ris/reminders/config", { method: "GET" });

export const saveReminderConfig = (data: ReminderConfigInput): Promise<{ status: string }> =>
  request("ris/reminders/config", { method: "POST", data });

export interface PatientOptOutEntry {
  id: string;
  patient_id: string;
  event_type: string | null;
  tenant_id: string;
  created_at: string;
  created_by: string;
}

export interface PatientOptOutInput {
  patient_id: string;
  event_type?: string | null;
  opted_out?: boolean;
}

// CS4/CC-12: per-patient reminder opt-out registry.
export const listPatientOptOuts = (): Promise<{ data: PatientOptOutEntry[] }> =>
  request("ris/reminders/optouts", { method: "GET" });

export const setPatientOptOut = (data: PatientOptOutInput): Promise<{ data: PatientOptOutInput }> =>
  request("ris/reminders/optouts", { method: "POST", data });