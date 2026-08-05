import { request } from "./client";

export interface PatientSummary {
  id?: number;
  patient_id?: string;
  name?: string;
  birth_date?: string;
  sex?: string;
  studies?: Array<Record<string, unknown>>;
}

export const getPatient = (patientId: string): Promise<PatientSummary> =>
  request<PatientSummary>(`patients/${patientId}`);
