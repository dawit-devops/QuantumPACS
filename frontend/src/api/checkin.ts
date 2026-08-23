import { request } from "./client";

export interface CheckInSummary {
  patient_name: string | null;
  start_time: string;
  status: string;
  modality?: string | null;
  room?: string | null;
  prep_instructions?: string | null;
}

export interface CheckInConfirmation {
  id: string;
  status: string;
}

export interface ConsentPayload {
  accepted: boolean;
  signature_png: string;
  decline_reason: string;
}

export interface PaymentPayload {
  method: "cash" | "card" | "check";
  amount: number;
  idempotency_key: string;
  processor_token?: string;
}

export interface PaymentResult {
  payment: { id: string; amount: number; method: string };
  receipt: { id: string; payment_id: string; receipt_number: string };
}

// RIS-REG-04: kiosk self-check-in. The QR token is the credential —
// no Authorization header, the backend whitelists this path.
export const getCheckIn = (token: string): Promise<CheckInSummary> =>
  request<CheckInSummary>(`ris/checkin/${encodeURIComponent(token)}`);

export const confirmCheckIn = (
  token: string,
): Promise<CheckInConfirmation> =>
  request<CheckInConfirmation>(`ris/checkin/${encodeURIComponent(token)}`, {
    method: "POST",
  });

// K-03: persist kiosk digital consent (signature PNG base64 / decline reason).
export const submitConsent = (
  token: string,
  payload: ConsentPayload,
): Promise<{ id: string; accepted: boolean }> =>
  request<{ id: string; accepted: boolean }>(
    `ris/checkin/${encodeURIComponent(token)}/consent`,
    { method: "POST", data: payload },
  );

// K-04: co-pay capture at the kiosk — token-scoped, idempotent.
export const submitPayment = (
  token: string,
  payload: PaymentPayload,
): Promise<PaymentResult> =>
  request<{ data: PaymentResult }>(
    `ris/checkin/${encodeURIComponent(token)}/payment`,
    { method: "POST", data: payload },
  ).then((res) => res.data);
