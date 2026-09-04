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
  // B-12: match quality of the coding-map hit (0.95 exact key, 0.75 substring).
  confidence?: number;
}

export interface UnbilledAgingGroup {
  // 'date' on the default grouping; dimension value under 'bucket' for
  // site/payer groupings (D2).
  date?: string;
  bucket?: string;
  count: number;
  total_amount: number;
  oldest_charge_days: number;
}

export interface UnbilledAgingReport {
  groups: UnbilledAgingGroup[];
  total_unbilled: number;
  group_by?: "date" | "site" | "payer";
  buckets?: { over5: number; over10: number };
}

export const listBillingQueue = (query: Record<string, string> = {}): Promise<BillingQueuePage> =>
  request<BillingQueuePage>("ris/billing/queue", { query });

export const dropCharge = (id: string): Promise<{ id: string; status: string }> =>
  request(`ris/billing/charges/${id}/drop`, { method: "POST" });

// B-05: batch confirm-and-drop — best-effort per charge, server reports
// dropped/missing/skipped so the coder sees exactly what landed.
export interface BatchDropResult {
  dropped: string[];
  missing: string[];
  skipped: string[];
}

export const batchDropCharges = (
  chargeIds: string[],
  overrides?: Record<string, { cpt_code?: string; icd10_code?: string }>
): Promise<BatchDropResult> =>
  request<{ data: BatchDropResult }>("ris/billing/charges/batch", {
    method: "POST",
    data: { charge_ids: chargeIds, overrides },
  }).then((res) => res?.data ?? { dropped: [], missing: [], skipped: [] });

// B-10: batch rework of a denial reason-code group.
export const batchResubmitClaims = (
  claimIds: string[],
  note: string
): Promise<{ resubmitted: string[]; missing: string[] }> =>
  request<{ data: { resubmitted: string[]; missing: string[] } }>(
    "ris/billing/claims/batch-resubmit",
    { method: "POST", data: { claim_ids: claimIds, note } }
  ).then((res) => res?.data ?? { resubmitted: [], missing: [] });

export const getUnbilledAging = (
  query: Record<string, string> = {}
): Promise<UnbilledAgingReport> => request<UnbilledAgingReport>("ris/billing/unbilled", { query });

export const getCptSuggestions = (procedure: string): Promise<{ data: CptSuggestion[] }> =>
  request<{ data: CptSuggestion[] }>("ris/billing/cpt-suggestions", {
    query: { procedure },
  });

export const submitClaim = (
  id: string
): Promise<{ id: string; claim_number: string; status: string }> =>
  request(`ris/billing/claims/${id}/submit`, { method: "POST" });

// B-03: patient financial responsibility — coverage snapshot plus open
// charges/invoice balances for the coder's pre-bill review.
export interface PatientResponsibility {
  patient_id: string;
  coverage_status: string;
  provider?: string;
  member_id?: string;
  copay_amount: number | null;
  deductible_total: number | null;
  deductible_remaining: number | null;
  coinsurance_pct: number | null;
  open_charges_count: number;
  open_charges_total: number;
  open_invoices: number;
  invoice_balance: number;
}

export const getPatientResponsibility = (patientId: string): Promise<PatientResponsibility> =>
  request<{ data: PatientResponsibility }>(`ris/billing/patients/${patientId}/responsibility`).then(
    (res) => res?.data
  );

export const reworkDenial = (id: string): Promise<{ id: string; status: string }> =>
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
  request<{ data: DenialReworkRow[] }>("ris/billing/denials").then((res) => res.data ?? []);

export const resubmitClaim = (
  id: string,
  body: { note: string }
): Promise<{ id: string; status: string }> =>
  request(`ris/billing/claims/${id}/resubmit`, { method: "POST", data: body });

export const getClaimHistory = (id: string): Promise<ClaimEvent[]> =>
  request<{ data: ClaimEvent[] }>(`ris/billing/claims/${id}/history`).then((res) => res.data ?? []);

// B-06: full claim lifecycle dashboard.
export interface ClaimRow {
  id: string;
  claim_number: string;
  payer_name: string;
  status: string;
  rejection_code?: string;
  rejection_reason?: string;
  correction_count?: number;
  prior_auth_number?: string;
  created_at?: string;
  patient_name: string;
  accession_number: string;
  cpt_code: string;
  charge_amount: number;
}

export const listClaims = (query: Record<string, string> = {}): Promise<ClaimRow[]> =>
  request<{ data: ClaimRow[] }>("ris/billing/claims", { query }).then((res) => res?.data ?? []);

