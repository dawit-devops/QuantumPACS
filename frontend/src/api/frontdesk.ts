import { request } from "./client";
import type { RisAppointment } from "./scheduling";

// ---------------------------------------------------------------------------
// R08 Front Desk API client — patient registration, visits + check-in, order
// intake, consents, insurance/guarantor, appointment booking (capacity-aware)
// and the HIPAA privacy-projected waiting queue (api/frontdesk.py).
// ---------------------------------------------------------------------------

export interface FrontDeskPatient {
  id: number;
  patient_id: string;
  name: string;
  birth_date?: string;
  sex?: string;
}

export interface Visit {
  id: string;
  patient_id: string;
  visit_date?: string;
  status: "registered" | "checked_in" | "in_progress" | "complete";
  destination_room?: string;
  hl7_sync_status?: "pending" | "synced" | "failed";
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface VisitOrder {
  id: string;
  visit_id: string;
  patient_id: string;
  requested_procedure: string;
  indication?: string;
  urgency: "routine" | "urgent" | "stat";
  referring_physician?: string;
  status: "open" | "cancelled";
  created_at?: string;
}

export interface ConsentDocument {
  id: string;
  visit_id: string;
  consent_type: string;
  status: "required" | "attached" | "missing";
  file_name?: string;
  attached_by?: string;
  attached_at?: string;
  created_at?: string;
}

export interface InsuranceRecord {
  id: string;
  patient_id: string;
  visit_id?: string | null;
  policy_number?: string;
  guarantor_name?: string;
  authorization_status?: "none" | "pending" | "approved" | "denied";
  authorization_number?: string;
  notes?: string;
  provider?: string;
  member_id?: string;
  copay_amount?: number | null;
  deductible_total?: number | null;
  deductible_remaining?: number | null;
  created_at?: string;
}

export interface InsuranceEligibility {
  patient_id: string;
  status: "active" | "none" | "inactive";
  provider: string;
  member_id: string;
  copay_amount: number | null;
  deductible_total: number | null;
  deductible_remaining: number | null;
  checked_at: string;
}

export interface Appointment {
  id: string;
  patient_id: string;
  visit_id?: string | null;
  worklist_entry_id?: string | null;
  modality?: string;
  room?: string;
  technologist?: string;
  scheduled_date?: string;
  scheduled_time?: string;
  status: "scheduled" | "checked_in" | "completed" | "cancelled";
  created_at?: string;
}

export interface AvailabilitySlot {
  time: string;
  capacity: number;
  booked: number;
  state: "full" | "free";
}

export interface QueueEntry {
  visit_id: string;
  initials: string;
  last4: string;
  status: string;
  destination: string;
  updated_at: string;
  wait_minutes: number | null;
}

export interface VisitPage {
  data: Visit[];
  total: number;
  page: number;
  per_page: number;
}

// ---- Patients ---------------------------------------------------------------

export const searchPatients = (q: string): Promise<FrontDeskPatient[]> =>
  request<{ data: FrontDeskPatient[] }>("patients/search", {
    query: { q },
  }).then((res) => res.data ?? []);

export const createPatient = (
  data: Record<string, unknown>,
): Promise<FrontDeskPatient> =>
  request<{ data: FrontDeskPatient }>("patients", { data }).then(
    (res) => res.data,
  );

// ---- Visits ------------------------------------------------------------------

export const listVisits = (
  query: Record<string, string> = {},
): Promise<VisitPage> =>
  request<VisitPage>("visits", { query }).then(
    (res) => res ?? { data: [], total: 0, page: 1, per_page: 20 },
  );

export const createVisit = (data: Record<string, unknown>): Promise<Visit> =>
  request<{ data: Visit }>("visits", { data }).then((res) => res.data);

export const getVisit = (id: string): Promise<Visit | null> =>
  request<{ data: Visit }>(`visits/${id}`).then((res) => res?.data ?? null);

export const updateVisit = (
  id: string,
  data: Record<string, unknown>,
): Promise<void> => request(`visits/${id}`, { method: "PUT", data });

export const checkInVisit = (id: string): Promise<void> =>
  updateVisit(id, { status: "checked_in" });

// ---- Orders -----------------------------------------------------------------

export const listOrders = (visitId: string): Promise<VisitOrder[]> =>
  request<{ data: VisitOrder[] }>(`visits/${visitId}/orders`).then(
    (res) => res.data ?? [],
  );

export const createOrder = (
  visitId: string,
  data: Record<string, unknown>,
): Promise<VisitOrder> =>
  request<{ data: VisitOrder }>(`visits/${visitId}/orders`, { data }).then(
    (res) => res.data,
  );

// ---- Consents ---------------------------------------------------------------

export const listConsents = (visitId: string): Promise<ConsentDocument[]> =>
  request<{ data: ConsentDocument[] }>(`visits/${visitId}/consents`).then(
    (res) => res.data ?? [],
  );

export const attachConsent = (
  visitId: string,
  data: Record<string, unknown>,
): Promise<ConsentDocument> =>
  request<{ data: ConsentDocument }>(`visits/${visitId}/consents/attach`, {
    data,
  }).then((res) => res.data);

// ---- Insurance ----------------------------------------------------------------

export const listInsurance = (patientId: string): Promise<InsuranceRecord[]> =>
  request<{ data: InsuranceRecord[] }>(`patients/${patientId}/insurance`).then(
    (res) => res.data ?? [],
  );

export const createInsurance = (
  patientId: string,
  data: Record<string, unknown>,
): Promise<InsuranceRecord> =>
  request<{ data: InsuranceRecord }>(`patients/${patientId}/insurance`, {
    data,
  }).then((res) => res.data);

export const getInsuranceEligibility = (
  patientId: string,
): Promise<InsuranceEligibility | null> =>
  request<{ data: InsuranceEligibility }>(
    `ris/patients/${patientId}/eligibility`,
  ).then((res) => res?.data ?? null);

// ---- Appointments / capacity ---------------------------------------------------

export const getAvailability = (
  query: Record<string, string>,
): Promise<AvailabilitySlot[]> =>
  request<{ data: AvailabilitySlot[] }>("schedule/availability", {
    query,
  }).then((res) => res.data ?? []);

export const listAppointments = (
  query: Record<string, string> = {},
): Promise<Appointment[]> =>
  request<{ data: Appointment[] }>("appointments", { query }).then(
    (res) => res.data ?? [],
  );

export const createAppointment = (
  data: Record<string, unknown>,
): Promise<Appointment> =>
  request<{ data: Appointment }>("appointments", { data }).then(
    (res) => res.data,
  );

// ---- RIS appointments (today schedule, FD-06) ---------------------------------

export const listRisAppointments = (
  query: Record<string, string> = {},
): Promise<RisAppointment[]> =>
  request<{ data: RisAppointment[] }>("ris/appointments", { query }).then(
    (res) => res.data ?? [],
  );
export const cancelAppointment = (id: string): Promise<void> =>
  request(`appointments/${id}`, { data: undefined, method: "DELETE" });

// ---- Waiting queue --------------------------------------------------------------

export const getWaitingQueue = (
  query: Record<string, string> = {},
): Promise<QueueEntry[]> =>
  request<{ data: QueueEntry[] }>("queue", { query }).then(
    (res) => res.data ?? [],
  );
