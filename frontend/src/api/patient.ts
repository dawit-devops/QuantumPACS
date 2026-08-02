import { request } from "./client";

export interface PatientSummary {
  id?: number;
  patient_id?: string;
  name?: string;
  studies?: Array<Record<string, unknown>>;
}

export const getPatient = (patientId: string): Promise<PatientSummary> =>
  request<PatientSummary>(`patients/${patientId}`);
