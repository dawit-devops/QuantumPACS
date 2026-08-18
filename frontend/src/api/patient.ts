import { request } from "./client";

export interface PatientSummary {
  id?: number;
  patient_id?: string;
  name?: string;
  birth_date?: string;
  sex?: string;
  studies?: Array<Record<string, unknown>>;
  // Care-coordinator review (P2-1): patient-scoped reports for the Reports &
  // Results card (backend enriches the patient payload).
  reports?: Array<{
    id: string;
    exam_id: string;
    status: string;
    created_at?: string;
    signed_at?: string;
    accession_number?: string;
    modality?: string;
    procedure_desc?: string;
  }>;
}

export const getPatient = (patientId: string): Promise<PatientSummary> =>
  request<PatientSummary>(`patients/${patientId}`);