// B-02: batch submission — one claim per prepared charge.
export const batchSubmitClaims = (
  chargeIds: string[]
): Promise<{
  submitted: { charge_id: string; claim_number: string; status: string }[];
  missing: string[];
}> =>
  request<{
    data: {
      submitted: { charge_id: string; claim_number: string; status: string }[];
      missing: string[];
    };
  }>("ris/billing/claims/batch-submit", {
    method: "POST",
    data: { charge_ids: chargeIds },
  }).then((res) => res?.data ?? { submitted: [], missing: [] });

// B-09: Procedure Fee Schedule — list/edit/import/history.
export interface FeeScheduleItem {
  id: string;
  procedure_code: string;
  description: string;
  list_price: number;
  active: boolean;
}

export interface FeeScheduleHistoryRow {
  procedure_code: string;
  description: string;
  list_price: number;
  changed_by: string;
  changed_at: string;
}

export const listFeeSchedule = (query: Record<string, string> = {}): Promise<FeeScheduleItem[]> =>
  request<{ data: FeeScheduleItem[] }>("ris/billing/fee-schedule", { query }).then(
    (res) => res?.data ?? []
  );

export const updateFeeScheduleItem = (
  code: string,
  body: { list_price?: number; description?: string }
): Promise<FeeScheduleItem> =>
  request<{ data: FeeScheduleItem }>(`ris/billing/fee-schedule/${code}`, {
    method: "PUT",
    data: body,
  }).then((res) => res?.data);

export const importFeeSchedule = (rows: FeeScheduleItem[]): Promise<{ imported: number }> =>
  request<{ data: { imported: number } }>("ris/billing/fee-schedule/import", {
    method: "POST",
    data: { rows },
  }).then((res) => res?.data ?? { imported: 0 });

export const getFeeScheduleHistory = (code: string): Promise<FeeScheduleHistoryRow[]> =>
  request<{ data: FeeScheduleHistoryRow[] }>(`ris/billing/fee-schedule/history/${code}`).then(
    (res) => res?.data ?? []
  );

// B-08: Payer Contract Rates — list/create/update/deactivate/comparison.
export interface PayerContract {
  id: string;
  payer_id: string;
  payer_name: string;
  procedure_code: string;
  contracted_rate: number;
  effective_date: string;
  active: boolean;
}

export interface ContractComparisonRow {
  charge_id: string;
  procedure_code: string;
  payer_name: string;
  charged_amount: number;
  contracted_rate: number;
  variance: number;
  flag: "under_charge" | "over_charge" | "at_rate";
}

export const listPayerContracts = (query: Record<string, string> = {}): Promise<PayerContract[]> =>
  request<{ data: PayerContract[] }>("ris/billing/contracts", { query }).then(
    (res) => res?.data ?? []
  );

export const createPayerContract = (body: Partial<PayerContract>): Promise<PayerContract> =>
  request<{ data: PayerContract }>("ris/billing/contracts", {
    method: "POST",
    data: body,
  }).then((res) => res?.data);

export const updatePayerContract = (
  id: string,
  body: { contracted_rate?: number; effective_date?: string; active?: boolean }
): Promise<PayerContract> =>
  request<{ data: PayerContract }>(`ris/billing/contracts/${id}`, {
    method: "PUT",
    data: body,
  }).then((res) => res?.data);

export const deletePayerContract = (id: string): Promise<{ id: string; active: boolean }> =>
  request<{ data: { id: string; active: boolean } }>(`ris/billing/contracts/${id}`, {
    method: "DELETE",
  }).then((res) => res?.data);

export const getContractComparison = (): Promise<ContractComparisonRow[]> =>
  request<{ data: ContractComparisonRow[] }>("ris/billing/contracts/comparison").then(
    (res) => res?.data ?? []
  );

// S11-13: signed-vs-charged reconciliation snapshot (Billing → Reconciliation).
export interface ReconciliationSnapshot {
  signed_reports: number;
  charged_reports: number;
  capture_rate_pct: number;
}

export const getReconciliation = (): Promise<ReconciliationSnapshot> =>
  request<ReconciliationSnapshot>("ris/billing/reconciliation").then((res) => res);

// R2-02-01: 835-style denial intake — records a denial on a claim with the
// payer's reason code so the rework trail starts at intake (BILLING_WRITE).
// Response is the bare object { id, status, code } (not wrapped in `data`).
export const importDenial = (body: {
  claim_id: string;
  reason_code?: string;
  reason?: string;
}): Promise<{ id: string; status: string; code: string }> =>
  request<{ id: string; status: string; code: string }>("ris/billing/denials/import", {
    method: "POST",
    data: body,
  }).then((res) => res ?? { id: "", status: "DENIED", code: "" });
