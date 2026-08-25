import { request } from "./client";

// §2.11 nursing surfaces (N-01..N-04), backed by api/nursing.py.
// Reads pass any-of [NURSING_READ, EXAM_READ]; writes require NURSING_WRITE.

export interface VitalsRow {
  id: string;
  exam_id?: string;
  patient_id?: string;
  bp_systolic?: number | null;
  bp_diastolic?: number | null;
  hr?: number | null;
  spo2?: number | null;
  temperature?: number | null;
  respiration?: number | null;
  weight_kg?: number | null;
  height_cm?: number | null;
  operator_id?: string;
  recorded_at?: string;
}

export interface VitalsInput {
  bp_systolic?: number;
  bp_diastolic?: number;
  heart_rate?: number;
  spo2?: number;
  temperature_c?: number;
  respiration?: number;
  weight_kg?: number;
  height_cm?: number;
}

export interface ChecklistItem {
  key: string;
  label: string;
  required: boolean;
  checked: boolean;
}

export interface ChecklistRow {
  id: string;
  exam_id?: string;
  status: "in_progress" | "complete";
  items: ChecklistItem[];
  confirmed_by?: string;
  confirmed_at?: string | null;
}

export interface ConsentRow {
  id: string;
  accepted: boolean;
  signature_png?: string;
  declined_reason?: string;
  consent_text_version?: string;
  signed_by?: string;
  signed_at?: string;
}

export interface ConsentInput {
  accepted: boolean;
  signature_png?: string;
  declined_reason?: string;
  consent_text_version?: string;
  witnessed_by?: string;
}

export interface NurseNoteRow {
  id: string;
  note: string;
  author_id?: string;
  author_role?: string;
  created_at?: string;
}

export interface PrepListRow {
  exam_id: string;
  patient_id?: string;
  patient_name?: string;
  modality?: string;
  priority?: string;
  status?: string;
  checklist_id?: string | null;
  checklist_status?: "in_progress" | "complete" | null;
  checked_count?: number;
  required_count?: number;
}

const data = async <T>(path: string): Promise<T> => {
  const res = await request<{ data: T }>(path);
  return (res as { data: T }).data;
};

export const getExamVitals = (examId: string): Promise<VitalsRow[]> =>
  data<VitalsRow[]>(`exams/${examId}/vitals`).then((d) => d ?? []);

export const recordExamVitals = (examId: string, input: VitalsInput): Promise<VitalsRow> =>
  request(`exams/${examId}/vitals`, { data: input });

export const getChecklist = (examId: string): Promise<ChecklistRow> =>
  data<ChecklistRow>(`exams/${examId}/pre-procedure-checklist`);

export const updateChecklist = (
  examId: string,
  payload: { items: ChecklistItem[]; confirmed: boolean }
): Promise<ChecklistRow> =>
  request(`exams/${examId}/pre-procedure-checklist`, {
    method: "PUT",
    data: payload,
  });

export const getConsent = (examId: string): Promise<ConsentRow | null> =>
  data<ConsentRow | null>(`exams/${examId}/consent`);

export const recordConsent = (examId: string, input: ConsentInput): Promise<ConsentRow> =>
  request(`exams/${examId}/consent`, { data: input });

export const getNurseNotes = (examId: string): Promise<NurseNoteRow[]> =>
  data<NurseNoteRow[]>(`exams/${examId}/nurse-notes`).then((d) => d ?? []);

export const addNurseNote = (examId: string, note: string): Promise<NurseNoteRow> =>
  request(`exams/${examId}/nurse-notes`, { data: { note } });

export const getPrepList = (): Promise<PrepListRow[]> =>
  data<PrepListRow[]>("nursing/prep-list").then((d) => d ?? []);
