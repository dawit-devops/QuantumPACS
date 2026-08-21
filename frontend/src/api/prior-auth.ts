import { request } from "./client";

export interface PriorAuthRequest {
  id: string;
  order_id: string;
  procedure_code: string;
  payer_id: string;
  payer_name: string;
  status: "NOT_REQUIRED" | "REQUIRED" | "PENDING" | "APPROVED" | "DENIED" | "EXPIRED";
  auth_number?: string;
  approved_units?: number;
  approved_date?: string;
  expiry_date?: string;
  denial_reason?: string;
  created_at?: string;
}

export interface PriorAuthPage {
  data: PriorAuthRequest[];
  total: number;
}

export interface SubmitPriorAuthInput {
  order_id: string;
  procedure_code?: string;
  payer_id?: string;
  payer_name?: string;
}

// R2-01: prior authorization request lifecycle.
export const listPriorAuth = (
  query: Record<string, string> = {},
): Promise<PriorAuthPage> => request<PriorAuthPage>("ris/prior-auth", { query });

export const listPriorAuthExpiring = (
  days = 7,
): Promise<PriorAuthPage> =>
  request<PriorAuthPage>("ris/prior-auth", {
    query: { expiring_soon: "1", days: String(days) },
  });

export const submitPriorAuth = (data: SubmitPriorAuthInput): Promise<{ status: string }> =>
  request("ris/prior-auth", { method: "POST", data });

export const decidePriorAuth = (
  id: string,
  decision: {
    action: "approve" | "deny";
    auth_number?: string;
    approved_units?: number;
    expiry_date?: string;
    denial_reason?: string;
  },
): Promise<{ id: string; status: string }> =>
  request(`ris/prior-auth/${id}/decision`, { method: "POST", data: decision });

export const runPriorAuthExpiry = (): Promise<{ expired: number }> =>
  request("ris/prior-auth/expire", { method: "POST" });