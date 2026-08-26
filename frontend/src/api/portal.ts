import { request } from "./client";

// ---------------------------------------------------------------------------
// R19 Hospital Staff / Patient portal API client — scope-gated patient data
// (api/portal.py). Patients are only reachable through patient_staff_scope
// for the requesting user (HIPAA minimum necessary); out-of-scope lookups
// return data: null instead of 403 so scope absence is indistinguishable from
// "no such patient".
// ---------------------------------------------------------------------------

export interface PortalScope {
  id: string;
  patient_id: string;
  scope_type: "ward" | "care_team" | "assigned";
  existing?: boolean;
}

export interface PortalDemographics {
  id?: number;
  patient_id?: string;
  name?: string;
  birth_date?: string;
  sex?: string;
}

export interface PortalOrder {
  id: string;
  patient_id?: string;
  requested_procedure?: string;
  indication?: string;
  urgency?: string;
  status?: string;
  created_at?: string;
}

export interface PortalReport {
  id: string;
  exam_id?: string;
  accession_number?: string;
  modality?: string;
  body_part?: string;
  finding?: string;
  impression?: string;
  status?: string;
  signed_at?: string;
  signed_by_name?: string;
  created_at?: string;
}

export interface PortalPatientBundle {
  patient: PortalDemographics | null;
  orders: PortalOrder[];
  reports: PortalReport[];
}

export interface PortalFollowUp {
  id: string;
  patient_id?: string;
  reason?: string;
  status?: string;
  priority?: string;
  created_at?: string;
}

export interface PortalAppointment {
  id: string;
  patient_id?: string;
  start_time?: string;
  end_time?: string;
  status?: string;
  modality?: string;
  room?: string;
  prep_instructions?: string;
  procedure?: string;
  priority?: string;
  accession_number?: string;
  checked_in_at?: string;
}

// ---- Scope ------------------------------------------------------------------

export const listScope = (): Promise<PortalScope[]> =>
  request<{ data: PortalScope[] }>("portal/scope").then((res) => res.data ?? []);

// ---- Patient data --------------------------------------------------------------

export const getPortalPatient = (patientId: string): Promise<PortalPatientBundle | null> =>
  request<{ data: PortalPatientBundle | null }>(`portal/patients/${patientId}`).then(
    (res) => res?.data ?? null
  );

export const getPortalOrders = (patientId: string): Promise<PortalOrder[]> =>
  request<{ data: PortalOrder[] }>(`portal/patients/${patientId}/orders`).then(
    (res) => res.data ?? []
  );

export const getPortalReport = (
  patientId: string,
  reportId: string
): Promise<PortalReport | null> =>
  request<{ data: PortalReport | null }>(`portal/patients/${patientId}/reports/${reportId}`).then(
    (res) => res?.data ?? null
  );

// ---- Follow-ups -----------------------------------------------------------------

export const listFollowUps = (query: Record<string, string> = {}): Promise<PortalFollowUp[]> =>
  request<{ data: PortalFollowUp[] }>("portal/follow-ups", { query }).then((res) => res.data ?? []);

export const createFollowUp = (data: Record<string, unknown>): Promise<{ id: string }> =>
  request<{ data: { id: string } }>("portal/follow-ups", { data }).then((res) => res.data);

export const updateFollowUp = (id: string, data: Record<string, unknown>): Promise<void> =>
  request<void>(`portal/follow-ups/${id}`, {
    method: "PUT",
    data,
  }).then(() => undefined);

// ---- Consent ----------------------------------------------------------------

export const updateConsent = (
  patientId: string,
  consentResults: boolean,
  consentAppointments?: boolean
): Promise<{ patient_id: string; consent_results: boolean }> =>
  request<{ data: { patient_id: string; consent_results: boolean } }>(
    `portal/patients/${patientId}/consent`,
    {
      method: "PUT",
      data: {
        consent_results: consentResults,
        ...(consentAppointments !== undefined ? { consent_appointments: consentAppointments } : {}),
      },
    }
  ).then((res) => res.data);

// ---- Appointments ----------------------------------------------------------

export const getPortalAppointments = (
  patientId: string,
  query?: Record<string, string>
): Promise<PortalAppointment[]> =>
  request<{ data: PortalAppointment[] }>(
    `portal/patients/${patientId}/appointments`,
    query ? { query } : undefined
  ).then((res) => res.data ?? []);
