import { request } from "./client";

export interface RisInterface {
  id: string;
  name: string;
  interface_type: string;
  protocol: string;
  is_active: boolean;
  last_message_at: string | null;
  message_count: number;
  error_count: number;
  status_counts: Record<string, number>;
  [key: string]: unknown;
}

export interface RisHl7MessageRow {
  id: string;
  message_type: string;
  trigger_event: string;
  control_id: string;
  status: string;
  error_message: string | null;
  retry_count: number;
  created_at: string | null;
  processed_at: string | null;
  [key: string]: unknown;
}

export interface RisMessagePage {
  messages: RisHl7MessageRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface RisMetrics {
  endpoint_id: string;
  period: string;
  [key: string]: unknown;
}

export interface RisException {
  id: string;
  retry_count: number;
  error_message: string | null;
  created_at: string | null;
  [key: string]: unknown;
}

// The /api/ris/* handlers wrap payloads in {"data": ...} — unwrap here so
// callers get the resource directly (same shape the legacy hl7 module
// surfaces for /hl7/admin/*, which does not wrap).
export const listRisInterfaces = async (): Promise<RisInterface[]> => {
  const body = await request<{
    data: { interfaces: RisInterface[]; total: number };
  }>("ris/interfaces");
  return body.data.interfaces;
};

export const listRisInterfaceMessages = async (
  id: string,
  params: { limit?: number; offset?: number } = {}
): Promise<RisMessagePage> => {
  const query: Record<string, string> = {};
  if (params.limit !== undefined) query.limit = String(params.limit);
  if (params.offset !== undefined) query.offset = String(params.offset);
  const body = await request<{ data: RisMessagePage }>(`ris/interfaces/${id}/messages`, { query });
  return body.data;
};

export const getRisInterfaceMetrics = async (id: string, period: string): Promise<RisMetrics> => {
  const body = await request<{ data: RisMetrics }>(`ris/interfaces/${id}/metrics`, {
    query: { period },
  });
  return body.data;
};

export const listRisExceptions = async (limit = 50): Promise<RisException[]> => {
  const body = await request<{
    data: { exceptions: RisException[]; count: number };
  }>("ris/interfaces/exceptions", { query: { limit: String(limit) } });
  return body.data.exceptions;
};

export const retryRisException = async (id: string): Promise<{ retried: boolean }> => {
  const body = await request<{
    data: { message_id: string; retried: boolean };
  }>(`ris/interfaces/exceptions/${id}/retry`, { method: "POST" });
  return body.data;
};

/* ── Handoff Notes (CC-08) ────────────────────────────────────────────── */

export interface HandoffNote {
  id: string;
  patient_id: string;
  note: string;
  priority: "low" | "normal" | "high" | "urgent";
  is_read: boolean;
  tenant_id: string;
  created_by: string;
  created_at: string;
}

export const listHandoffNotes = async (params?: {
  patient_id?: string;
  unread_only?: boolean;
}): Promise<HandoffNote[]> => {
  const query: Record<string, string> = {};
  if (params?.patient_id) query.patient_id = params.patient_id;
  if (params?.unread_only) query.unread_only = "true";
  const body = await request<{ data: HandoffNote[] }>("ris/handoff-notes", {
    query,
  });
  return body.data;
};

export const createHandoffNote = async (data: {
  patient_id: string;
  note: string;
  priority?: string;
}): Promise<HandoffNote> => {
  const body = await request<{ data: HandoffNote }>("ris/handoff-notes", {
    method: "POST",
    data,
  });
  return body.data;
};

export const markHandoffNoteRead = async (id: string): Promise<void> => {
  await request(`ris/handoff-notes/${id}/read`, { method: "PATCH" });
};

/* ── Referral Tracking (CC-05) ────────────────────────────────────────── */

export interface Referral {
  id: string;
  patient_id: string;
  from_provider: string;
  to_specialist: string;
  specialty: string;
  status: "pending" | "accepted" | "completed" | "cancelled";
  order_id: string;
  report_id: string;
  notes: string;
  tenant_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export const listReferrals = async (params?: {
  status?: string;
  patient_id?: string;
}): Promise<Referral[]> => {
  const query: Record<string, string> = {};
  if (params?.status) query.status = params.status;
  if (params?.patient_id) query.patient_id = params.patient_id;
  const body = await request<{ data: Referral[] }>("ris/referrals", { query });
  return body.data;
};

export const createReferral = async (data: {
  patient_id: string;
  from_provider?: string;
  to_specialist: string;
  specialty?: string;
  order_id?: string;
  report_id?: string;
  notes?: string;
}): Promise<Referral> => {
  const body = await request<{ data: Referral }>("ris/referrals", {
    method: "POST",
    data,
  });
  return body.data;
};

export const updateReferral = async (
  id: string,
  data: { status: string; notes?: string }
): Promise<void> => {
  await request(`ris/referrals/${id}`, { method: "PATCH", data });
};

/* ── Discharge Planning Checklists (CC-06) ────────────────────────────── */

export interface DischargeItem {
  label: string;
  done: boolean;
}

export interface DischargeChecklist {
  id: string;
  patient_id: string;
  title: string;
  status: "open" | "completed";
  items: DischargeItem[];
  notes: string;
  tenant_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export const DEFAULT_DISCHARGE_ITEMS: DischargeItem[] = [
  { label: "Follow-up appointment scheduled", done: false },
  { label: "Medication reconciliation", done: false },
  { label: "Patient education provided", done: false },
];

export const listDischargeChecklists = async (params?: {
  status?: string;
  patient_id?: string;
}): Promise<DischargeChecklist[]> => {
  const query: Record<string, string> = {};
  if (params?.status) query.status = params.status;
  if (params?.patient_id) query.patient_id = params.patient_id;
  const body = await request<{ data: DischargeChecklist[] }>("ris/discharge-checklists", { query });
  return body.data;
};

export const createDischargeChecklist = async (data: {
  patient_id: string;
  title?: string;
  items?: DischargeItem[];
  notes?: string;
}): Promise<DischargeChecklist> => {
  const body = await request<{ data: DischargeChecklist }>("ris/discharge-checklists", {
    method: "POST",
    data,
  });
  return body.data;
};

export const updateDischargeChecklist = async (
  id: string,
  data: { status: string; items?: DischargeItem[]; notes?: string }
): Promise<void> => {
  await request(`ris/discharge-checklists/${id}`, { method: "PATCH", data });
};
