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