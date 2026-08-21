import { request } from "./client";

export interface BillingQueueEntry {
  id: string;
  patient_id: string;
  patient_name: string;
  accession_number: string;
  cpt_code: string;
  cpt_description: string;
  icd10_code: string;
  charge_amount: number;
  status: string;
  created_at: string;
}

export interface BillingQueuePage {
  data: BillingQueueEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface CptSuggestion {
  procedure_code: string;
  cpt_code: string;
  cpt_description: string;
  icd10_code: string;
  icd10_description: string;
}

export interface UnbilledAgingGroup {
  date: string;
  count: number;
  total_amount: number;
  oldest_charge_days: number;
}

export interface UnbilledAgingReport {
  groups: UnbilledAgingGroup[];
  total_unbilled: number;
}

export const listBillingQueue = (
  query: Record<string, string> = {},
): Promise<BillingQueuePage> =>
  request<BillingQueuePage>("ris/billing/queue", { query });

export const dropCharge = (id: string): Promise<{ id: string; status: string }> =>
  request(`ris/billing/charges/${id}/drop`, { method: "POST" });

export const getUnbilledAging = (): Promise<UnbilledAgingReport> =>
  request<UnbilledAgingReport>("ris/billing/unbilled", { method: "GET" });

export const getCptSuggestions = (
  procedure: string,
): Promise<{ data: CptSuggestion[] }> =>
  request<{ data: CptSuggestion[] }>("ris/billing/cpt-suggestions", {
    query: { procedure },
  });

export const submitClaim = (
  id: string,
): Promise<{ id: string; claim_number: string; status: string }> =>
  request(`ris/billing/claims/${id}/submit`, { method: "POST" });

export const reworkDenial = (
  id: string,
): Promise<{ id: string; status: string }> =>
  request(`ris/billing/denials/${id}/rework`, { method: "POST" });
// ---------------------------------------------------------------------------
// R2-S3/S4 — denial rework chain
// ---------------------------------------------------------------------------

export interface DenialReworkRow {
  id: string;
  claim_number?: string;
  payer_name?: string;
  status: string;
  rejection_code?: string;
  rejection_reason?: string;
  correction_count: number;
  prior_auth_number?: string;
  patient_name?: string;
  accession_number?: string;
  cpt_code?: string;
  charge_amount?: number;
}

export interface ClaimEvent {
  id?: string;
  event_type: string;
  note?: string;
  actor?: string;
  created_at?: string;
}

export const listDenialRework = (): Promise<DenialReworkRow[]> =>
  request<{ data: DenialReworkRow[] }>("ris/billing/denials").then(
    (res) => res.data ?? [],
  );

export const resubmitClaim = (
  id: string,
  body: { note: string },
): Promise<{ id: string; status: string }> =>
  request(`ris/billing/claims/${id}/resubmit`, { method: "POST", data: body });

export const getClaimHistory = (id: string): Promise<ClaimEvent[]> =>
  request<{ data: ClaimEvent[] }>(`ris/billing/claims/${id}/history`).then(
    (res) => res.data ?? [],
  );
